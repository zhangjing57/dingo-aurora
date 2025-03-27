from asyncio import sleep
import json
import os
import subprocess
import time
from typing import Dict, Optional
from celery import Celery
from dingoops.db.models.cluster.models import Cluster
from pydantic import BaseModel, Field
from fastapi import Path
from pathlib import Path as PathLib
from requests import Session
from dingoops.celery_api.celery_app import celery_app
from dingoops.celery_api import CONF
from dingoops.db.engines.mysql import get_engine 


BASE_DIR = os.getcwd()
TERRAFORM_DIR = os.path.join(BASE_DIR, "dingoops", "templates", "terraform")
ANSIBLE_DIR = os.path.join(BASE_DIR, "templates", "ansible-deploy")
WORK_DIR = CONF.DEFAULT.cluster_work_dir


class NodeGroup(BaseModel):
    az: Optional[str] = Field(None, description="可用域")
    flavor_id: Optional[str] = Field(None, description="规格")
    floating_ip: Optional[str] = Field(None, description="浮动ip")
    etcd: Optional[str] = Field(None, description="是否是etcd节点")

class ClusterTFVarsObject(BaseModel):
    id: Optional[str] = Field(None, description="项目id")
    cluster_name: Optional[str] = Field(None, description="集群名称")   
    image: Optional[str] = Field(None, description="用户id")
    k8s_masters: Optional[Dict[str, NodeGroup]] = Field(None, description="集群标签")
    k8s_nodes: Optional[Dict[str, NodeGroup]] = Field(None, description="集群状态")
    admin_subnet_id: Optional[str] = Field(None, description="管理子网id")
    bus_network_id: Optional[str] = Field(None, description="业务网络id")
    admin_network_id: Optional[str] = Field(None, description="管理网id")
    bus_subnet_id: Optional[str] = Field(None, description="业务子网id")
    floatingip_pool: Optional[str] = Field(None, description="节点配置")
    subnet_cidr: Optional[str] = Field(None, description="运行时类型")
    use_existing_network: Optional[str] = Field(None, description="是否使用已有网络")
    external_net: Optional[str] = Field(None, description="外部网络id")

def create_infrastructure(cluster:ClusterTFVarsObject):
    """使用Terraform创建基础设施"""
    try:
        
        # 将templat下的terraform目录复制到WORK_DIR/cluster.id目录下
        cluster_dir = os.path.join(WORK_DIR, str(cluster.id))
        os.makedirs(cluster_dir, exist_ok=True)
        res = subprocess.run(["cp", "-r", str(TERRAFORM_DIR), str(cluster_dir)], capture_output=True)
        os.chdir(os.path.join(cluster_dir, "terraform"))
        # 初始化terraform
        subprocess.run(["terraform", "init"], capture_output=True)
        # 遍历cluster.node_config，组装成
            

        tfvars_str = json.dumps(cluster, default=lambda o: o.__dict__, indent=2)
        #result = subprocess.run(["json2hcl", tfvars_str], capture_output=True, text=True)
        with open("output.tfvars.json", "w") as f:
            f.write(tfvars_str)
       
        # 执行terraform apply
        subprocess.run([
            "terraform",
            "apply",
            "-auto-approve",
            "-var-file=output.tfvars.json"
        ], check=True,capture_output=True, text=True) 
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"Terraform error: {e}")
        return False


def deploy_kubernetes(cluster):
    """使用Ansible部署K8s集群"""
    try:
        # 将templates下的ansible-deploy目录复制到WORK_DIR/cluster.id目录下
        cluster_dir = os.path.join(WORK_DIR, str(cluster.id))
        os.chdir(cluster_dir/"ansible-deploy")
        
        # 执行ansible-playbook
        subprocess.run([
            "ansible-playbook",
            "-i", "inventory/hosts.yaml",
            "cluster.yml",
        ], check=True)
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"Ansible error: {e}")
        return False
def get_cluster_kubeconfig(cluster):
    """获取集群的kubeconfig配置"""
    try:
        # 切换到terraform工作目录
        os.chdir(TERRAFORM_DIR)
        
        # 获取master节点IP
        result = subprocess.run(
            ["terraform", "output", "master_ip"],
            capture_output=True,
            text=True,
            check=True
        )
        master_ip = result.stdout.strip()
        
        # SSH连接到master节点获取kubeconfig
        result = subprocess.run(
            [
                "ssh",
                "-i", f"{TERRAFORM_DIR}/ssh_key",  # SSH私钥路径
                f"ubuntu@{master_ip}",
                "sudo cat /etc/kubernetes/admin.conf"
            ],
            capture_output=True,
            text=True,
            check=True
        )
        
        kubeconfig = result.stdout
        
        # 替换server地址为外部IP
        kubeconfig = kubeconfig.replace(
            "server: https://127.0.0.1:6443",
            f"server: https://{master_ip}:6443"
        )
        get_engine()
        # 保存kubeconfig到数据库
        with Session(get_engine()) as session:
            db_cluster = session.get(Cluster, cluster.id)
            db_cluster.kube_config = kubeconfig
            session.commit()
            
        return kubeconfig
        
    except subprocess.CalledProcessError as e:
        print(f"Error getting kubeconfig: {e}")
        return None
    
@celery_app.task
def create_cluster(cluster_dict):
    try:
        cluster = ClusterTFVarsObject(**cluster_dict)
        # 等待10s模拟集群创建过程
        # 1. 使用Terraform创建基础设施
        sleep(15)
        terraform_result = create_infrastructure(cluster)
        sleep(10)
        
        if not terraform_result:
            raise Exception("Terraform infrastructure creation failed")
        # 打印日志
        print("Terraform infrastructure creation succeeded")
        # 根据生成inventory
        # 复制script下面的host文件到WORK_DIR/cluster.id目录下
        cluster_dir = WORK_DIR / str(cluster.id)
        subprocess.run(["cp", "-r", str(ANSIBLE_DIR), str(cluster_dir)])
        #执行python3 host --list，将生成的内容转换为yaml格式写入到inventory/inventory.yaml文件中
        res = subprocess.run(["执行python3", "host", "--list"], capture_output=True)
        if res.returncode != 0:
            raise Exception("Error generating Ansible inventory")
        with open(cluster_dir/"ansible-deploy/inventory/inventory.yaml", "w") as f:
            f.write(res.stdout)
        # 执行ansible命令验证是否能够连接到所有节点
        res = subprocess.run([
            "ansible",
            "-i", "inventory/hosts.yaml",
            "-m", "ping",
            "all"
        ], capture_output=True)
        if res.returncode != 0:
            # Keep trying to connect to all nodes until successful
            max_attempts = 12  # Try for up to 1 minute (12 * 5 seconds)
            attempt = 1
            start_time = time.time()
            timeout = 1800  # 30 minutes in seconds
            while True:
                if time.time() - start_time > timeout:
                    raise Exception("Operation timed out after 30 minutes. Terminating execution.")
                print(f"Attempting to connect to all nodes with Ansible (attempt {attempt}/{max_attempts})...")
                res = subprocess.run([
                    "ansible",
                    "-i", "inventory/hosts",
                    "-m", "ping",
                    "all"
                ], capture_output=True)
                
                if res.returncode == 0:
                    print("Successfully connected to all nodes")
                    break
                
                attempt += 1
                if attempt > max_attempts:
                    raise Exception(f"Failed to connect to all nodes with Ansible ping after {max_attempts} attempts")
                
                print(f"Connection attempt failed. Waiting 5 seconds before retrying...")
                time.sleep(5)
                # Add timeout check - terminate after 30 minutes

        # 2. 使用Ansible部署K8s集群
        ansible_result = deploy_kubernetes(cluster)
        if not ansible_result:
            raise Exception("Ansible kubernetes deployment failed")
        # 获取集群的kube_config
        kube_config = get_cluster_kubeconfig(cluster)
        # 更新集群状态为running
        with Session(get_engine()) as session:
            db_cluster = session.get(cluster, cluster.id)
            db_cluster.status = 'running'
            db_cluster.kube_config = kube_config
            session.commit()
        
    except Exception as e:
        # 发生错误时更新集群状态为"失败"
          # 发生错误时更新集群状态为failed
        # with Session(get_engine()) as session:
        #     db_cluster = session.get(Database.Cluster, cluster.id)
        #     db_cluster.status = 'failed'
        #     db_cluster.error_message = str(e)
        #     session.commit()
        # 重新抛出异常供 Celery 处理
        raise

@celery_app.task
def create_node(cluster_id, node_name):
    
    try:
        # Add your cluster creation logic here
        pass
        
    except Exception as e:
        # 发生错误时更新集群状态为"失败"
        with Session(get_engine()) as session:
            cluster = session.get(Cluster, cluster.id)
            cluster.status = 'failed'
            cluster.error_message = str(e)
            session.commit()
        
        # 重新抛出异常供 Celery 处理
        raise
      
@celery_app.task(bind=True)
def install_component(cluster_id, node_name):
    with Session(get_engine()) as session:
        # cluster = session.get(Cluster, cluster_id)
        # if not cluster:
        #     raise ValueError(f"Cluster with ID {cluster_id} does not exist")
        # node = Node(cluster_id=cluster_id, name=node_name)
        # session.add(node)
        # session.commit()
        # return node.id
        pass
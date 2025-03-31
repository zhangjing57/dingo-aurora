from asyncio import sleep
import json
import logging
import os
import subprocess
import time
from typing import Any, Dict, Optional
from celery import Celery
from dingoops.api.model.cluster import ClusterObject
from dingoops.celery_api.ansible import AnsibleApi
from dingoops.db.models.cluster.models import Cluster
from pydantic import BaseModel, Field
from fastapi import Path
from pathlib import Path as PathLib
from requests import Session
from dingoops.celery_api.celery_app import celery_app
from dingoops.celery_api import CONF
from dingoops.db.engines.mysql import get_engine 
from ansible.executor.playbook_executor import PlaybookExecutor
# 用于导入资产文件
from ansible.inventory.manager import InventoryManager
from celery import current_task   
import yaml
        



BASE_DIR = os.getcwd()
TERRAFORM_DIR = os.path.join(BASE_DIR, "dingoops", "templates", "terraform")
ANSIBLE_DIR = os.path.join(BASE_DIR, "templates", "ansible-deploy")
WORK_DIR = CONF.DEFAULT.cluster_work_dir


class NodeGroup(BaseModel):
    az: Optional[str] = Field(None, description="可用域")
    flavor: Optional[str] = Field(None, description="规格")
    floating_ip: Optional[bool] = Field(None, description="浮动ip")
    etcd: Optional[bool] = Field(None, description="是否是etcd节点")

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
    use_existing_network: Optional[bool] = Field(None, description="是否使用已有网络")
    external_net: Optional[str] = Field(None, description="外部网络id")
    group_vars_path:  Optional[str] = Field(None, description="集群变量路径")
    number_of_etcd: Optional[int] = Field(None, description="ETCD节点数量")
    number_of_k8s_masters: Optional[int] = Field(None, description="K8s master节点数量")
    number_of_k8s_masters_no_etcd: Optional[int] = Field(None, description="不带ETCD的K8s master节点数量")
    number_of_k8s_masters_no_floating_ip: Optional[int] = Field(None, description="无浮动IP的K8s master节点数量")
    number_of_k8s_masters_no_floating_ip_no_etcd: Optional[int] = Field(None, description="无浮动IP且不带ETCD的K8s master节点数量")
    number_of_k8s_nodes: Optional[int] = Field(None, description="K8s worker节点数量")
    number_of_k8s_nodes_no_floating_ip: Optional[int] = Field(None, description="无浮动IP的K8s worker节点数量")
    password: Optional[str] = Field(None, description="密码")
    
    
def create_infrastructure(cluster:ClusterTFVarsObject):
    """使用Terraform创建基础设施"""
    try:
        
        # 将templat下的terraform目录复制到WORK_DIR/cluster.id目录下
        cluster_dir = os.path.join(WORK_DIR, "ansible-deploy", "inventory", str(cluster.id))
        dd = subprocess.run(["cp", "-LRp", os.path.join(WORK_DIR, "ansible-deploy", "inventory","sample-inventory"), str(cluster_dir)], capture_output=True)

        subprocess.run(["cp", "-r", str(TERRAFORM_DIR), str(cluster_dir)], capture_output=True)
        os.chdir(os.path.join(cluster_dir, "terraform"))
        # 初始化terraform
        os.environ['https_proxy']="172.20.3.88:1088"
        subprocess.run(["terraform", "init"], capture_output=True)
        cluster.group_vars_path = os.path.join(cluster_dir, "group_vars")
   
        tfvars_str = json.dumps(cluster, default=lambda o: o.__dict__, indent=2)
        with open("output.tfvars.json", "w") as f:
            f.write(tfvars_str)
       
        # 执行terraform apply
        # os.environ['OS_CLOUD']=cluster.region_name
        os.environ['OS_CLOUD']="shangdi"
        res = subprocess.run([
            "terraform",
            "apply",
            "-auto-approve",
            "-var-file=output.tfvars.json"
        ], capture_output=True, text=True) 
        return res
        
    except subprocess.CalledProcessError as e:
        print(f"Terraform error: {e}")
        return False

def wait_for_ansible_result(ansible_client: AnsibleApi, task_id: str, timeout: int = 3600, interval: int = 5) -> Optional[Dict[str, Any]]:

    start_time = time.time()
    logging.info(f"等待Ansible任务 {task_id} 完成...")
    
    while True:
        # 检查是否超时
        if time.time() - start_time > timeout:
            logging.error(f"等待Ansible任务 {task_id} 结果超时")
            return None
        
        try:
            # 获取任务结果
            result = ansible_client.get_playbook_result(task_id)
            
            # 检查任务是否完成且成功
            if result and result.get('status') == 'SUCCESS':
                logging.info(f"Ansible任务 {task_id} 执行成功")
                return result
            elif result and result.get('status') in ['FAILED', 'ERROR']:
                logging.error(f"Ansible任务 {task_id} 执行失败: {result}")
                return None
                
            # 任务仍在运行，继续等待
            logging.debug(f"Ansible任务 {task_id} 仍在执行中，继续等待...")
            
        except Exception as e:
            logging.warning(f"获取Ansible任务 {task_id} 结果时出错: {str(e)}，将继续尝试")
        
        # 等待一段时间再次检查
        time.sleep(interval)

def deploy_kubernetes(cluster:ClusterObject):
    """使用Ansible部署K8s集群"""
    try:
        # 将templates下的ansible-deploy目录复制到WORK_DIR/cluster.id目录下
        ansible_dir = os.path.join(WORK_DIR, str(cluster.id), "ansible-deploy")
        os.chdir(ansible_dir)
        hostfile = os.path.join(ansible_dir, "inventory", "hosts.yaml")

        ansible_server = {}
        if cluster.node_config[0].auth_type == "key":
            #创建private_key.pem文件
            with open(os.path.join(ansible_dir, "private_key.pem"), "w") as f:
                f.write(cluster.node_config[0].private_key)

            ansible_server = AnsibleApi(inventory_path=hostfile, default_username="root", private_key_file=os.path.join(ansible_dir, "private_key.pem"))
        else:
            ansible_server = AnsibleApi(inventory_path=hostfile, default_username="root", password=cluster.node_config[0].password)
        ansible_server.run_playbook([os.path.join()])
        res = wait_for_ansible_result(ansible_server)
        return  res
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
def create_cluster(cluster_tf_dict,cluster_dict):
    try:
        task_id = current_task.request.id
        
        cluster_tfvars = ClusterTFVarsObject(**cluster_tf_dict)
        cluster = ClusterTFVarsObject(**cluster_dict)
        # 1. 使用Terraform创建基础设施
        terraform_result = create_infrastructure(cluster_tfvars)
        
        if not terraform_result:
            raise Exception("Terraform infrastructure creation failed")
        # 打印日志
        print("Terraform infrastructure creation succeeded")
        # 根据生成inventory
        # 复制script下面的host文件到WORK_DIR/cluster.id目录下
        #执行python3 host --list，将生成的内容转换为yaml格式写入到inventory/inventory.yaml文件中
        host_file = os.path.join(WORK_DIR, "ansible-deploy", "inventory", str(cluster.id), "hosts")
        res = subprocess.run(["python3", host_file, "--list"], capture_output=True, text=True)
        if res.returncode != 0:
            raise Exception("Error generating Ansible inventory")
        aaa = res.stdout
        # Convert JSON output to Python object
        inventory_json = json.loads(res.stdout)
        
        # Convert Python object to YAML
        inventory_yaml = yaml.dump(inventory_json, default_flow_style=False)
        
        inventory_file = os.path.join(WORK_DIR, "ansible-deploy", "inventory", str(cluster.id), "inventory.yaml")
        with open(inventory_file, "w") as f:
            f.write(inventory_yaml)
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
        #阻塞线程，直到ansible_client.get_playbook_result()返回结果成功
        
        
        
        if not ansible_result:
            # 更新数据库的状态为failed
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
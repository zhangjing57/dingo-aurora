from asyncio import sleep
import json
import os
import subprocess
from databases import Database
from fastapi import Path
from pathlib import Path as PathLib
from requests import Session
from celery_api.celery_app import celery_app
from api.model.cluster import ClusterObject, NodeGroup,ClusterTFVarsObject
from services import CONF


BASE_DIR = os.getcwd()
TERRAFORM_DIR = os.path.join(BASE_DIR, "dingoops", "templates", "terraform")
ANSIBLE_DIR = os.path.join(BASE_DIR, "templates", "ansible-deploy")
WORK_DIR = CONF.DEFAULT.cluster_work_dir

def generate_k8s_nodes(cluster, k8s_masters, k8s_nodes):
    for idx, node in enumerate(cluster.node_config):
        for y in range(node.count):
            if node.role == 'master':
                    #index=master+node
                if y == 0:
                    float_ip=True
                else:
                    float_ip=False
                if y<3:
                    etcd = True
                else:
                    etcd =False
                k8s_masters[f"master-{int(y)+1}"] = NodeGroup(
                    az=get_az_value(node.type),
                    flavor_id=node.flavor_id,
                    floating_ip=float_ip, 
                    etcd=etcd
                )
            if node.role == 'worker':
                    #index=master+node
                k8s_nodes[f"node-{int(y)+1}"] = NodeGroup(
                    az=get_az_value(node.type),
                    flavor_id=node.flavor_id,
                    floating_ip=False, 
                    etcd=True
                )

def get_az_value(node_type):
    """根据节点类型返回az值"""
    return "nova" if node_type == "vm" else ""

def create_infrastructure(cluster:ClusterObject):
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
        k8s_masters = {}
        k8s_nodes = {}
        generate_k8s_nodes(cluster, k8s_masters, k8s_nodes)
            
        # 创建terraform变量文件
        tfvars = ClusterTFVarsObject(
            cluster_name=cluster.name,
            image=cluster.node_config[0].image,
            k8s_masters=k8s_masters,
            k8s_nodes=k8s_nodes,
            admin_subnet_id=cluster.network_config.admin_subnet_id,
            bus_subnet_id=cluster.network_config.admin_subnet_id,
            admin_network_id=cluster.network_config.admin_subnet_id,
            bus_network_id=cluster.network_config.bus_network_id,
            floatingip_pool="physnet2",
            subnet_cidr=cluster.network_config.pod_cidr,
            external_net=
            use_existing_network=True)
        tfvars_str = json.dumps(tfvars, default=lambda o: o.__dict__, indent=2)
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
        cluster_dir = WORK_DIR / str(cluster.id)
        subprocess.run(["cp", "-r", str(ANSIBLE_DIR), str(cluster_dir)])
        os.chdir(cluster_dir/"ansible-deploy")
        
        # 执行ansible-playbook
        subprocess.run([
            "ansible-playbook",
            "-i", "inventory/hosts",
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
        
        # 保存kubeconfig到数据库
        with Session(Database.engine) as session:
            db_cluster = session.get(Database.Cluster, cluster.id)
            db_cluster.kube_config = kubeconfig
            session.commit()
            
        return kubeconfig
        
    except subprocess.CalledProcessError as e:
        print(f"Error getting kubeconfig: {e}")
        return None
    
@celery_app.task
def create_cluster(cluster):
    try:
        # 等待10s模拟集群创建过程
        # 1. 使用Terraform创建基础设施
        terraform_result = create_infrastructure(cluster)
        if not terraform_result:
            raise Exception("Terraform infrastructure creation failed")
           
        # 2. 使用Ansible部署K8s集群
        ansible_result = deploy_kubernetes(cluster)
        if not ansible_result:
            raise Exception("Ansible kubernetes deployment failed")
        # 获取集群的kube_config
        kube_config = get_cluster_kubeconfig(cluster)
        # 更新集群状态为running
        with Session(Database.engine) as session:
            db_cluster = session.get(Database.Cluster, cluster.id)
            db_cluster.status = 'running'
            db_cluster.kube_config = kube_config
            session.commit()
        
    except Exception as e:
        # 发生错误时更新集群状态为"失败"
          # 发生错误时更新集群状态为failed
        with Session(Database.engine) as session:
            db_cluster = session.get(Database.Cluster, cluster.id)
            db_cluster.status = 'failed'
            db_cluster.error_message = str(e)
            session.commit()
        # 重新抛出异常供 Celery 处理
        raise

@celery_app.task
def create_node(cluster_id, node_name):
    
    try:
        # Add your cluster creation logic here
        pass
        
    except Exception as e:
        # 发生错误时更新集群状态为"失败"
        with Session(Database.engine) as session:
            cluster = session.get(Database.Cluster, cluster.id)
            cluster.status = 'failed'
            cluster.error_message = str(e)
            session.commit()
        
        # 重新抛出异常供 Celery 处理
        raise
      
@celery_app.task(bind=True)
def install_component(cluster_id, node_name):
    with Session(Database.engine) as session:
        cluster = session.get(Database.Cluster, cluster_id)
        if not cluster:
            raise ValueError(f"Cluster with ID {cluster_id} does not exist")
        node = Database.Node(cluster_id=cluster_id, name=node_name)
        session.add(node)
        session.commit()
        return node.id
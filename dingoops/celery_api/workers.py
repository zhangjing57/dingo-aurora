from asyncio import sleep
import os
import subprocess
from fastapi import Path
from requests import Session
from dingoops import database
from celery import celery_app
from services import CONF


BASE_DIR = Path(__file__).parent.parent.parent
TERRAFORM_DIR = BASE_DIR / "templates" / "terraform"
ANSIBLE_DIR = BASE_DIR / "templates" / "ansible-deploy"
WORK_DIR = CONF.default.work_dir

def create_infrastructure(cluster):
    """使用Terraform创建基础设施"""
    try:
        
        # 将templat下的terraform目录复制到WORK_DIR/cluster.id目录下
        cluster_dir = WORK_DIR / str(cluster.id)
        cluster_dir.mkdir(parents=True, exist_ok=True)
        subprocess.run(["cp", "-r", str(TERRAFORM_DIR), str(cluster_dir)])
        os.chdir(cluster_dir)
        # 初始化terraform
        subprocess.run(["terraform", "init"], check=True)
        
        # 创建terraform变量文件
        with open("terraform.tfvars", "w") as f:
            f.write(f"""
            cluster_name = "{cluster.name}"
            region = "{cluster.region}"
            node_count = {cluster.node_count}
            instance_type = "{cluster.instance_type}"
            """)
        
        # 应用terraform配置
        subprocess.run(["terraform", "apply", "-auto-approve"], check=True)
        
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
        with Session(database.engine) as session:
            db_cluster = session.get(database.Cluster, cluster.id)
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
        with Session(database.engine) as session:
            db_cluster = session.get(database.Cluster, cluster.id)
            db_cluster.status = 'running'
            db_cluster.kube_config = kube_config
            session.commit()
        
    except Exception as e:
        # 发生错误时更新集群状态为"失败"
          # 发生错误时更新集群状态为failed
        with Session(database.engine) as session:
            db_cluster = session.get(database.Cluster, cluster.id)
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
        with Session(database.engine) as session:
            cluster = session.get(database.Cluster, cluster.id)
            cluster.status = 'failed'
            cluster.error_message = str(e)
            session.commit()
        
        # 重新抛出异常供 Celery 处理
        raise
      
@celery_app.task(bind=True)
def install_component(cluster_id, node_name):
    with Session(database.engine) as session:
        cluster = session.get(database.Cluster, cluster_id)
        if not cluster:
            raise ValueError(f"Cluster with ID {cluster_id} does not exist")
        node = database.Node(cluster_id=cluster_id, name=node_name)
        session.add(node)
        session.commit()
        return node.id
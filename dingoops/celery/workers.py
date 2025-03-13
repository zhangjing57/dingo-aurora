from requests import Session
from dingoops import database
from dingoops.celery import celery_app

@celery_app.task
def create_cluster(cluster):
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
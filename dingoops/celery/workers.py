from dingoops import database
from dingoops.celery import celery_app
from sqlmodel import Session

@celery_app.task
def create_cluster(cluster_name):
    with Session(database.engine) as session:
        cluster = database.Cluster(name=cluster_name)
        session.add(cluster)
        session.commit()
        return cluster.id

@celery_app.task
def create_node(cluster_id, node_name):
    with Session(database.engine) as session:
        cluster = session.get(database.Cluster, cluster_id)
        if not cluster:
            raise ValueError(f"Cluster with ID {cluster_id} does not exist")
        node = database.Node(cluster_id=cluster_id, name=node_name)
        session.add(node)
        session.commit()
        return node.id
      
@celery_app.task
def install_component(cluster_id, node_name):
    with Session(database.engine) as session:
        cluster = session.get(database.Cluster, cluster_id)
        if not cluster:
            raise ValueError(f"Cluster with ID {cluster_id} does not exist")
        node = database.Node(cluster_id=cluster_id, name=node_name)
        session.add(node)
        session.commit()
        return node.id
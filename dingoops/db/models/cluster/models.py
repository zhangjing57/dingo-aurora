# 数据表对应的model对象

from __future__ import annotations

from sqlalchemy import JSON, Column, MetaData, String, Table, Text, DateTime, Integer, Boolean
from sqlalchemy.orm import declarative_base

Base = declarative_base()

# 集群对象
class Cluster(Base):
    __tablename__ = "ops_cluster_info"

    id = Column(String(length=128), primary_key= True, nullable=False, index=True, unique=False)
    name = Column(String(length=128), primary_key= True, nullable=False, index=True, unique=False)
    project_id = Column(String(length=128), nullable=True)
    user_id = Column(String(length=128), nullable=True)
    labels = Column(String(length=128), nullable=True)
    status = Column(String(length=128), nullable=True)
    status_msg = Column(String(length=128), nullable=True)
    region_name = Column(String(length=128), nullable=True)
    admin_network_id = Column(String(length=128), nullable=True)
    admin_subnet_id = Column(String(length=128), nullable=True)
    bus_network_id = Column(String(length=128), nullable=True)
    bus_subnet_id = Column(String(length=128), nullable=True)
    runtime = Column(String(length=128), nullable=True)
    type = Column(String(length=128), nullable=True)
    service_cidr = Column(String(length=255), nullable=True)
    bus_address = Column(String(length=255), nullable=True)
    api_address = Column(String(length=255), nullable=True)
    cni = Column(String(length=255), nullable=True)
    kube_config = Column(String(length=255), nullable=True)
    
    create_time = Column(DateTime, nullable=True)
    update_time = Column(DateTime, nullable=True)
    description = Column(String(length=255), nullable=True)
    extra = Column(String(length=255), nullable=True)
    
    
# 节点对象
class nodeinfo(Base):
    __tablename__ = "ops_node_info"

    id = Column(String(length=128), primary_key= True, nullable=False, index=True, unique=False)
    parent_id = Column(String(length=128), nullable=True)
    asset_type_name = Column(String(length=128), nullable=True)
    asset_type_name_zh = Column(String(length=128), nullable=True)
    queue = Column(Integer, default=0, nullable= False)
    description = Column(String(length=255), nullable=True)
    extra = Column(String(length=255), nullable=True)
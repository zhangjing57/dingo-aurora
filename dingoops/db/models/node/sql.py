# 数据表对应的model对象

from __future__ import annotations

from sqlalchemy.orm import sessionmaker, aliased
from sqlalchemy import create_engine, func
from typing_extensions import assert_type

from dingoops.db.engines.mysql import get_session
from dingoops.db.models.cluster.models import Cluster,Taskinfo
from dingoops.db.models.node.models import NodeInfo
from enum import Enum

cluster_dir_dic= {"asset_type":Cluster.type,"create_time":Cluster.create_time,
              "name":Cluster.name,"status":Cluster.status,"region_name":Cluster.region_name}

class NodeSQL:

    @classmethod
    def list_nodes(cls, query_params, page=1, page_size=10, sort_keys=None, sort_dirs="ascend"):
        # 获取session
        session = get_session()
        with session.begin():
            # 根据query_params查询数据
            query = session.query(NodeInfo)
            # 查询语句

            # 数据库查询参数
            if "name" in query_params and query_params["name"]:
                query = query.filter(NodeInfo.name.like('%' + query_params["name"] + '%'))
            if "cluster_id" in query_params and query_params["cluster_id"]:
                query = query.filter(NodeInfo.cluster_id == query_params["cluster_id"])
            # 总数
            count = query.count()
            # 排序
            if sort_keys is not None and sort_keys in cluster_dir_dic:
                if sort_dirs == "ascend" or sort_dirs is None :
                    query = query.order_by(cluster_dir_dic[sort_keys].asc())
                elif sort_dirs == "descend":
                    query = query.order_by(cluster_dir_dic[sort_keys].desc())
            else:
                query = query.order_by(Cluster.create_time.desc())
            # 分页条件
            page_size = int(page_size)
            page_num = int(page)
            # 查询所有数据
            if page_size == -1:
                return count, query.all()
            # 页数计算
            start = (page_num - 1) * page_size
            query = query.limit(page_size).offset(start)
            cluster_list = query.all()
            # 返回
            return count, cluster_list

    @classmethod
    def create_nodes(cls, node_list):
        # Session = sessionmaker(bind=engine, expire_on_commit=False)
        # session = Session()
        session = get_session()
        with session.begin():
            for node in node_list:
                session.add(node)

    @classmethod
    def update_node(cls, cluster):
        # Session = sessionmaker(bind=engine, expire_on_commit=False)
        # session = Session()
        session = get_session()
        with session.begin():
            session.merge(cluster)
# 数据表对应的model对象

from __future__ import annotations

from sqlalchemy.orm import sessionmaker, aliased
from sqlalchemy import create_engine, func
from typing_extensions import assert_type

from db.engines.mysql import get_session
from db.models.cluster.models import Cluster

from enum import Enum

#链接数据库，可以使用配置文件进行定义
# engine = create_engine("mysql+pymysql://root:HworLIIDvmTRsPfQauNskuJF8PcoTuULfu3dEHFg@10.220.56.254:3306/dingoops?charset=utf8mb3", echo=True)
# 资产排序字段字典
cluster_dir_dic= {"asset_type":Cluster.type,"create_time":Cluster.create_time,
              "name":Cluster.name,"status":Cluster.status,"region_name":Cluster.region_name}
class ClusterSQL:

    @classmethod
    def list_cluster(cls, query_params, page=1, page_size=10, sort_keys=None, sort_dirs="ascend"):
        # 获取session
        session = get_session()
        with session.begin():
            # 根据query_params查询数据
            query = session.query(Cluster)
            # 查询语句

            # 数据库查询参数
            if "name" in query_params and query_params["name"]:
                query = query.filter(Cluster.name.like('%' + query_params["name"] + '%'))
            if "id" in query_params and query_params["id"]:
                query = query.filter(Cluster.id == query_params["id"])
            if "user_id" in query_params and query_params["user_id"]:
               query = query.filter(Cluster.user_id == query_params["user_id"])
            if "project_id" in query_params and query_params["project_id"]:
                query = query.filter(Cluster.project_id == query_params["project_id"])
            if "status" in query_params and query_params["status"]:
                query = query.filter(Cluster.status.like('%' + query_params["status"] + '%'))
            if "region_name" in query_params and query_params["region_name"]:
                query = query.filter(Cluster.region_name.like('%' + query_params["region_name"] + '%'))
            if "network_id" in query_params and query_params["network_id"]:
                query = query.filter(Cluster.network_id == query_params["network_id"])
            if "subnet_id" in query_params and query_params["subnet_id"]:
                query = query.filter(Cluster.subnet_id == query_params["subnet_id"])
            if "runtime" in query_params and query_params["runtime"]:
                query = query.filter(Cluster.runtime.like('%' + query_params["runtime"] + '%'))
            if "type" in query_params and query_params["type"]:
                query = query.filter(Cluster.type.like('%' + query_params["type"] + '%'))
            if "service_cidr" in query_params and query_params["service_cidr"]:
                query = query.filter(Cluster.service_cidr.like('%' + query_params["service_cidr"] + '%'))
            if "bus_address" in query_params and query_params["bus_address"]:
                query = query.filter(Cluster.bus_address.like('%' + query_params["bus_address"] + '%'))
            if "api_address" in query_params and query_params["api_address"]:
                query = query.filter(Cluster.api_address.like('%' + query_params["api_address"] + '%'))
            if "cni" in query_params and query_params["cni"]:
                query = query.filter(Cluster.cni.like('%' + query_params["cni"] + '%'))
            if "user_name" in query_params and query_params["user_name"]:
                query = query.filter(Cluster.user_name.like('%' + query_params["user_name"] + '%'))
            if "manufacture_id" in query_params and query_params["manufacture_id"]:
                query = query.filter(Cluster.id == query_params["manufacture_id"])
            if "manufacture_name" in query_params and query_params["manufacture_name"]:
                query = query.filter(Cluster.name.like('%' + query_params["manufacture_name"] + '%'))
            # 总数
            count = query.count()
            # 排序
            if sort_keys is not None and sort_keys in cluster_dir_dic:
                if sort_dirs == "ascend" or sort_dirs is None :
                    query = query.order_by(cluster_dir_dic[sort_keys].asc())
                elif sort_dirs == "descend":
                    query = query.order_by(cluster_dir_dic[sort_keys].desc())
            else:
                query = query.order_by(Cluster.create_date.desc())
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
    def get_cluster_info(cls, asset_name=None, page=1, page_size=10, field=None, dir="ascend"):
        # Session = sessionmaker(bind=engine,expire_on_commit=False)
        # session = Session()
        
            return count, assert_list


    @classmethod
    def create_cluster(cls, cluster):
        # Session = sessionmaker(bind=engine, expire_on_commit=False)
        # session = Session()
        session = get_session()
        with session.begin():
            session.add(cluster)

    @classmethod
    def delete_cluster(cls, catalog, name):
        # Session = sessionmaker(bind=engine, expire_on_commit=False)
        # session = Session()
        session = get_session()
        with session.begin():
            return session.query(AssetBasicInfo).filter(AssetBasicInfo.asset_category == catalog).filter(AssetBasicInfo.name == name).first()

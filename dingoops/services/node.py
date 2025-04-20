# 资产的service层
import json
import logging
import os
import shutil
import uuid
from io import BytesIO

import pandas as pd
from datetime import datetime

from openpyxl.reader.excel import load_workbook
from openpyxl.styles import Border, Side
from typing_extensions import assert_type

from dingoops.celery_api.celery_app import celery_app
from dingoops.db.models.cluster.sql import ClusterSQL
from dingoops.db.models.node.sql import NodeSQL
from dingoops.db.models.node.sql import NodeSQL
from math import ceil
from oslo_log import log
from dingoops.api.model.cluster import ClusterTFVarsObject, NodeGroup, ClusterObject
from dingoops.db.models.cluster.models import Cluster as ClusterDB
from dingoops.db.models.node.models import NodeInfo as NodeDB
from dingoops.utils import neutron

from dingoops.services.custom_exception import Fail
from dingoops.services.system import SystemService



LOG = log.getLogger(__name__)

# 定义边框样式
thin_border = Border(
    left=Side(border_style="thin", color="000000"),  # 左边框
    right=Side(border_style="thin", color="000000"),  # 右边框
    top=Side(border_style="thin", color="000000"),  # 上边框
    bottom=Side(border_style="thin", color="000000")  # 下边框
)

system_service = SystemService()

class NodeService:

    def get_az_value(self, node_type):
        """根据节点类型返回az值"""
        return "nova" if node_type == "vm" else ""

    def generate_k8s_nodes(self, cluster, k8s_masters, k8s_nodes):
        for idx, node in enumerate(cluster.node_config):
            if node.get("role") == "master":
                for i in range(node.count):
                    if i == 0:
                        float_ip_bool = True
                    else:
                        float_ip_bool = False
                    if i < 3:
                        etcd_bool = True
                    else:
                        etcd_bool = False
                    k8s_masters[f"master-{int(i) + 1}"] = NodeGroup(
                        az=self.get_az_value(node.type),
                        flavor_id=node.flavor_id,
                        floating_ip=float_ip_bool,
                        etcd=etcd_bool
                    )
            if node.get("role") == "worker":
                for i in range(node.count):
                    k8s_nodes[f"node-{int(i) + 1}"] = NodeGroup(
                        az=self.get_az_value(node.type),
                        flavor_id=node.flavor_id,
                        floating_ip=False,
                        etcd=False
                    )

    # 查询资产列表
    @classmethod
    def list_nodes(cls, query_params, page, page_size, sort_keys, sort_dirs):
        # 业务逻辑
        try:
            # 按照条件从数据库中查询数据
            count, data = NodeSQL.list_nodes(query_params, page, page_size, sort_keys, sort_dirs)
            # 返回数据
            res = {}
            # 页数相关信息
            if page and page_size:
                res['currentPage'] = page
                res['pageSize'] = page_size
                res['totalPages'] = ceil(count / int(page_size))
            res['total'] = count
            res['data'] = data
            return res
        except Exception as e:
            import traceback
            traceback.print_exc()
            return None

    def get_node(self, cluster_id):
        if not cluster_id:
            return None
        # 详情
        try:
            # 根据id查询
            query_params = {}
            query_params["id"] = cluster_id
            res = self.list_nodes(query_params, 1, 10, None, None)
            # 空
            if not res or not res.get("data"):
                return None
            # 返回第一条数据
            return res.get("data")[0]
        except Exception as e:
            import traceback
            traceback.print_exc()
            raise e

    def delete_node(self, node_id):
        if not node_id:
            return None
        # 详情
        try:
            # 更新集群状态为删除中

            # 根据id查询
            query_params = {}
            query_params["id"] = node_id
            res = self.list_nodes(query_params, 1, 10, None, None)
            # 空
            if not res or not res.get("data"):
                return None
            # 返回第一条数据
            node = res.get("data")[0]
            node.status = "deleting"
            # 保存对象到数据库
            res = ClusterSQL.update_cluster(node)
            # 调用celery_app项目下的work.py中的delete_cluster方法
            result = celery_app.send_task("dingoops.celery_api.workers.delete_cluster", args=[node_id])
            if result.get():
                # 删除成功，更新数据库状态
                node.status = "deleted"
                res = ClusterSQL.update_cluster(node)
            else:
                # 删除失败，更新数据库状态
                node.status = "delete_failed"
                res = ClusterSQL.update_cluster(node)
            return res.get("data")[0]
        except Exception as e:
            import traceback
            traceback.print_exc()
            raise e

    def convert_nodeinfo_todb(self, cluster:ClusterObject):
        nodeinfo_list = []

        if not cluster or not hasattr(cluster, 'node_config') or not cluster.node_config:
            return nodeinfo_list

        # 遍历 node_config 并转换为 Nodeinfo 对象
        for node_conf in cluster.node_config:
            node_db = NodeDB()
            node_db.node_type = node_conf.type
            node_db.cluster_id = cluster.id
            node_db.cluster_name = cluster.name
            node_db.region_name = cluster.region_name
            node_db.role = node_conf.role
            node_db.user = node_conf.user
            node_db.password = node_conf.password
            node_db.private_key = node_conf.private_key
            node_db.openstack_id = node_conf.openstack_id

            # 节点的ip地址，创建虚拟机的时候不知道，只能等到后面从集群中获取ip地址，node的名字如何匹配，节点的状态是not ready还是ready？
            node_db.admin_address = ""
            node_db.name = ""
            node_db.status = ""
            node_db.bus_address = ""

            nodeinfo_list.append(node_db)
        return nodeinfo_list

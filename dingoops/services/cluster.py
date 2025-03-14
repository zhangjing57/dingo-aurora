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

from celery_api.celery_app import celery_app
from db.models.asset.sql import AssetSQL
from math import ceil
from oslo_log import log

from services.custom_exception import Fail
from services.system import SystemService



LOG = log.getLogger(__name__)

# 定义边框样式
thin_border = Border(
    left=Side(border_style="thin", color="000000"),  # 左边框
    right=Side(border_style="thin", color="000000"),  # 右边框
    top=Side(border_style="thin", color="000000"),  # 上边框
    bottom=Side(border_style="thin", color="000000")  # 下边框
)

system_service = SystemService()

class ClusterService:

    # 查询资产列表
    def list_clusters(self, query_params, page, page_size, sort_keys, sort_dirs):
        # 业务逻辑
        try:
            # 按照条件从数据库中查询数据
            count, data = AssetSQL.list_asset(query_params, page, page_size, sort_keys, sort_dirs)
            # 数据处理
            ret = []
            # 遍历
            for r in data:
                # 填充数据
                temp = {}
                temp["asset_id"] = r.id
                temp["asset_type_id"] = r.asset_type_id
                temp["asset_category"] = r.asset_category
                temp["asset_type"] = r.asset_type
                temp["asset_type_name_zh"] = r.asset_type_name_zh
                temp["asset_name"] = r.name
                temp["equipment_number"] = r.equipment_number
                temp["sn_number"] = r.sn_number
                temp["asset_number"] = r.asset_number
                temp["asset_status"] = r.asset_status
                temp["asset_status_description"] = r.asset_status_description
                temp["asset_description"] = r.description
                temp["extra"] = r.extra
                temp["extend_column_extra"] = r.extend_column_extra
                # 厂商信息
                temp_manufacture = {}
                temp_manufacture["id"] = r.manufacture_id
                temp_manufacture["name"] = r.manufacture_name
                temp_manufacture["description"] = r.manufacture_description
                temp_manufacture["extra"] = r.manufacture_extra
                temp["asset_manufacturer"] = temp_manufacture
                # 位置信息
                temp_position = {}
                temp_position["id"] = r.position_id
                temp_position["frame_position"] = r.position_frame_position
                temp_position["cabinet_position"] = r.position_cabinet_position
                temp_position["u_position"] = r.position_u_position
                temp_position["description"] = r.position_description
                temp["asset_position"] = temp_position
                # 合同信息
                temp_contract = {}
                temp_contract["id"] = r.contract_id
                temp_contract["contract_number"] = r.contract_number
                temp_contract["purchase_date"] = None if r.contract_purchase_date is None else r.contract_purchase_date.timestamp() * 1000
                temp_contract["batch_number"] = r.contract_batch_number
                temp_contract["description"] = r.contract_description
                temp["asset_contract"] = temp_contract
                # 归属信息
                temp_belong = {}
                temp_belong["id"] = r.belong_id
                temp_belong["department_id"] = r.belong_department_id
                temp_belong["department_name"] = r.belong_department_name
                temp_belong["user_id"] = r.belong_user_id
                temp_belong["user_name"] = r.belong_user_name
                temp_belong["tel_number"] = r.belong_tel_number
                temp_belong["description"] = r.belong_contract_description
                temp["asset_belong"] = temp_belong
                # 租户信息
                temp_cutomer = {}
                temp_cutomer["id"] = r.customer_id
                temp_cutomer["customer_id"] = r.customer_customer_id
                temp_cutomer["customer_name"] = r.customer_customer_name
                temp_cutomer["rental_duration"] = r.customer_rental_duration
                temp_cutomer["start_date"] = None if r.customer_start_date is None else r.customer_start_date.timestamp() * 1000
                temp_cutomer["end_date"] = None if r.customer_end_date is None else r.customer_end_date.timestamp() * 1000
                temp_cutomer["vlan_id"] = r.customer_vlan_id
                temp_cutomer["float_ip"] = r.customer_float_ip
                temp_cutomer["band_width"] = r.customer_band_width
                temp_cutomer["description"] = r.customer_description
                temp["asset_customer"] = temp_cutomer
                # 配件信息
                temp["asset_part"] = self.list_assets_parts(r.id)
                # 流量信息 列表上不需要
                # temp["asset_flow"] = self.list_assets_flows(r.id)
                # 加入列表
                ret.append(temp)

            # 返回数据
            res = {}
            # 页数相关信息
            if page and page_size:
                res['currentPage'] = page
                res['pageSize'] = page_size
                res['totalPages'] = ceil(count / int(page_size))
            res['total'] = count
            res['data'] = ret
            return res
        except Exception as e:
            import traceback
            traceback.print_exc()
            return None

    def create_cluster(self, cluster):
        # 数据校验 todo
        try:
            cluster_info_db = self.convert_clusterinfo_todb(cluster)
            # 保存对象到数据库
            cluster_id = AssetSQL.create_cluster(cluster_info_db)
            # 保存节点信息到数据库
            # cluster_id = AssetSQL.create_cluster(cluster_info_db)
            # 调用celery_app项目下的work.py中的create_cluster方法
            result = celery_app.send_task("work.create_cluster", args=[cluster])
            logging.info(result.get())
        except Fail as e:
            raise e
        except Exception as e:
            import traceback
            traceback.print_exc()
            raise e
        # 成功返回资产id
        return cluster_id
    
    def convert_clusterinfo_todb(cluster):
        pass

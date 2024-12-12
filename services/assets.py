# 资产的service层
import json
import os
import uuid
import pandas as pd
from datetime import datetime

from db.models.asset.models import AssetBasicInfo, AssetManufacturesInfo, AssetPartsInfo, AssetPositionsInfo, \
    AssetContractsInfo, AssetCustomersInfo, AssetBelongsInfo
from db.models.asset.sql import AssetSQL
from math import ceil
from oslo_log import log

from utils.constant import ASSET_TEMPLATE_FILE_DIR, asset_equipment_columns, asset_basic_info_columns

LOG = log.getLogger(__name__)

class AssetsService:

    # 查询资产列表
    def list_assets(self, asset_id, asset_name, page, page_size, sort_keys, sort_dirs):
        # 业务逻辑
        try:
            # 按照条件从数据库中查询数据
            count, data = AssetSQL.list_asset(asset_id, asset_name, page, page_size, sort_keys, sort_dirs)
            # 数据处理
            ret = []
            # 遍历
            for r in data:
                # 填充数据
                temp = {}
                temp["asset_id"] = r.id
                temp["asset_type_id"] = r.asset_type_id
                temp["asset_name"] = r.name
                temp["equipment_number"] = r.equipment_number
                temp["sn_number"] = r.sn_number
                temp["asset_number"] = r.asset_number
                temp["asset_status"] = r.asset_status
                temp["asset_description"] = r.description
                temp["extra"] = r.extra
                # 厂商信息
                temp_manufacture = {}
                temp_manufacture["id"] = r.manufacture_id
                temp_manufacture["name"] = r.manufacture_name
                temp_manufacture["description"] = r.manufacture_description
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



# 返回对应数据
#     return {
#         "flag": True,
#         "errorCode": None,
#         "errorMessage": None,
#         "resData": {
#             "currentPage": 1,
#             "pageSize": 10,
#             "total": count,
#             "totalPages": 2,
#             "data":
#                 [
#                     {
#                         "uuid":"5a1c563b91fd4cbfaf518cd6e8a42059",
#                         "asset_name":"服务器",
#                         "asset_description":"服务器描述",
#                     }
#                 ]
#         }
#     }



    def create_asset(self, asset):
        # 业务校验 todo
        if asset is None:
            return None
        # 资产id
        asset_id = None
        try:
            # 数据组装
            # 1、资产基础信息
            asset_basic_info_db = self.convert_asset_basic_info_db(asset)
            # 资产的id重新生成覆盖
            asset.asset_id = asset_basic_info_db.id
            asset_id = asset_basic_info_db.id
            # 2、资产厂商信息
            asset_manufacture_info_db = self.convert_asset_manufacturer_info_db(asset)
            # 3、资产位置信息
            asset_position_info_db = self.convert_asset_position_info_db(asset)
            # 4、资产合同信息
            asset_contract_info_db = self.convert_asset_contract_info_db(asset)
            # 5、资产归属信息
            asset_belong_info_db = self.convert_asset_belong_info_db(asset)
            # 6、资产租赁信息
            asset_customer_info_db = self.convert_asset_customer_info_db(asset)
            # 7、资产配件信息
            asset_part_info_db = self.convert_asset_part_info_db(asset)
            # 保存对象
            AssetSQL.create_asset(asset_basic_info_db, asset_manufacture_info_db, asset_position_info_db, asset_contract_info_db, asset_belong_info_db, asset_customer_info_db, asset_part_info_db)
        except Exception as e:
            import traceback
            traceback.print_exc()
        # 成功返回资产id
        return asset_id


    # 资产创建时基础对象数据转换
    def convert_asset_basic_info_db(self, asset):
        # 数据转化为db对象
        asset_basic_info_db = AssetBasicInfo(
            id=uuid.uuid4().hex,
            asset_type_id=asset.asset_type_id,
            name=asset.asset_name,
            description=asset.asset_description,
            equipment_number=asset.equipment_number,
            sn_number=asset.sn_number,
            asset_number=asset.asset_number,
            asset_status=asset.asset_status,
            extra=json.dumps(asset.extra)
        )
        # 返回数据
        return asset_basic_info_db


    # 资产创建时厂商对象数据转换
    def convert_asset_manufacturer_info_db(self, asset):
        # 判空
        if asset.asset_manufacturer is None:
            return None
        # 数据转化为db对象
        asset_manufacturer_info_db = AssetManufacturesInfo(
            id=uuid.uuid4().hex,
            asset_id=asset.asset_id,
            name=asset.asset_manufacturer.name,
            description=asset.asset_manufacturer.description,
        )
        # 返回数据
        return asset_manufacturer_info_db


    # 资产创建时配件对象数据转换
    def convert_asset_part_info_db(self, asset):
        # 判空
        if asset.asset_part is None:
            return None
        # 配件列表
        asset_part_info_dbs = []
        # 遍历
        for temp in asset.asset_part:
            # 数据转化为db对象
            asset_part_info_db = AssetPartsInfo(
                id=uuid.uuid4().hex,
                asset_id=asset.asset_id,
                name=temp.name,
                part_type=temp.part_type,
                part_brand=temp.part_brand,
                part_config=temp.part_config,
                part_number=temp.part_number,
                personal_used_flag=temp.personal_used_flag,
                surplus=temp.surplus,
                description=temp.description,
            )
            #
            asset_part_info_dbs.append(asset_part_info_db)
        # 返回数据
        return asset_part_info_dbs


    # 资产创建时位置对象数据转换
    def convert_asset_position_info_db(self, asset):
        # 判空
        if asset.asset_position is None:
            return None
        # 数据转化为db对象
        asset_position_info_db = AssetPositionsInfo(
            id=uuid.uuid4().hex,
            asset_id=asset.asset_id,
            frame_position=asset.asset_position.frame_position,
            cabinet_position=asset.asset_position.cabinet_position,
            u_position=asset.asset_position.u_position,
            description=asset.asset_position.description,
        )
        # 返回数据
        return asset_position_info_db


    # 资产创建时合同对象数据转换
    def convert_asset_contract_info_db(self, asset):
        # 判空
        if asset.asset_contract is None:
            return None
        # 数据转化为db对象
        asset_contract_info_db = AssetContractsInfo(
            id=uuid.uuid4().hex,
            asset_id=asset.asset_id,
            contract_number=asset.asset_contract.contract_number,
            purchase_date=None if asset.asset_contract.purchase_date is None else datetime.fromtimestamp(asset.asset_contract.purchase_date/1000),
            batch_number=asset.asset_contract.batch_number,
            description=asset.asset_contract.description,
        )
        # 返回数据
        return asset_contract_info_db


    # 资产创建时合同对象数据转换
    def convert_asset_belong_info_db(self, asset):
        # 判空
        if asset.asset_belong is None:
            return None
        # 数据转化为db对象
        asset_contract_info_db = AssetBelongsInfo(
            id=uuid.uuid4().hex,
            asset_id=asset.asset_id,
            department_id=asset.asset_belong.department_id,
            department_name=asset.asset_belong.department_name,
            user_id=asset.asset_belong.user_id,
            user_name=asset.asset_belong.user_name,
            tel_number=asset.asset_belong.tel_number,
            description=asset.asset_belong.description,
        )
        # 返回数据
        return asset_contract_info_db


    # 资产创建时合同对象数据转换
    def convert_asset_customer_info_db(self, asset):
        # 判空
        if asset.asset_customer is None:
            return None
        # 数据转化为db对象
        asset_customer_info_db = AssetCustomersInfo(
            id=uuid.uuid4().hex,
            asset_id=asset.asset_id,
            customer_id=asset.asset_customer.customer_id,
            customer_name=asset.asset_customer.customer_name,
            rental_duration=asset.asset_customer.rental_duration,
            start_date=asset.asset_customer.start_date,
            end_date=asset.asset_customer.end_date,
            vlan_id=asset.asset_customer.vlan_id,
            float_ip=asset.asset_customer.float_ip,
            band_width=asset.asset_customer.band_width,
            description=asset.asset_customer.description,
        )
        # 返回数据
        return asset_customer_info_db

    def get_asset(self, asset_id):
        # 业务校验 todo
        if asset_id is None or len(asset_id) <= 0:
            return None
        # 详情
        try:
            # 通过列表接口查
            res = self.list_assets(asset_id, None, 1, 10, None, None)
            # 空
            if res is None or res["data"] is None:
                return None
            # 返回第一个数据
            return res["data"][0]
        except Exception as e:
            import traceback
            traceback.print_exc()
        # 成功返回资产id
        return None

    def delete_asset(self, asset_id):
        # 业务校验 todo
        if asset_id is None or len(asset_id) <= 0:
            return None
        # 删除
        try:
            # 删除对象
            AssetSQL.delete_asset(asset_id)
        except Exception as e:
            import traceback
            traceback.print_exc()
        # 成功返回资产id
        return None



    def import_asset(self, row):
        # 存入一行
        try:
            # 初始化数据对象
            asset = self.init_empty_asset_info()
            # 从excel中加载基础信息数据
            for basic_key, basic_column in asset_basic_info_columns:
                asset[basic_key] = row[basic_column]
            # todo 导入解析数据要是活的
            # 解析一行数据，按照模板字段数据组装 资产数据信息
            for column_name in asset_equipment_columns:
                print(row[column_name])
            # 组装数据
        except Exception as e:
            import traceback
            traceback.print_exc()

    # 初始化一个空的资产数据的结构对象
    def init_empty_asset_info(self):
        asset = {}
        asset["asset_id"] = uuid.uuid4().hex
        asset["asset_type_id"] = "8fb707d8-b07e-11ef-90c8-44a842237864"
        # 厂商信息
        manufacture = {}
        manufacture["id"] = uuid.uuid4().hex
        manufacture["asset_id"] = asset["asset_id"]
        asset["asset_manufacturer"] = manufacture
        # 位置信息
        position = {}
        position["id"] = uuid.uuid4().hex
        position["asset_id"] = asset["asset_id"]
        asset["asset_position"] = position
        # 合同信息
        contract = {}
        contract["id"] = uuid.uuid4().hex
        contract["asset_id"] = asset["asset_id"]
        asset["asset_contract"] = contract
        # 归属信息
        belong = {}
        belong["id"] = uuid.uuid4().hex
        belong["asset_id"] = asset["asset_id"]
        asset["asset_belong"] = belong
        # 租户信息
        customer = {}
        customer["id"] = uuid.uuid4().hex
        customer["asset_id"] = asset["asset_id"]
        asset["asset_customer"] = customer
        # 返回
        return asset


    def create_asset_excel(self):
        # 模板路径
        template_file = os.getcwd() + ASSET_TEMPLATE_FILE_DIR
        # 读取模板的第一个sheet页
        df = pd.read_excel(template_file, sheet_name="asset")
        # 读取数据数据
        data = []
        # 写入数据
        index = 1
        for temp in data:
            # 第 index 行 数据
            df.loc[index,"列A"] = "xx"
            # 下一行
            index = index + 1
        pass


    def update_asset(self, asset_id, asset):
        pass


    # 以下厂商相关功能 创建、查询、删除、修改
    def create_manufacture(self, manufacture):
        # 业务校验 todo
        if manufacture is None:
            return None
        # 定义id
        manufacture_id = None
        try:
            # 数据组装
            # 资产厂商信息
            manufacture_info_db = self.convert_manufacturer_info_db(manufacture)
            # 保存对象
            AssetSQL.create_manufacture(manufacture_info_db)
        except Exception as e:
            import traceback
            traceback.print_exc()
        # 成功返回资产id
        return manufacture_id

    # 创建时厂商对象数据转换
    def convert_manufacturer_info_db(self, manufacture):
        # 判空
        if manufacture is None:
            return None
        # 数据转化为db对象
        manufacturer_info_db = AssetManufacturesInfo(
            id=uuid.uuid4().hex,
            asset_id=manufacture.asset_id,
            name=manufacture.name,
            description=manufacture.name,
        )
        # 返回数据
        return manufacturer_info_db

    # 查询厂商列表
    def list_manufactures(self, manufacture_name, page, page_size, sort_keys, sort_dirs):
        # 业务逻辑
        try:
            # 按照条件从数据库中查询数据
            count, data = AssetSQL.list_manufacture(manufacture_name, page, page_size, sort_keys, sort_dirs)
            # 数据处理
            ret = []
            # 遍历
            for r in data:
                # 填充数据 厂商信息
                temp_manufacture = {}
                temp_manufacture["manufacture_id"] = r.id
                temp_manufacture["asset_id"] = r.asset_id
                temp_manufacture["manufacture_name"] = r.name
                temp_manufacture["manufacture_description"] = r.description
                # 加入列表
                ret.append(temp_manufacture)
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

    # 删除厂商
    def delete_manufacture(self, manufacture_id):
        # 业务校验 todo
        if manufacture_id is None or len(manufacture_id) <= 0:
            return None
        # 删除
        try:
            # 删除对象
            AssetSQL.delete_manufacture(manufacture_id)
        except Exception as e:
            import traceback
            traceback.print_exc()
        # 成功返回资产id
        return manufacture_id

    # 根据id修改厂商
    def update_manufacture(self, manufacture_id, manufacture_update_info):
        # 业务校验 todo
        if manufacture_update_info is None or manufacture_id is None or len(manufacture_id) <= 0:
            return None
        try:
            # 资产厂商信息
            manufacture_db = AssetSQL.get_manufacture_by_id(manufacture_id)
            # 判空
            if manufacture_db is None:
                return None
            # 填充需要修改的数据
            # 名称
            if manufacture_update_info.name is not None and len(manufacture_update_info.name) > 0:
                manufacture_db.name = manufacture_update_info.name
            # 描述
            if manufacture_update_info.description is not None and len(manufacture_update_info.description) > 0:
                manufacture_db.description = manufacture_update_info.description
            # 保存对象
            AssetSQL.update_manufacture(manufacture_db)
        except Exception as e:
            import traceback
            traceback.print_exc()
        # 成功返回资产id
        return manufacture_id


# 以下是资产类型相关的service
    # 查询资产列表
    def list_assets_types(self, asset_type_name):
        # 业务逻辑
        try:
            # 按照条件从数据库中查询数据
            data = AssetSQL.list_asset_type(asset_type_name)
            # 数据处理
            ret = []
            # 遍历
            for r in data:
                # 填充数据
                temp = {}
                temp["id"] = r.id
                temp["parent_id"] = r.parent_id
                temp["asset_type_name"] = r.asset_type_name
                temp["asset_type_name_zh"] = r.asset_type_name_zh
                temp["queue"] = r.queue
                temp["description"] = r.description
                # 加入列表
                ret.append(temp)
            # 返回数据
            return ret
        except Exception as e:
            import traceback
            traceback.print_exc()
            return None


    # 以下是资产配件相关方法
    # 查询资产配件列表
    def list_assets_parts(self, asset_id):
        # 业务逻辑
        try:
            # 按照条件从数据库中查询数据
            data = AssetSQL.list_asset_part(asset_id)
            # 数据处理
            ret = []
            # 遍历
            for r in data:
                # 填充数据
                temp = {}
                temp["id"] = r.id
                temp["name"] = r.name
                temp["asset_id"] = r.asset_id
                temp["part_type"] = r.part_type
                temp["part_brand"] = r.part_brand
                temp["part_config"] = r.part_config
                temp["part_number"] = r.part_number
                temp["personal_used_flag"] = r.personal_used_flag
                temp["surplus"] = r.surplus
                temp["description"] = r.description
                # 加入列表
                ret.append(temp)
            # 返回数据
            return ret
        except Exception as e:
            import traceback
            traceback.print_exc()
            return None
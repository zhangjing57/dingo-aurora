# 资产的service层
import json
import os
import shutil
import uuid
from io import BytesIO

import pandas as pd
from datetime import datetime

from openpyxl.reader.excel import load_workbook

from api.model.assets import AssetCreateApiModel
from db.models.asset.models import AssetBasicInfo, AssetManufacturesInfo, AssetPartsInfo, AssetPositionsInfo, \
    AssetContractsInfo, AssetCustomersInfo, AssetBelongsInfo
from db.models.asset.sql import AssetSQL
from math import ceil
from oslo_log import log

from utils.constant import ASSET_TEMPLATE_FILE_DIR, asset_equipment_columns, asset_basic_info_columns, \
    asset_manufacture_info_columns, asset_position_info_columns, asset_contract_info_columns, asset_belong_info_columns, \
    asset_customer_info_columns, asset_part_info_columns
from utils.datetime import change_excel_date_to_timestamp

LOG = log.getLogger(__name__)

class AssetsService:

    # 查询资产列表
    def list_assets(self, asset_id, asset_name, asset_status, frame_position, cabinet_position, u_position, equipment_number, asset_number, sn_number, department_name, user_name, page, page_size, sort_keys, sort_dirs):
        # 业务逻辑
        try:
            # 按照条件从数据库中查询数据
            count, data = AssetSQL.list_asset(asset_id, asset_name, asset_status, frame_position, cabinet_position, u_position, equipment_number, asset_number, sn_number, department_name, user_name, page, page_size, sort_keys, sort_dirs)
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
            # 数据校验
            # 1、名称空
            if asset.asset_name is None:
                raise Exception
            # 2、重名
            count, _ = AssetSQL.list_asset(None, asset.asset_name, None, None, None, None, None, None, None, None, None, 1,10,None,None)
            if count > 0:
                LOG.error("asset name exist")
                raise Exception
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
            raise e
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
            start_date=None if asset.asset_customer.start_date is None else datetime.fromtimestamp(asset.asset_customer.start_date/1000),
            end_date=None if asset.asset_customer.end_date is None else datetime.fromtimestamp(asset.asset_customer.end_date/1000),
            vlan_id=asset.asset_customer.vlan_id,
            float_ip=asset.asset_customer.float_ip,
            band_width=asset.asset_customer.band_width,
            description=asset.asset_customer.description,
        )
        # 返回数据
        return asset_customer_info_db

    def get_asset_by_id(self, asset_id):
        if not asset_id:
            return None
        # 详情
        try:
            # 根据id查询
            res = self.list_assets(asset_id, None, None, None, None, None, None, None, None, None, None, 1, 10, None, None)
            # 空
            if not res or not res.get("data"):
                return None
            # 返回第一条数据
            return res.get("data")[0]
        except Exception as e:
            import traceback
            traceback.print_exc()
            raise Exception


    def update_assets_status(self, asset_list):
        # 列表空
        if not asset_list:
            return None
        # 详情
        try:
            for asset_temp in asset_list:
                # 判断对象是空
                if asset_temp is None:
                    pass
                # 资产id空或者资产状态空
                if not asset_temp.asset_id or not asset_temp.asset_status:
                    pass
                # 资产状态如果是错误的时候 描述信息不能为空
                if asset_temp.asset_status == "3" and not asset_temp.asset_status_description:
                    pass
                # 查询数据
                asset_basic_info_db = AssetSQL.get_asset_basic_info_by_id(asset_temp.asset_id)
                # 不存在
                if not asset_basic_info_db:
                    pass
                # 设置更新的字段
                asset_basic_info_db.asset_status = asset_temp.asset_status
                # 更新数据
                AssetSQL.update_asset_basic_info(asset_basic_info_db)
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
            asset = self.init_empty_asset_api_model()
            # 从excel中加载基础信息数据
            for basic_key, basic_column in asset_basic_info_columns.items():
                # 判断excel的数据是非nan
                if pd.notna(row[basic_column]):
                    asset.__setattr__(basic_key, row[basic_column])
            # 从excel中加载厂商信息数据
            for manufacture_key, manufacture_column in asset_manufacture_info_columns.items():
                # 判断excel的数据是非nan
                if pd.notna(row[manufacture_column]):
                    asset.asset_manufacturer.__setattr__(manufacture_key, row[manufacture_column])
            # 从excel中加载位置信息数据
            for position_key, position_column in asset_position_info_columns.items():
                # 判断excel的数据是非nan
                if pd.notna(row[position_column]):
                    asset.asset_position.__setattr__(position_key, row[position_column])
            # 从excel中加载合同信息数据
            for contract_key, contract_column in asset_contract_info_columns.items():
                # 判断excel的数据是非nan
                if pd.notna(row.get(contract_column, None)):
                    row_value = row[contract_column]
                    # 购买日期单独处理
                    if "purchase_date" == contract_key:
                        row_value = int(row_value.timestamp() * 1000)
                    # 赋值
                    asset.asset_contract.__setattr__(contract_key, row_value)
            # 从excel中加载归属信息数据
            for belong_key, belong_column in asset_belong_info_columns.items():
                # 判断excel的数据是非nan
                if pd.notna(row[belong_column]):
                    asset.asset_belong.__setattr__(belong_key, row[belong_column])
            # 从excel中加载租户信息数据
            for customer_key, customer_column in asset_customer_info_columns.items():
                # 判断excel的数据是非nan
                if pd.notna(row.get(customer_column, None)):
                    asset.asset_customer.__setattr__(customer_key, row.get(customer_column, None))
                    # 调用创建
            self.create_asset(asset)
            # 组装数据
        except Exception as e:
            import traceback
            traceback.print_exc()


    def import_asset_part(self, row):
        # 存入一行
        try:
            # 获取配件属于的资产编号
            asset_number = None
            if pd.notna(row["资产编号"]):
                asset_number = row["资产编号"]
            # 根据资产编号精准查询资产设备
            asset_id = None
            asset_basic_info_db = AssetSQL.get_asset_basic_info_by_asset_number(asset_number)
            if asset_basic_info_db:
                asset_id = asset_basic_info_db.id
            # 从excel中加载配件信息数据
            for part_key, part_column in asset_part_info_columns.items():
                # 每一列的数据都作为一个配件
                # 初始化数据对象
                asset_part = self.init_empty_asset_part_api_model()
                # 判断excel的数据是非nan
                if pd.notna(row[part_column]):
                    asset_part.__setattr__("part_type", part_key)
                    asset_part.__setattr__("asset_id", asset_id)
                    asset_part.__setattr__("name", row[part_column])
                # 入库
                AssetSQL.create_asset_part(asset_part)
        except Exception as e:
            import traceback
            traceback.print_exc()


    # 初始化一个空的资产数据的结构对象
    def init_empty_asset_api_model(self):
        # 初始化api的model对象
        asset = AssetCreateApiModel(
            # 资产通用信息
            asset_id = uuid.uuid4().hex,
            asset_name = "Default",
            asset_type_id = None,
            asset_description = None,
            # 资产基础信息
            equipment_number = None,
            sn_number = None,
            asset_number = None,
            asset_status = "0",
            extra = None,
            # 配件信息
            asset_part = None,
            # 位置信息
            asset_position = None,
            # 厂商信息
            asset_manufacturer = None,
            # 合同信息
            asset_contract = None,
            # 所属用户信息
            asset_belong = None,
            # 租户信息
            asset_customer = None,
        )
        # 厂商
        asset_manufacturer = AssetManufacturesInfo(
            id = uuid.uuid4().hex,
            asset_id = asset.asset_id,
            name = None,
            description = None,
            extra = None,
        )
        asset.asset_manufacturer = asset_manufacturer
        # 位置
        asset_position = AssetPositionsInfo(
            id = uuid.uuid4().hex,
            asset_id = asset.asset_id,
            frame_position = None,
            cabinet_position = None,
            u_position = None,
            description = None,
        )
        asset.asset_position = asset_position
        # 合同
        asset_contract = AssetContractsInfo(
            id = uuid.uuid4().hex,
            asset_id = asset.asset_id,
            contract_number = None,
            purchase_date = None,
            batch_number = None,
            description = None,
        )
        asset.asset_contract = asset_contract
        # 归属信息
        asset_belong = AssetBelongsInfo(
            id = uuid.uuid4().hex,
            asset_id = asset.asset_id,
            department_id = None,
            department_name = None,
            user_id = None,
            user_name = None,
            tel_number = None,
            description = None,
        )
        asset.asset_belong = asset_belong
        # 租户信息
        asset_customer = AssetCustomersInfo(
            id = uuid.uuid4().hex,
            asset_id = asset.asset_id,
            customer_id = None,
            customer_name = None,
            rental_duration = None,
            start_date = None,
            end_date = None,
            vlan_id = None,
            float_ip = None,
            band_width = None,
            description = None,
        )
        asset.asset_customer = asset_customer
        # 返回
        return asset

    # 初始化一个空的资产数据的结构对象
    def init_empty_asset_part_api_model(self):
        # 租户信息
        asset_part = AssetPartsInfo(
            id = uuid.uuid4().hex,
            asset_id = None,
            part_type = None,
            part_brand = None,
            part_config = None,
            part_number = None,
            personal_used_flag = None,
            surplus = None,
            name = None,
            description = None,
            extra = None,
        )
        # 返回
        return asset_part


    def create_asset_excel(self, result_file_path):
        # 模板路径
        template_file = os.getcwd() + ASSET_TEMPLATE_FILE_DIR
        # 复制模板文件到临时目录
        shutil.copy2(template_file, result_file_path)
        # 导出的excel数据
        excel_asset_data = []
        excel_part_data = []
        # 读取数据数据
        page = 1
        page_size = 100
        # 查询一页
        res = self.list_assets(None, None, None, None, None, None, None, None, None, None, None, page, page_size, None, None)
        while res and res['data']:
            # 写入数据
            for temp in res['data']:
                # df.loc[index,"设备名称"] = temp["asset_name"]
                # 下一行
                # index = index + 1
                # 修改或添加新数据
                temp_asset_data = {'机架': temp['asset_position']['frame_position'],'机柜': temp['asset_position']['cabinet_position'],'U位': temp['asset_position']['u_position'],
                             '设备名称': temp['asset_name'],'设备型号': temp['equipment_number'],'资产编号': temp['asset_number'],'序列号': temp['sn_number'],
                             '部门': temp['asset_belong']['department_name'],'负责人': temp['asset_belong']['user_name'],'主机名': None,'IP': None,
                             'IDRAC': None,'用途': None,'密码': None,'操作系统': None,
                             '购买日期': temp['asset_contract']['purchase_date'],'厂商': temp['asset_manufacturer']['name'],'批次': temp['asset_contract']['batch_number'],'备注': temp['asset_description'],}
                # 配件数据
                if temp['asset_part']:
                    temp_part_data = {'资产编号': temp['asset_number'],}
                    # 遍历配件
                    for temp_part in temp['asset_part']:
                        # 表头存在
                        if asset_part_info_columns.get(temp_part['part_type'], None):
                            temp_part_data[asset_part_info_columns.get(temp_part['part_type'], None)] = temp_part['part_name']
                    # 数据追加
                    excel_part_data.append(temp_part_data)
                # 加入excel导出数据列表
                excel_asset_data.append(temp_asset_data)
            # 判断总页数已经大于等于当前已经查询的页数，已经查询完成，退出循环
            if res['totalPages'] >= page:
                break
            # 查询下一页
            page = page + 1
            res = self.list_assets(None, None, None, None, None, None, None, None, None, None, None, page, page_size, None, None)
        try:
            # 加载模板文件
            book = load_workbook(result_file_path)
            sheet = book.active  # 默认使用第一个工作表
            # 确定起始写入行号
            start_row = 2  # 自动追加到最后一行之后
            # 写入数据到模板文件
            for idx, row in pd.DataFrame(excel_asset_data).iterrows():
                for col_idx, value in enumerate(row, start=1):  # 列从 1 开始
                    sheet.cell(row=start_row + idx, column=col_idx, value=value)
            # 保存修改
            book.save(result_file_path)
            # 配件sheet
            part_sheet = book['part']
            start_row = 2  # 自动追加到最后一行之后
            # 写入数据到模板文件
            for idx, row in pd.DataFrame(excel_part_data).iterrows():
                for col_idx, value in enumerate(row, start=1):  # 列从 1 开始
                    part_sheet.cell(row=start_row + idx, column=col_idx, value=value)
                    # 保存修改
            book.save(result_file_path)
        except Exception as e:
            import traceback
            traceback.print_exc()
            raise e





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
            manufacture_id = manufacture_info_db.id
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
            extra=json.dumps(manufacture.extra)
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
                temp_manufacture["manufacture_extra"] = r.extra
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
    # 查询资产类型列表
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

    # 查询资产配件列表
    def list_assets_parts_pages(self, part_catalog, asset_id, name, page, page_size, sort_keys, sort_dirs):
        # 业务逻辑
        try:
            # 按照条件从数据库中查询数据
            count, data = AssetSQL.list_asset_part_page(part_catalog, asset_id, name, page, page_size, sort_keys, sort_dirs)
            # 数据处理
            ret = []
            # 遍历
            for r in data:
                # 填充数据
                temp = {}
                temp["id"] = r.id
                temp["name"] = r.name
                temp["asset_name"] = r.asset_name
                temp["asset_number"] = r.asset_number
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

    def create_asset_part(self, asset_part):
        # 判空
        if asset_part is None:
            return None
        # 定义id
        asset_part_id = None
        try:
            # 数据组装
            # 配件信息
            asset_part_info_db = self.convert_asset_part_info_db_4api(asset_part)
            asset_part_id = asset_part_info_db.id
            # 保存对象
            AssetSQL.create_asset_part(asset_part_info_db)
        except Exception as e:
            import traceback
            traceback.print_exc()
        # 成功返回资产id
        return asset_part_id


        # 创建配件对象数据转换 1个数据对象
    def convert_asset_part_info_db_4api(self, asset_part):
        # 判空
        if asset_part is None:
            return None
        # 数据转化为db对象
        asset_part_info_db = AssetPartsInfo(
            id=uuid.uuid4().hex,
            asset_id=asset_part.asset_id,
            name=asset_part.name,
            part_type=asset_part.part_type,
            part_brand=asset_part.part_brand,
            part_config=asset_part.part_config,
            part_number=asset_part.part_number,
            personal_used_flag=asset_part.personal_used_flag,
            surplus=asset_part.surplus,
            description=asset_part.description,
        )
        # 返回数据
        return asset_part_info_db

    # 根据id修改配件
    def update_asset_part_by_id(self, id, asset_part):
        # 业务校验
        if asset_part is None or id is None or len(id) <= 0:
            return None
        try:
            # 配件信息
            asset_part_db = AssetSQL.get_asset_part_by_id(id)
            # 判空
            if asset_part_db is None:
                return None
            # 填充需要修改的数据
            # 名称
            if asset_part.name is not None and len(asset_part.name) > 0:
                asset_part_db.name = asset_part.name
            # 类型
            if asset_part.part_type is not None and len(asset_part.part_type) > 0:
                asset_part_db.part_type = asset_part.part_type
            # 品牌
            if asset_part.part_brand is not None and len(asset_part.part_brand) > 0:
                asset_part_db.part_brand = asset_part.part_brand
            # 配置
            if asset_part.part_config is not None and len(asset_part.part_config) > 0:
                asset_part_db.part_config = asset_part.part_config
            # 编号
            if asset_part.part_number is not None and len(asset_part.part_number) > 0:
                asset_part_db.part_number = asset_part.part_number
            # 是否可自用
            if asset_part.personal_used_flag is not None:
                asset_part_db.personal_used_flag = asset_part.personal_used_flag
            # 剩余情况
            if asset_part.surplus is not None and len(asset_part.surplus) > 0:
                asset_part_db.surplus = asset_part.surplus
            # 描述
            if asset_part.description is not None and len(asset_part.description) > 0:
                asset_part_db.description = asset_part.description
            # 保存对象
            AssetSQL.update_asset_part(asset_part_db)
        except Exception as e:
            import traceback
            traceback.print_exc()
        # 成功返回资产id
        return id

    # 删除配件
    def delete_asset_part_by_id(self, asset_part_id):
        # 业务校验
        if asset_part_id is None or len(asset_part_id) <= 0:
            return None
        # 删除
        try:
            # 删除对象
            AssetSQL.delete_asset_part(asset_part_id)
        except Exception as e:
            import traceback
            traceback.print_exc()
        # 成功返回资产id
        return asset_part_id


    # 根据id修改配件
    def bind_asset_part_by_id(self, id, asset_id):
        # 业务校验
        if asset_id is None or len(asset_id) <= 0 or id is None or len(id) <= 0:
            return None
        try:
            # 配件信息
            asset_part_db = AssetSQL.get_asset_part_by_id(id)
            # 判空
            if asset_part_db is None:
                return None
            # 资产信息
            asset_basic_info_db = AssetSQL.get_asset_basic_info_by_id(asset_id)
            if asset_basic_info_db is None:
                return None
            # 填充需要修改的数据
            # id
            asset_part_db.asset_id = asset_id
            # 保存对象
            AssetSQL.update_asset_part(asset_part_db)
        except Exception as e:
            import traceback
            traceback.print_exc()
        # 成功返回资产id
        return id

        # 根据id修改配件
    def unbind_asset_part_by_id(self, id, asset_id):
        # 业务校验
        if asset_id is None or len(asset_id) <= 0 or id is None or len(id) <= 0:
            return None
        try:
            # 配件信息
            asset_part_db = AssetSQL.get_asset_part_by_id(id)
            # 判空
            if asset_part_db is None:
                return None
            # 资产信息
            asset_basic_info_db = AssetSQL.get_asset_basic_info_by_id(asset_id)
            if asset_basic_info_db is None:
                return None
            # 填充需要修改的数据
            # id
            asset_part_db.asset_id = None
            # 保存对象
            AssetSQL.update_asset_part(asset_part_db)
        except Exception as e:
            import traceback
            traceback.print_exc()
        # 成功返回资产id
        return id
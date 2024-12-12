# 数据表对应的model对象

from __future__ import annotations

from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from typing_extensions import assert_type

from db.models.asset.models import Asset, AssetBasicInfo, AssetPartsInfo, AssetManufacturesInfo, AssetPositionsInfo, \
    AssetContractsInfo, AssetBelongsInfo, AssetCustomersInfo, AssetType

from enum import Enum

#链接数据库，可以使用配置文件进行定义
engine = create_engine("mysql+pymysql://root:HworLIIDvmTRsPfQauNskuJF8PcoTuULfu3dEHFg@10.220.56.254:3306/dingoops?charset=utf8mb3", echo=True)
# 资产排序字段字典
asset_dir_dic= {"name":AssetBasicInfo.name, "id": AssetBasicInfo.id}

class AssetSQL:

    # 数据库操作添加
    @classmethod
    def add_user(cls):
        #创建会话 ，正常是公共代码
        Session = sessionmaker(bind=engine)
        session = Session()
        new_user = Asset(name='John', fullname='John Doe', nickname='johndoe')
        #使用begin方式，自动管理会话的开启和关闭，不需要commit和close操作，中介出错的话会自动回滚
        with session.begin():
            session.add(new_user)

    @classmethod
    def list_asset(cls, asset_id, asset_name, page=1, page_size=10, sort_keys=None, sort_dirs="asc"):
        Session = sessionmaker(bind=engine,expire_on_commit=False)
        session = Session()
        with session.begin():
            # 查询语句
            query = session.query(AssetBasicInfo.id.label("id"),
                                  AssetBasicInfo.name.label("name"),
                                  AssetBasicInfo.asset_type_id.label("asset_type_id"),
                                  AssetBasicInfo.equipment_number.label("equipment_number"),
                                  AssetBasicInfo.sn_number.label("sn_number"),
                                  AssetBasicInfo.asset_number.label("asset_number"),
                                  AssetBasicInfo.asset_status.label("asset_status"),
                                  AssetBasicInfo.description.label("description"),
                                  AssetBasicInfo.extra.label("extra"),
                                  AssetManufacturesInfo.id.label("manufacture_id"),
                                  AssetManufacturesInfo.name.label("manufacture_name"),
                                  AssetManufacturesInfo.description.label("manufacture_description"),
                                  AssetPositionsInfo.id.label("position_id"),
                                  AssetPositionsInfo.frame_position.label("position_frame_position"),
                                  AssetPositionsInfo.cabinet_position.label("position_cabinet_position"),
                                  AssetPositionsInfo.u_position.label("position_u_position"),
                                  AssetPositionsInfo.description.label("position_description"),
                                  AssetContractsInfo.id.label("contract_id"),
                                  AssetContractsInfo.contract_number.label("contract_number"),
                                  AssetContractsInfo.purchase_date.label("contract_purchase_date"),
                                  AssetContractsInfo.batch_number.label("contract_batch_number"),
                                  AssetContractsInfo.description.label("contract_description"),
                                  AssetBelongsInfo.id.label("belong_id"),
                                  AssetBelongsInfo.department_id.label("belong_department_id"),
                                  AssetBelongsInfo.department_name.label("belong_department_name"),
                                  AssetBelongsInfo.user_id.label("belong_user_id"),
                                  AssetBelongsInfo.user_name.label("belong_user_name"),
                                  AssetBelongsInfo.tel_number.label("belong_tel_number"),
                                  AssetBelongsInfo.description.label("belong_contract_description"),
                                  AssetCustomersInfo.id.label("customer_id"),
                                  AssetCustomersInfo.customer_id.label("customer_customer_id"),
                                  AssetCustomersInfo.customer_name.label("customer_customer_name"),
                                  AssetCustomersInfo.rental_duration.label("customer_rental_duration"),
                                  AssetCustomersInfo.start_date.label("customer_start_date"),
                                  AssetCustomersInfo.end_date.label("customer_end_date"),
                                  AssetCustomersInfo.vlan_id.label("customer_vlan_id"),
                                  AssetCustomersInfo.float_ip.label("customer_float_ip"),
                                  AssetCustomersInfo.band_width.label("customer_band_width"),
                                  AssetCustomersInfo.description.label("customer_description"),
                                  )
            # 外连接
            query = query.outerjoin(AssetManufacturesInfo, AssetManufacturesInfo.asset_id == AssetBasicInfo.id). \
                outerjoin(AssetPositionsInfo, AssetPositionsInfo.asset_id == AssetBasicInfo.id). \
                outerjoin(AssetContractsInfo, AssetContractsInfo.asset_id == AssetBasicInfo.id). \
                outerjoin(AssetBelongsInfo, AssetBelongsInfo.asset_id == AssetBasicInfo.id). \
                outerjoin(AssetCustomersInfo, AssetCustomersInfo.asset_id == AssetBasicInfo.id)
                # 数据库查询参数
            if asset_name is not None and len(asset_name) > 0 :
                query = query.filter(AssetBasicInfo.name.like('%' + asset_name + '%'))
            if asset_id is not None and len(asset_id) > 0 :
                query = query.filter(AssetBasicInfo.id == asset_id)

            # 总数
            count = query.count()
            # 排序
            if sort_keys is not None and asset_dir_dic[sort_keys] is not None:
                if sort_dirs == "asc" or sort_dirs is None :
                    query = query.order_by(asset_dir_dic[sort_keys].asc())
                elif sort_dirs == "desc":
                    query = query.order_by(asset_dir_dic[sort_keys].desc())
            # 分页条件
            page_size = int(page_size)
            page_num = int(page)
            # 查询所有数据
            if page_size == -1:
                return count, query.all()
            # 页数计算
            start = (page_num - 1) * page_size
            query = query.limit(page_size).offset(start)
            assert_list = query.all()
            # 返回
            return count, assert_list


    @classmethod
    def list_asset_bak(cls, asset_name=None, page=1, page_size=10, field=None, dir="ASC"):
        Session = sessionmaker(bind=engine,expire_on_commit=False)
        session = Session()
        with session.begin():
            query = session.query(Asset)
            # 数据库查询参数
            if asset_name is not None:
                query = query.filter(Asset.asset_name.like('%' + asset_name + '%'))

            # 总数
            count = query.count()
            # 分页条件
            page_size = int(page_size)
            page_num = int(page)
            # 查询所有数据
            if page_size == -1:
                return count, query.all()
            # 页数计算
            start = (page_num - 1) * page_size
            query = query.limit(page_size).offset(start)
            assert_list = query.all()
            # 返回
            return count, assert_list


    @classmethod
    def list_asset_basic_info(cls, asset_name=None, page=1, page_size=10, field=None, dir="ASC"):
        Session = sessionmaker(bind=engine,expire_on_commit=False)
        session = Session()
        with session.begin():
            query = session.query(AssetBasicInfo)
            # 数据库查询参数
            if asset_name is not None:
                query = query.filter(AssetBasicInfo.name.like('%' + asset_name + '%'))

            # 总数
            count = query.count()
            # 分页条件
            page_size = int(page_size)
            page_num = int(page)
            # 查询所有数据
            if page_size == -1:
                return count, query.all()
            # 页数计算
            start = (page_num - 1) * page_size
            query = query.limit(page_size).offset(start)
            assert_list = query.all()
            # 返回
            return count, assert_list


    @classmethod
    def create_asset_basic_info(cls, data):
        Session = sessionmaker(bind=engine, expire_on_commit=False)
        session = Session()
        with session.begin():
            session.add(data)


    @classmethod
    def create_asset(cls, basic_info, manufacture_info, position_info, contract_info, belong_info, customer_info, part_info):
        Session = sessionmaker(bind=engine, expire_on_commit=False)
        session = Session()
        with session.begin():
            session.add(basic_info)
            if manufacture_info is not None:
                session.add(manufacture_info)
            if position_info is not None:
                session.add(position_info)
            if contract_info is not None:
                session.add(contract_info)
            if belong_info is not None:
                session.add(belong_info)
            if customer_info is not None:
                session.add(customer_info)
            if part_info is not None:
                session.add_all(part_info)


    @classmethod
    def delete_asset(cls, asset_id):
        Session = sessionmaker(bind=engine, expire_on_commit=False)
        session = Session()
        with session.begin():
            # 删除资产基础信息
            session.query(AssetBasicInfo).filter(AssetBasicInfo.id == asset_id).delete()
            # 删除资产的配件信息
            session.query(AssetPartsInfo).filter(AssetPartsInfo.asset_id == asset_id).delete()
            # 删除资产的厂商信息
            session.query(AssetManufacturesInfo).filter(AssetManufacturesInfo.asset_id == asset_id).delete()
            # 删除资产的位置信息
            session.query(AssetPositionsInfo).filter(AssetPositionsInfo.asset_id == asset_id).delete()
            # 删除资产的合同信息
            session.query(AssetContractsInfo).filter(AssetContractsInfo.asset_id == asset_id).delete()
            # 删除资产的归属信息
            session.query(AssetBelongsInfo).filter(AssetBelongsInfo.asset_id == asset_id).delete()
            # 删除资产的租户信息
            session.query(AssetCustomersInfo).filter(AssetCustomersInfo.asset_id == asset_id).delete()


    @classmethod
    def list_manufacture(cls, manufacture_name=None, page=1, page_size=10, field=None, dir="ASC"):
        Session = sessionmaker(bind=engine,expire_on_commit=False)
        session = Session()
        with session.begin():
            # 查询厂商表
            query = session.query(AssetManufacturesInfo)
            # 数据库查询参数
            if manufacture_name is not None:
                query = query.filter(AssetManufacturesInfo.name.like('%' + manufacture_name + '%'))

            # 总数
            count = query.count()
            # 分页条件
            page_size = int(page_size)
            page_num = int(page)
            # 查询所有数据
            if page_size == -1:
                return count, query.all()
            # 页数计算
            start = (page_num - 1) * page_size
            query = query.limit(page_size).offset(start)
            assert_list = query.all()
            # 返回
            return count, assert_list

    @classmethod
    def create_manufacture(cls, manufacture_info):
        Session = sessionmaker(bind=engine, expire_on_commit=False)
        session = Session()
        with session.begin():
            session.add(manufacture_info)

    @classmethod
    def delete_manufacture(cls, manufacture_id):
        Session = sessionmaker(bind=engine, expire_on_commit=False)
        session = Session()
        with session.begin():
            # 删除资产的厂商信息
            session.query(AssetManufacturesInfo).filter(AssetManufacturesInfo.id == manufacture_id).delete()

    @classmethod
    def get_manufacture_by_id(cls, manufacture_id):
        Session = sessionmaker(bind=engine, expire_on_commit=False)
        session = Session()
        with session.begin():
            return session.query(AssetManufacturesInfo).filter(AssetManufacturesInfo.id == manufacture_id).first()

    @classmethod
    def update_manufacture(cls, manufacture_db):
        Session = sessionmaker(bind=engine, expire_on_commit=False)
        session = Session()
        with session.begin():
            return session.merge(manufacture_db)


    # 资产类型查询列表
    @classmethod
    def list_asset_type(cls, asset_type_name=None):
        Session = sessionmaker(bind=engine,expire_on_commit=False)
        session = Session()
        with session.begin():
            query = session.query(AssetType)
            # 数据库查询参数
            if asset_type_name is not None:
                query = query.filter(AssetType.asset_type_name.like('%' + asset_type_name + '%'))
            # 查询所有数据
            assert_type_list = query.all()
            # 返回
            return assert_type_list


    # 资产配件查询列表
    @classmethod
    def list_asset_part(cls, asset_id=None):
        Session = sessionmaker(bind=engine,expire_on_commit=False)
        session = Session()
        with session.begin():
            query = session.query(AssetPartsInfo)
            # 数据库查询参数
            if asset_id is not None:
                query = query.filter(AssetPartsInfo.asset_id == asset_id)
            # 查询所有数据
            assert_part_list = query.all()
            # 返回
            return assert_part_list

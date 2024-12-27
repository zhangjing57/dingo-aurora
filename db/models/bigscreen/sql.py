# 数据表对应的model对象

from __future__ import annotations

from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from typing_extensions import assert_type

from enum import Enum
import db.models.bigscreen.models as bigscreen
from db.models.bigscreen.models import BigscreenMetricsConfig

#链接数据库，可以使用配置文件进行定义
engine = create_engine("mysql+pymysql://root:HworLIIDvmTRsPfQauNskuJF8PcoTuULfu3dEHFg@10.220.56.254:3306/dingoops?charset=utf8mb3", echo=True)

class BigscreenSQL:
    # 数据库操作添加
    @classmethod
    def create_bigscreen_metrics_config(cls, bigscreen_metrics_config_info):
        Session = sessionmaker(bind=engine, expire_on_commit=False)
        session = Session()
        with session.begin():
            session.add(bigscreen_metrics_config_info)

    @classmethod
    def update_bigscreen_metrics_config(cls, bigscreen_metrics_config_info):
        Session = sessionmaker(bind=engine, expire_on_commit=False)
        session = Session()
        with session.begin():
            session.merge(bigscreen_metrics_config_info)

    @classmethod
    def delete_bigscreen_metrics_config(cls, bigscreen_metrics_config_id):
        Session = sessionmaker(bind=engine, expire_on_commit=False)
        session = Session()
        with session.begin():
            session.query(BigscreenMetricsConfig).filter(BigscreenMetricsConfig.id == bigscreen_metrics_config_id).delete()

    @classmethod
    def get_bigscreen_metrics_config_by_id(cls, bigscreen_metrics_config_id):
        Session = sessionmaker(bind=engine, expire_on_commit=False)
        session = Session()
        with session.begin():
            return session.query(BigscreenMetricsConfig).filter(BigscreenMetricsConfig.id == bigscreen_metrics_config_id).first()
        
    @classmethod
    def get_bigscreen_metrics_config_by_name(cls, bigscreen_metrics_config_name):
        Session = sessionmaker(bind=engine, expire_on_commit=False)
        session = Session()
        with session.begin():
            return session.query(BigscreenMetricsConfig).filter(BigscreenMetricsConfig.name == bigscreen_metrics_config_name).first()
        
    @classmethod
    def get_bigscreen_metrics_configs(cls):
        Session = sessionmaker(bind=engine, expire_on_commit=False)
        session = Session()
        with session.begin():
            return session.query(BigscreenMetricsConfig).all()
        
    @classmethod
    def get_bigscreen_metrics_config_by_sub_class(cls, bigscreen_metrics_config_sub_class):
        Session = sessionmaker(bind=engine, expire_on_commit=False)
        session = Session()
        with session.begin():
            return session.query(BigscreenMetricsConfig).filter(BigscreenMetricsConfig.sub_class == bigscreen_metrics_config_sub_class)

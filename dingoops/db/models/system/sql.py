# 数据表对应的model对象

from __future__ import annotations
from dingoops.db.engines.mysql import get_session
from dingoops.db.models.system.models import OperateLog

# 日志排序字段
operate_log_dir_dic= {"log_date":OperateLog.log_date, "operate_type":OperateLog.operate_type, "user_id":OperateLog.user_id,}

class SystemSQL:

    @classmethod
    def list_operate_log(cls, query_params, page=1, page_size=10, sort_keys=None, sort_dirs="ascend"):
        session = get_session()
        with session.begin():
            query = session.query(OperateLog)
            # 数据库查询参数
            if "resource_id" in query_params and query_params["resource_id"]:
                query = query.filter(OperateLog.resource_id == query_params["resource_id"])
            if "operate_type" in query_params and query_params["operate_type"]:
                operate_type_arr = query_params["operate_type"].split(",")
                query = query.filter(OperateLog.operate_type.in_(operate_type_arr))
            # 默认排序，按照时间降序
            # 排序
            if sort_keys is not None and sort_keys in operate_log_dir_dic:
                if sort_dirs == "ascend" or sort_dirs is None :
                    query = query.order_by(operate_log_dir_dic[sort_keys].asc())
                elif sort_dirs == "descend":
                    query = query.order_by(operate_log_dir_dic[sort_keys].desc())
            else:
                query = query.order_by(OperateLog.log_date.desc())
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
    def create_operate_log(cls, operate_log_info):
        session = get_session()
        with session.begin():
            session.add(operate_log_info)

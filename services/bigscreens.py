# 大屏的service层
import json
import urllib

import requests

from db.models.bigscreen.models import BigscreenMetricsConfig
from db.models.bigscreen.sql import BigscreenSQL
from config.settings import settings

prometheus_query_url = settings.prometheus_query_url

class BigScreensService:
    @classmethod
    def list_bigscreen_metrics_configs(self):
        return BigscreenSQL.get_bigscreen_metrics_configs()

    # 查询大屏数据
    @classmethod
    def get_bigscreen_metrics(self, name):
        bigscreen_metrics_config = BigscreenSQL.get_bigscreen_metrics_config_by_name(name)
        if bigscreen_metrics_config:
            query = bigscreen_metrics_config.query
        else:
            return None
        # 通过get请求读取实时监控数据 指标项的查询语句 + / 需要转义
        request_url = prometheus_query_url + urllib.parse.quote(query)
        print(request_url)
        response = requests.get(request_url)
        # 处理只有1组value的数据
        return self.__handle_response(response)

    # 解析接口返回的数据
    @classmethod
    def __handle_response(self, response):
        try:
            # response数据
            json_response = response.json()
            print(json_response)
            # 请求结果
            if json_response:
                # 请求成功
                if json_response['status'] == 'success':
                    # 请求结果
                    json_data = json_response['data']
                    # 解析数据
                    json_data_result = json_data['result']
                    # 数据是1组
                    return json_data_result
                    # if json_data_result and len(json_data_result) == 1:
                    #     for temp in json_data_result:
                    #         print(temp['value'][1])
                    #         return temp['value'][1]
                    # # 数据是多组
                    # if json_data_result and len(json_data_result) == 1:
                    #     for temp in json_data_result:
                    #         print(temp[1])
        except Exception as e:
            raise e

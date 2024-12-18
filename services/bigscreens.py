# 大屏的service层
import json
import urllib

import requests

from utils.constant import bigscreen_query_items

# 大屏数据测试接口
big_scren_test_url = 'http://172.20.53.200:80/api/v1/query?query='

class BigScreensService:

    # 查询大屏数据
    def list_bigscreen(self, sub_class_item):
        # 指标项空
        if sub_class_item is None or len(sub_class_item) <= 0:
            print("sub_class_item is empty")
            return None
        # 指标项是否约定的指标项
        sub_class_item_query = None
        for temp in bigscreen_query_items:
            # 对应的指标项
            if temp.get("name") == sub_class_item:
                sub_class_item_query = temp.get("query")
                break
        if sub_class_item_query is None or len(sub_class_item_query) <= 0:
            print("sub_class_item_query is empty")
            return None
        # 通过get请求读取实时监控数据 指标项的查询语句 + / 需要转义
        request_url = big_scren_test_url + urllib.parse.quote(sub_class_item_query)
        print(request_url)
        response = requests.get(request_url)
        # 处理只有1组value的数据
        return self.handle_response(response)

    # 解析接口返回的数据
    def handle_response(self, response):
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

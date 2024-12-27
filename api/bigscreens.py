# 大屏的api接口
from fastapi import APIRouter, Query

from services.bigscreens import BigScreensService

router = APIRouter()

@router.get("/bigscreen/metrics", summary="获取大屏指标数据")
# TODO: 错误处理
async def get_bigscreen_metrics(name: str):
    return BigScreensService.get_bigscreen_metrics(name)


@router.get("/bigscreen/metrics_configs", summary="获取大屏指标配置信息")
# TODO: name 可选参数做筛选
async def list_bigscreen_metrics_configs():
    # 返回数据接口
    try:
        result = BigScreensService.list_bigscreen_metrics_configs()
        return result
    except Exception as e:
        import traceback
        traceback.print_exc()
        return None

@router.get("/bigscreen/query", summary="获取大屏指标下钻数据")
# 转发给prometheus, 将查询到的数据返回
async def get_bigscreen_metrics_drill(promql: str):
    metrics = BigScreensService.fetch_metrics_with_promql(promql)
    return metrics

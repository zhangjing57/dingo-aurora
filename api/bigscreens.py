# 大屏的api接口
from fastapi import APIRouter, Query

from services.bigscreens import BigScreensService

router = APIRouter()
big_screen_service = BigScreensService()

@router.get("/bigscreens")
async def list_bigscreens(sub_class_item:str = Query(None, description="指标项"),):
    # 返回数据接口
    try:
        # 查询成功
        result = big_screen_service.list_bigscreen(sub_class_item)
        return result
    except Exception as e:
        import traceback
        traceback.print_exc()
        return None


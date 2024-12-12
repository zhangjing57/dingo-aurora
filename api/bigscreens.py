# 大屏的api接口
from fastapi import APIRouter

from services.bigscreens import BigScreensService

router = APIRouter()
big_screen_service = BigScreensService()

@router.get("/bigscreens")
async def list_bigscreens():
    # 返回数据接口
    try:
        # 查询成功
        result = big_screen_service.list_bigscreen()
        return result
    except Exception as e:
        return None


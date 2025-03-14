from fastapi import HTTPException
from api.model.cluster import ClusterObject

from starlette import status
from api.model.system import OperateLogApiModel
from services.cluster import ClusterService
from services.system import SystemService
from services.custom_exception import Fail
from fastapi import APIRouter, HTTPException
    
router = APIRouter()

@router.post("/cluster", summary="创建k8s集群", description="创建k8s集群")
async def create_cluster(cluster_object:ClusterObject):
    try:
        # 集群信息存入数据库
        result = ClusterService.create_cluster(cluster_object)
        # 操作日志
        SystemService.create_system_log(OperateLogApiModel(operate_type="create", resource_type="flow", resource_id=result, resource_name=cluster_object.name, operate_flag=True))
        return result
    except Fail as e:
        raise HTTPException(status_code=400, detail=e.error_message)
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=400, detail="asset flow create error")

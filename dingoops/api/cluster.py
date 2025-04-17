from fastapi import HTTPException, Query
from dingoops.api.model.cluster import ClusterObject

from starlette import status
from dingoops.api.model.system import OperateLogApiModel
from dingoops.services.cluster import ClusterService
from dingoops.services.system import SystemService
from dingoops.services.custom_exception import Fail
from fastapi import APIRouter, HTTPException
    
router = APIRouter()
cluster_service = ClusterService()

@router.post("/cluster", summary="创建k8s集群", description="创建k8s集群")
async def create_cluster(cluster_object:ClusterObject):
    try:
        # 集群信息存入数据库
        result = cluster_service.create_cluster(cluster_object)
        # 操作日志
        SystemService.create_system_log(OperateLogApiModel(operate_type="create", resource_type="flow", resource_id=result, resource_name=cluster_object.name, operate_flag=True))
        return result
    except Fail as e:
        raise HTTPException(status_code=400, detail=e.error_message)
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=400, detail="asset flow create error")
    
@router.get("/cluster/list", summary="k8s集群列表", description="k8s集群列表")
async def list_cluster(id:str = Query(None, description="集群id"),
        name:str = Query(None, description="集群名称"),
        type:str = Query(None, description="集群类型"),
        page: int = Query(1, description="页码"),
        page_size: int = Query(10, description="页数量大小"),
        sort_keys:str = Query(None, description="排序字段"),
        sort_dirs:str = Query(None, description="排序方式"),):
    try:
         # 声明查询条件的dict
        query_params = {}
        # 查询条件组装
        if name:
            query_params['name'] = name
        if type:
            query_params['type'] = type
        query_params = {}
        # 查询条件组装
        if id:
            query_params['id'] = id
        if name:
            query_params['name'] = name
        if type:
            query_params['type'] = type
        result = ClusterService.list_clusters(id, query_params, page,page_size, sort_keys,sort_dirs)
        return result
    except Exception as e:
        return None
    
@router.get("/cluster/{cluster_id}", summary="获取k8s集群详情", description="获取k8s集群详情")
async def get_cluster(cluster_id:str):
    try:
        # 集群信息存入数据库
        result = cluster_service.get_cluster(cluster_id)
        # 操作日志
        #SystemService.create_system_log(OperateLogApiModel(operate_type="create", resource_type="flow", resource_id=result, resource_name=cluster_object.name, operate_flag=True))
        return result
    except Fail as e:
        raise HTTPException(status_code=400, detail=e.error_message)
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=400, detail="get cluster error")

@router.delete("/cluster/{cluster_id}", summary="删除k8s集群", description="删除k8s集群")
async def get_cluster(cluster_id:str):
    try:
        # 集群信息存入数据库
        result = cluster_service.get_cluster(cluster_id)
        # 操作日志
        #SystemService.create_system_log(OperateLogApiModel(operate_type="create", resource_type="flow", resource_id=result, resource_name=cluster_object.name, operate_flag=True))
        return result
    except Fail as e:
        raise HTTPException(status_code=400, detail=e.error_message)
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=400, detail="get cluster error")
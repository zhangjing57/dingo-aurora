from dingoops.api.model.cluster import ClusterObject
from dingoops.api.model import router
from starlette import status
from api.model.system import OperateLogApiModel
from dingoops.services.cluster import ClusterService
from services.system import SystemService
from services.custom_exception import Fail


@router.post(  # type: ignore
    "", status_code=status.HTTP_303_SEE_OTHER, responses=api_models.ErrorResponses
)
    
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
    
@router.get("/clusters", summary="创建网络设备的流转数据", description="创建网络设备的流转数据")
async def create_asset_flow(asset_flow:AssetFlowApiModel):
    # 创建资产类型
    try:
        # 创建成功
        result = assert_service.create_asset_flow(asset_flow)
        # 操作日志
        system_service.create_system_log(OperateLogApiModel(operate_type="create", resource_type="flow", resource_id=result, resource_name=asset_flow.label, operate_flag=True))
        return result
    except Fail as e:
        raise HTTPException(status_code=400, detail=e.error_message)
    except Exception as e:
        import traceback
        traceback.print_exc()   
        raise HTTPException(status_code=400, detail="asset flow create error")
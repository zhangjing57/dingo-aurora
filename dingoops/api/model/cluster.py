
from typing import Optional

from pydantic import Field
from dingoops.api.model.base import DingoopsObject


class ClusterObject(DingoopsObject):
    project_id: Optional[str] = Field(None, description="项目id")
    user_id: Optional[str] = Field(None, description="用户id")
    keypair: Optional[str] = Field(None, description="密钥对")
    flavor_id: Optional[str] = Field(None, description="规格id")
    labels: Optional[str] = Field(None, description="集群标签")
    status: Optional[str] = Field(None, description="集群状态")
    status_msg: Optional[str] = Field(None, description="集群状态原因")
    region_name: Optional[str] = Field(None, description="region名称")
    network_id: Optional[str] = Field(None, description="网络id")
    subnet_id: Optional[str] = Field(None, description="子网id")
    api_address: Optional[str] = Field(None, description="管理网访问地址")
    bus_address: Optional[str] = Field(None, description="业务网nodeport暴露地址")
    runtime: Optional[str] = Field(None, description="运行时类型")
    type: Optional[str] = Field(None, description="集群类型")
    service_cidr: Optional[str] = Field(None, description="服务网段")
    version: Optional[str] = Field(None, description="k8s版本")
    cni: Optional[str] = Field(None, description="cni插件")
    kube_config: Optional[str] = Field(None, description="cni插件")
   
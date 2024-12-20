import uuid
import sys

from db.models.bigscreen.sql import BigscreenSQL
from db.models.bigscreen.models import BigscreenMetricsConfig

bigscreen_metrics_config_data = [
    {
        "name": "gpu_average_temperature",
        "description": "GPU平均温度",
        "query": 'avg(DCGM_FI_DEV_GPU_TEMP)'
    },
    {
        "name": "gpu_total_power",
        "description": "GPU总功率",
        "query": 'sum(DCGM_FI_DEV_POWER_USAGE)'
    },
    {
        "name": "gpu_average_utilization",
        "description": "GPU平均利用率",
        "query": 'avg(DCGM_FI_DEV_GPU_UTIL)'
    },
    {
        "name": "cpu_nodes_count",
        "description": "CPU管理节点数",
        "query": 'count(node_uname_info{job="consul",hostname!~".*gpu.*"})'
    },
    {
        "name": "gpu_nodes_count",
        "description": "GPU节点数",
        "query": 'count(node_uname_info{job="consul",hostname=~".*gpu.*"})'
    },
    {
        "name": "storage_nodes_count",
        "description": "存储节点数",
        "query": 'count(node_uname_info{job="consul",hostname=~".*ceph.*"})'
    },
    {
        "name": "gpu_count",
        "description": "GPU卡数",
        "query": 'count(DCGM_FI_DEV_GPU_UTIL)'
    },
    {
        "name": "gpu_memory_usage",
        "description": "GPU显存使用率",
        "query": 'avg(DCGM_FI_DEV_FB_USED/(DCGM_FI_DEV_FB_USED+DCGM_FI_DEV_FB_FREE))'
    },
]

for item in bigscreen_metrics_config_data:
    item["id"] = uuid.uuid4().hex
    bigscreen_metrics_config_info = BigscreenMetricsConfig(**item)
    BigscreenSQL.create_bigscreen_metrics_config(bigscreen_metrics_config_info)

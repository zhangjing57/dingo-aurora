from pymemcache.client.base import Client
from config.settings import settings
from apscheduler.schedulers.background import BackgroundScheduler
from services.bigscreens import BigScreensService

scheduler = BackgroundScheduler()

def start():
    scheduler.add_job(fetch_bigscreen_metrics, 'interval', seconds=settings.metrics_fetch_interval)
    scheduler.start()

def fetch_bigscreen_metrics():
    metrics = BigScreensService.list_bigscreen_metrics_configs()
    memcached_client = Client((settings.memcached_address))
    metrics_dict = {}
    for metric in metrics:
        metric_name = metric.name
        metric_value = BigScreensService.get_bigscreen_metrics(metric_name)
        metrics_dict[f'{settings.memcached_key_prefix}{metric_name}'] = metric_value

    try:
        memcached_client.set_many(metrics_dict, expire=settings.metrics_expiration_time)
    except Exception as e:
        print(f"大屏指标缓存写入失败")

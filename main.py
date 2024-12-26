from fastapi import FastAPI
from api import api_router
from jobs import bigscreen_metrics_syncer

PROJECT_NAME = "dingoops"

app = FastAPI(
    title=PROJECT_NAME,
    openapi_url="/v1/openapi.json",
)

app.include_router(api_router, prefix="/v1")

@app.on_event("startup")
async def app_start():
    bigscreen_metrics_syncer.start()

# 本地启动作测试使用
if __name__ == '__main__':
    import uvicorn

    uvicorn.run("main:app", reload=True, host="0.0.0.0", port=8888)

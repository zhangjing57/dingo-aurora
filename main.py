from fastapi import FastAPI
from api import api_router

PROJECT_NAME = "dingoops"

app = FastAPI(
    title=PROJECT_NAME,
    openapi_url="/v1/openapi.json",
)

@app.get("/", description="根url")
async def root():
    return {"message": "Welcome to the dingoops!"}

@app.get("/v1", description="版本号url")
async def root():
    return {"message": "Welcome to the dingoops of version v1!"}

app.include_router(api_router, prefix="/v1")

# 本地启动作测试使用
if __name__ == '__main__':
    import uvicorn

    uvicorn.run("main:app", reload=True, host="0.0.0.0", port=8889)
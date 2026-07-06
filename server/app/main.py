from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from .core.config import get_settings
from .core.database import engine, Base
from .core.redis import redis_subscriber_task
from .api.v1 import device, task, audio, result, search, alert, auth, speaker, stats, settings as settings_router
from .api.ws import websocket_endpoint

app_settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    Base.metadata.create_all(bind=engine)

    # Ensure MinIO bucket exists
    try:
        from minio import Minio
        mc = Minio(
            app_settings.MINIO_ENDPOINT,
            access_key=app_settings.MINIO_ACCESS_KEY,
            secret_key=app_settings.MINIO_SECRET_KEY,
            secure=app_settings.MINIO_SECURE,
        )
        if not mc.bucket_exists(app_settings.MINIO_BUCKET):
            mc.make_bucket(app_settings.MINIO_BUCKET)
            print(f"Created MinIO bucket: {app_settings.MINIO_BUCKET}")
    except Exception as e:
        print(f"MinIO bucket check failed: {e}")

    # Start background tasks
    import asyncio
    from .services.inference_worker import inference_worker
    ws_task = asyncio.create_task(redis_subscriber_task())
    worker_task = asyncio.create_task(inference_worker())
    yield
    # Shutdown
    ws_task.cancel()
    worker_task.cancel()


app = FastAPI(
    title=app_settings.APP_NAME,
    version=app_settings.APP_VERSION,
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(auth.router, prefix="/api/auth", tags=["认证"])
app.include_router(device.router, prefix="/api/device", tags=["设备管理"])
app.include_router(task.router, prefix="/api/task", tags=["任务管理"])
app.include_router(audio.router, prefix="/api/audio", tags=["音频管理"])
app.include_router(result.router, prefix="/api/result", tags=["识别结果"])
app.include_router(search.router, prefix="/api/search", tags=["检索"])
app.include_router(alert.router, prefix="/api/alert", tags=["告警"])
app.include_router(speaker.router, prefix="/api/speaker", tags=["说话人管理"])
app.include_router(stats.router, prefix="/api/stats", tags=["统计"])
app.include_router(settings_router.router, prefix="/api/settings", tags=["系统设置"])

# WebSocket
app.add_api_websocket_route("/ws/realtime", websocket_endpoint)


@app.get("/")
async def root():
    return {"message": app_settings.APP_NAME, "version": app_settings.APP_VERSION}


@app.get("/health")
async def health():
    return {"status": "ok"}

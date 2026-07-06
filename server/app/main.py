from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from .core.config import get_settings
from .core.database import engine, Base
from .api.v1 import device, task, audio, result, search, alert, auth

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    Base.metadata.create_all(bind=engine)
    yield
    # Shutdown


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
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


@app.get("/")
async def root():
    return {"message": settings.APP_NAME, "version": settings.APP_VERSION}


@app.get("/health")
async def health():
    return {"status": "ok"}

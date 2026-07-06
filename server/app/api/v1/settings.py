import json
import os
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional

from ...core.security import get_current_user

router = APIRouter()

SETTINGS_FILE = os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "settings.json")

DEFAULT_SETTINGS = {
    "aiEngineUrl": "http://localhost:8001",
    "minioEndpoint": "localhost:9000",
    "sampleRate": 16000,
    "audioFormat": "opus",
    "segmentDuration": 5,
    "hotwords": "",
    "speakerThreshold": 0.6,
    "retentionDays": 90,
}


class SystemSettings(BaseModel):
    aiEngineUrl: str = "http://localhost:8001"
    minioEndpoint: str = "localhost:9000"
    sampleRate: int = 16000
    audioFormat: str = "opus"
    segmentDuration: int = 5
    hotwords: str = ""
    speakerThreshold: float = 0.6
    retentionDays: int = 90


def _load_settings() -> dict:
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, "r") as f:
            return json.load(f)
    return DEFAULT_SETTINGS.copy()


def _save_settings(data: dict):
    os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
    with open(SETTINGS_FILE, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


@router.get("", response_model=SystemSettings)
async def get_settings(user: dict = Depends(get_current_user)):
    return _load_settings()


@router.put("", response_model=SystemSettings)
async def update_settings(
    data: SystemSettings,
    user: dict = Depends(get_current_user),
):
    _save_settings(data.model_dump())
    return data

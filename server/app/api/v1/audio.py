import os
import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from minio import Minio

from ...core.database import get_db
from ...core.config import get_settings
from ...core.security import get_current_user
from ...models.audio import AudioRecord
from ...models.device import Device

router = APIRouter()
settings = get_settings()

minio_client = Minio(
    settings.MINIO_ENDPOINT,
    access_key=settings.MINIO_ACCESS_KEY,
    secret_key=settings.MINIO_SECRET_KEY,
    secure=settings.MINIO_SECURE,
)


class AudioResponse(BaseModel):
    id: int
    device_id: int
    task_id: Optional[int]
    file_path: str
    file_size: Optional[int]
    duration_ms: Optional[int]
    sample_rate: int
    format: str
    upload_time: datetime
    inference_status: str

    class Config:
        from_attributes = True


@router.post("/upload")
async def upload_audio(
    device_code: str = Query(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    # Find device
    device = db.query(Device).filter(Device.device_code == device_code).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    # Generate unique filename
    file_ext = os.path.splitext(file.filename)[1] or ".opus"
    object_name = f"audio/{device.device_code}/{datetime.utcnow().strftime('%Y%m%d')}/{uuid.uuid4().hex}{file_ext}"

    # Upload to MinIO
    file_data = await file.read()
    from io import BytesIO

    minio_client.put_object(
        settings.MINIO_BUCKET,
        object_name,
        BytesIO(file_data),
        length=len(file_data),
        content_type=file.content_type,
    )

    # Save to database
    audio_record = AudioRecord(
        device_id=device.id,
        file_path=object_name,
        file_size=len(file_data),
        format=file_ext.lstrip("."),
    )
    db.add(audio_record)
    device.last_upload = datetime.utcnow()
    db.commit()
    db.refresh(audio_record)

    # TODO: Push to Redis queue for AI inference
    # await publish_message("audio:pending_inference", str(audio_record.id))

    return {"id": audio_record.id, "file_path": object_name, "status": "uploaded"}


@router.get("/list", response_model=List[AudioResponse])
async def list_audio(
    device_id: Optional[int] = Query(None),
    task_id: Optional[int] = Query(None),
    inference_status: Optional[str] = Query(None),
    start_time: Optional[datetime] = Query(None),
    end_time: Optional[datetime] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    query = db.query(AudioRecord)
    if device_id:
        query = query.filter(AudioRecord.device_id == device_id)
    if task_id:
        query = query.filter(AudioRecord.task_id == task_id)
    if inference_status:
        query = query.filter(AudioRecord.inference_status == inference_status)
    if start_time:
        query = query.filter(AudioRecord.upload_time >= start_time)
    if end_time:
        query = query.filter(AudioRecord.upload_time <= end_time)
    return query.order_by(AudioRecord.upload_time.desc()).offset(skip).limit(limit).all()


@router.get("/{audio_id}", response_model=AudioResponse)
async def get_audio(
    audio_id: int,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    audio = db.query(AudioRecord).filter(AudioRecord.id == audio_id).first()
    if not audio:
        raise HTTPException(status_code=404, detail="Audio not found")
    return audio


@router.get("/{audio_id}/download")
async def download_audio(
    audio_id: int,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    audio = db.query(AudioRecord).filter(AudioRecord.id == audio_id).first()
    if not audio:
        raise HTTPException(status_code=404, detail="Audio not found")

    # Generate presigned URL
    url = minio_client.presigned_get_object(settings.MINIO_BUCKET, audio.file_path)
    return {"url": url}

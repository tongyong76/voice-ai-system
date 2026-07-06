import os
import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from minio import Minio
from io import BytesIO

from ...core.database import get_db
from ...core.config import get_settings
from ...core.security import get_current_user
from ...models.result import Speaker

router = APIRouter()
settings = get_settings()

minio_client = Minio(
    settings.MINIO_ENDPOINT,
    access_key=settings.MINIO_ACCESS_KEY,
    secret_key=settings.MINIO_SECRET_KEY,
    secure=settings.MINIO_SECURE,
)


class SpeakerResponse(BaseModel):
    id: int
    name: str
    tags: Optional[list]
    created_at: datetime

    class Config:
        from_attributes = True


class SpeakerUpdate(BaseModel):
    name: Optional[str] = None
    tags: Optional[list] = None


@router.get("/list", response_model=List[SpeakerResponse])
async def list_speakers(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    speakers = db.query(Speaker).offset(skip).limit(limit).all()
    return speakers


@router.get("/{speaker_id}", response_model=SpeakerResponse)
async def get_speaker(
    speaker_id: int,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    speaker = db.query(Speaker).filter(Speaker.id == speaker_id).first()
    if not speaker:
        raise HTTPException(status_code=404, detail="Speaker not found")
    return speaker


@router.post("/enroll")
async def enroll_speaker(
    name: str = Form(...),
    tags: str = Form(""),
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Enroll a new speaker with audio samples"""
    import httpx

    # Upload audio files to MinIO
    audio_paths = []
    for file in files:
        file_data = await file.read()
        object_name = f"speakers/{uuid.uuid4().hex}{os.path.splitext(file.filename)[1] or '.wav'}"
        minio_client.put_object(
            settings.MINIO_BUCKET,
            object_name,
            BytesIO(file_data),
            length=len(file_data),
            content_type=file.content_type,
        )
        audio_paths.append(object_name)

    # Create speaker record in DB
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []
    speaker = Speaker(name=name, tags=tag_list)
    db.add(speaker)
    db.commit()
    db.refresh(speaker)

    # Call AI engine to enroll
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{settings.AI_ENGINE_URL}/enroll",
                json={
                    "speaker_id": speaker.id,
                    "audio_paths": audio_paths,
                    "name": name,
                    "tags": tag_list,
                },
            )
            if resp.status_code != 200:
                print(f"AI engine enroll warning: {resp.text}")
    except Exception as e:
        print(f"AI engine enroll error: {e}")

    return {
        "id": speaker.id,
        "name": speaker.name,
        "tags": speaker.tags,
        "audio_paths": audio_paths,
        "status": "enrolled",
    }


@router.put("/{speaker_id}", response_model=SpeakerResponse)
async def update_speaker(
    speaker_id: int,
    data: SpeakerUpdate,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    speaker = db.query(Speaker).filter(Speaker.id == speaker_id).first()
    if not speaker:
        raise HTTPException(status_code=404, detail="Speaker not found")
    if data.name is not None:
        speaker.name = data.name
    if data.tags is not None:
        speaker.tags = data.tags
    db.commit()
    db.refresh(speaker)
    return speaker


@router.delete("/{speaker_id}")
async def delete_speaker(
    speaker_id: int,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    speaker = db.query(Speaker).filter(Speaker.id == speaker_id).first()
    if not speaker:
        raise HTTPException(status_code=404, detail="Speaker not found")
    db.delete(speaker)
    db.commit()
    return {"status": "deleted"}

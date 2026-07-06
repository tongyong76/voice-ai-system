from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List

from ...core.database import get_db
from ...core.security import get_current_user
from ...models.result import Transcript, SpeakerRecord, EmotionRecord, NLUResult, Speaker

router = APIRouter()


class TranscriptResponse(BaseModel):
    id: int
    audio_id: int
    full_text: Optional[str]
    language: str
    segments: Optional[list]

    class Config:
        from_attributes = True


class SpeakerRecordResponse(BaseModel):
    id: int
    audio_id: int
    speaker_label: Optional[str]
    speaker_id: Optional[int]
    confidence: Optional[float]
    start_ms: Optional[int]
    end_ms: Optional[int]

    class Config:
        from_attributes = True


class EmotionResponse(BaseModel):
    id: int
    audio_id: int
    label: Optional[str]
    confidence: Optional[float]
    start_ms: Optional[int]
    end_ms: Optional[int]

    class Config:
        from_attributes = True


class NLUResponse(BaseModel):
    id: int
    audio_id: int
    keywords: Optional[list]
    intent: Optional[str]
    entities: Optional[dict]

    class Config:
        from_attributes = True


@router.get("/transcript/{audio_id}", response_model=List[TranscriptResponse])
async def get_transcript(
    audio_id: int,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    results = db.query(Transcript).filter(Transcript.audio_id == audio_id).all()
    return results


@router.get("/speaker/{audio_id}", response_model=List[SpeakerRecordResponse])
async def get_speaker_records(
    audio_id: int,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    results = db.query(SpeakerRecord).filter(SpeakerRecord.audio_id == audio_id).all()
    return results


@router.get("/emotion/{audio_id}", response_model=List[EmotionResponse])
async def get_emotion_records(
    audio_id: int,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    results = db.query(EmotionRecord).filter(EmotionRecord.audio_id == audio_id).all()
    return results


@router.get("/nlu/{audio_id}", response_model=List[NLUResponse])
async def get_nlu_results(
    audio_id: int,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    results = db.query(NLUResult).filter(NLUResult.audio_id == audio_id).all()
    return results


@router.get("/speakers")
async def list_speakers(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    speakers = db.query(Speaker).offset(skip).limit(limit).all()
    return speakers

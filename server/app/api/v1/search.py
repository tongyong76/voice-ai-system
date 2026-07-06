from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import Optional, List

from ...core.database import get_db
from ...core.security import get_current_user
from ...models.result import Transcript, Speaker, EmotionRecord

router = APIRouter()


@router.get("/transcript")
async def search_transcripts(
    q: str = Query(..., min_length=1),
    device_id: Optional[int] = Query(None),
    start_time: Optional[str] = Query(None),
    end_time: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    query = db.query(Transcript).filter(Transcript.full_text.contains(q))

    # Join with audio records for filtering
    from ...models.audio import AudioRecord

    query = query.join(AudioRecord, Transcript.audio_id == AudioRecord.id)

    if device_id:
        query = query.filter(AudioRecord.device_id == device_id)
    if start_time:
        query = query.filter(AudioRecord.upload_time >= start_time)
    if end_time:
        query = query.filter(AudioRecord.upload_time <= end_time)

    results = query.offset(skip).limit(limit).all()

    return [
        {
            "transcript_id": r.id,
            "audio_id": r.audio_id,
            "text": r.full_text,
            "segments": r.segments,
        }
        for r in results
    ]


@router.get("/speaker")
async def search_speaker(
    speaker_name: Optional[str] = Query(None),
    speaker_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    query = db.query(Speaker)
    if speaker_name:
        query = query.filter(Speaker.name.contains(speaker_name))
    if speaker_id:
        query = query.filter(Speaker.id == speaker_id)
    return query.all()

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional, List

from ...core.database import get_db
from ...core.security import get_current_user
from ...core.search import search_transcripts as redis_search
from ...models.result import Transcript, Speaker

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
    # 1. RediSearch 全文检索, 获取匹配的 transcript_id 列表
    hits = await redis_search(
        query=q,
        device_id=device_id,
        start_time=start_time,
        end_time=end_time,
        offset=skip,
        limit=limit,
    )

    if not hits:
        return []

    # 2. 收集 audio_id, 去 MySQL 做二次过滤 (device_id / 时间范围)
    transcript_ids = [h["transcript_id"] for h in hits]
    audio_ids = list(set(h["audio_id"] for h in hits))

    from ...models.audio import AudioRecord

    query = db.query(Transcript).filter(Transcript.id.in_(transcript_ids))

    # 如果有设备/时间过滤, 通过 audio_records 表二次筛选
    if device_id or start_time or end_time:
        audio_query = db.query(AudioRecord.id).filter(AudioRecord.id.in_(audio_ids))
        if device_id:
            audio_query = audio_query.filter(AudioRecord.device_id == device_id)
        if start_time:
            audio_query = audio_query.filter(AudioRecord.upload_time >= start_time)
        if end_time:
            audio_query = audio_query.filter(AudioRecord.upload_time <= end_time)
        valid_audio_ids = [r[0] for r in audio_query.all()]
        query = query.filter(Transcript.audio_id.in_(valid_audio_ids))

    results = query.all()

    # 3. 构建返回结果, 保留 RediSearch 的排序
    result_map = {r.id: r for r in results}
    return [
        {
            "transcript_id": h["transcript_id"],
            "audio_id": h["audio_id"],
            "text": result_map[h["transcript_id"]].full_text if h["transcript_id"] in result_map else h["text"],
            "segments": result_map[h["transcript_id"]].segments if h["transcript_id"] in result_map else None,
        }
        for h in hits
        if h["transcript_id"] in result_map
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

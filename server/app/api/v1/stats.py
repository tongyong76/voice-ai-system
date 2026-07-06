from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta

from ...core.database import get_db
from ...core.security import get_current_user
from ...models.device import Device
from ...models.audio import AudioRecord
from ...models.result import Speaker, EmotionRecord, AlertLog

router = APIRouter()


@router.get("/dashboard")
async def get_dashboard_stats(
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Get dashboard statistics"""
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    # Online devices
    online_devices = db.query(func.count(Device.id)).filter(Device.status == "online").scalar() or 0

    # Today's audio hours
    today_audio_ms = (
        db.query(func.sum(AudioRecord.duration_ms))
        .filter(AudioRecord.upload_time >= today)
        .scalar()
        or 0
    )
    today_audio_hours = round(today_audio_ms / 3600000, 1)

    # Total speakers
    speaker_count = db.query(func.count(Speaker.id)).scalar() or 0

    # Today's alerts
    alert_count = (
        db.query(func.count(AlertLog.id))
        .filter(AlertLog.triggered_at >= today)
        .scalar()
        or 0
    )

    return {
        "onlineDevices": online_devices,
        "todayAudio": today_audio_hours,
        "speakerCount": speaker_count,
        "alertCount": alert_count,
    }


@router.get("/trend")
async def get_collection_trend(
    days: int = 1,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Get audio collection trend (hourly for today, daily for longer periods)"""
    now = datetime.utcnow()

    if days <= 1:
        # Hourly trend for today
        today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        hourly = []
        for h in range(24):
            start = today + timedelta(hours=h)
            end = start + timedelta(hours=1)
            total_ms = (
                db.query(func.sum(AudioRecord.duration_ms))
                .filter(AudioRecord.upload_time >= start, AudioRecord.upload_time < end)
                .scalar()
                or 0
            )
            hourly.append({"hour": f"{h}:00", "hours": round(total_ms / 3600000, 2)})
        return hourly
    else:
        # Daily trend
        daily = []
        for d in range(days):
            day = (now - timedelta(days=d)).replace(hour=0, minute=0, second=0, microsecond=0)
            next_day = day + timedelta(days=1)
            total_ms = (
                db.query(func.sum(AudioRecord.duration_ms))
                .filter(AudioRecord.upload_time >= day, AudioRecord.upload_time < next_day)
                .scalar()
                or 0
            )
            daily.append({
                "date": day.strftime("%m-%d"),
                "hours": round(total_ms / 3600000, 2),
            })
        return list(reversed(daily))


@router.get("/emotion-distribution")
async def get_emotion_distribution(
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Get emotion distribution"""
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    results = (
        db.query(EmotionRecord.label, func.count(EmotionRecord.id))
        .filter(EmotionRecord.id.in_(
            db.query(EmotionRecord.id)
            .join(AudioRecord, EmotionRecord.audio_id == AudioRecord.id)
            .filter(AudioRecord.upload_time >= today)
        ))
        .group_by(EmotionRecord.label)
        .all()
    )

    label_map = {
        "happy": "积极",
        "sad": "消极",
        "angry": "愤怒",
        "fear": "恐惧",
        "surprise": "惊讶",
        "disgust": "厌恶",
        "neutral": "中性",
    }

    return [
        {"name": label_map.get(label, label), "value": count}
        for label, count in results
    ]


@router.get("/recent-audio")
async def get_recent_audio(
    limit: int = 10,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Get recent audio records for dashboard"""
    audios = (
        db.query(AudioRecord)
        .order_by(AudioRecord.upload_time.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": a.id,
            "device_id": a.device_id,
            "upload_time": a.upload_time.isoformat() if a.upload_time else None,
            "duration_ms": a.duration_ms,
            "inference_status": a.inference_status,
        }
        for a in audios
    ]


@router.get("/recent-alerts")
async def get_recent_alerts(
    limit: int = 10,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Get recent alert logs for dashboard"""
    alerts = (
        db.query(AlertLog)
        .order_by(AlertLog.triggered_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": a.id,
            "rule_id": a.rule_id,
            "audio_id": a.audio_id,
            "triggered_at": a.triggered_at.isoformat() if a.triggered_at else None,
            "acknowledged": a.acknowledged,
            "message": f"规则 #{a.rule_id} 触发告警",
        }
        for a in alerts
    ]

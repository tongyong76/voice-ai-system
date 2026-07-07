"""
Background worker: consume audio from Redis queue, call AI engine, save results to DB.
"""
import json
import asyncio
import traceback
import httpx
from datetime import datetime

from ..core.config import get_settings
from ..core.redis import get_redis, publish_message
from ..core.search import index_transcript
from ..core.database import SessionLocal
from ..models.audio import AudioRecord
from ..models.result import Transcript, SpeakerRecord, EmotionRecord, NLUResult

settings = get_settings()

AI_ENGINE_URL = settings.AI_ENGINE_URL


async def process_audio(audio_id: int, file_path: str):
    """Call AI engine and save results to database"""
    db = SessionLocal()
    try:
        # Update status to processing
        audio = db.query(AudioRecord).filter(AudioRecord.id == audio_id).first()
        if not audio:
            print(f"Audio {audio_id} not found")
            return
        audio.inference_status = "processing"
        db.commit()

        # Call AI engine
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{AI_ENGINE_URL}/inference",
                json={"audio_path": file_path},
            )
            if resp.status_code != 200:
                raise Exception(f"AI engine error: {resp.text}")
            result = resp.json()

        # Save ASR transcript
        asr = result.get("asr", {})
        if asr.get("text"):
            transcript = Transcript(
                audio_id=audio_id,
                full_text=asr["text"],
                language=asr.get("language", "zh"),
                segments=asr.get("segments"),
            )
            db.add(transcript)

        # Save speaker record
        speaker = result.get("speaker", {})
        if speaker:
            speaker_record = SpeakerRecord(
                audio_id=audio_id,
                speaker_id=speaker.get("speaker_id"),
                confidence=speaker.get("confidence", 0.0),
            )
            db.add(speaker_record)

        # Save emotion records
        emotions = result.get("emotions", [])
        for emo in emotions:
            emotion_record = EmotionRecord(
                audio_id=audio_id,
                label=emo.get("label"),
                confidence=emo.get("confidence", 0.0),
                start_ms=emo.get("start_ms", 0),
                end_ms=emo.get("end_ms", 0),
            )
            db.add(emotion_record)

        # Save NLU results
        nlu = result.get("nlu", {})
        if nlu:
            nlu_result = NLUResult(
                audio_id=audio_id,
                keywords=nlu.get("keywords"),
                intent=nlu.get("intent"),
                entities=nlu.get("entities"),
            )
            db.add(nlu_result)

        # Update status to completed
        audio.inference_status = "completed"
        db.commit()

        # 索引到 RediSearch (全文检索)
        try:
            if asr.get("text") and transcript:
                await index_transcript(
                    transcript_id=transcript.id,
                    audio_id=audio_id,
                    full_text=asr["text"],
                    language=asr.get("language", "zh"),
                )
        except Exception as e:
            print(f"RediSearch indexing error (non-fatal): {e}")

        # Publish result to WebSocket via Redis pub/sub
        await publish_message(
            "audio:inference_result",
            json.dumps({
                "channel": "realtime",
                "audio_id": audio_id,
                "device_id": audio.device_id,
                "text": asr.get("text", ""),
                "emotion": emotions[0].get("label") if emotions else None,
                "speaker_id": speaker.get("speaker_id"),
                "timestamp": datetime.utcnow().isoformat(),
            }),
        )

        print(f"Audio {audio_id} inference completed")

    except Exception as e:
        print(f"Inference error for audio {audio_id}: {e}")
        traceback.print_exc()
        # Mark as failed
        try:
            audio = db.query(AudioRecord).filter(AudioRecord.id == audio_id).first()
            if audio:
                audio.inference_status = "failed"
                db.commit()
        except Exception:
            pass
    finally:
        db.close()


async def inference_worker():
    """Background worker: listen to Redis queue and process audio"""
    while True:
        try:
            r = await get_redis()
            pubsub = r.pubsub()
            await pubsub.subscribe("audio:pending_inference")

            async for message in pubsub.listen():
                if message["type"] == "message":
                    try:
                        data = json.loads(message["data"])
                        audio_id = data["audio_id"]
                        file_path = data["file_path"]
                        # Process in background so we don't block the queue
                        asyncio.create_task(process_audio(audio_id, file_path))
                    except Exception as e:
                        print(f"Error parsing queue message: {e}")
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"Inference worker error: {e}, reconnecting in 5s...")
            await asyncio.sleep(5)

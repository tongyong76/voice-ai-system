import os
import json
import asyncio
import tempfile
from typing import Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from minio import Minio

from .pipeline.pipeline import get_pipeline
from .speaker_db.search import get_speaker_db
from .speaker_db.enroll import get_enroller

app = FastAPI(title="Voice AI Inference Engine", version="1.0.0")

# MinIO client
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin")
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "voice-audio")

minio_client = Minio(
    MINIO_ENDPOINT,
    access_key=MINIO_ACCESS_KEY,
    secret_key=MINIO_SECRET_KEY,
    secure=False,
)

# Initialize components
speaker_db = get_speaker_db()
pipeline = get_pipeline(speaker_db=speaker_db)
enroller = get_enroller()


class InferenceRequest(BaseModel):
    audio_path: str  # MinIO object path
    hotwords: Optional[str] = None


class EnrollRequest(BaseModel):
    speaker_id: int
    audio_paths: list  # List of MinIO object paths
    name: str = ""
    tags: list = []


class SearchRequest(BaseModel):
    audio_path: str  # MinIO object path
    threshold: float = 0.6


def download_from_minio(object_path: str) -> str:
    """Download file from MinIO to temp path"""
    suffix = os.path.splitext(object_path)[1] or ".wav"
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    minio_client.fget_object(MINIO_BUCKET, object_path, tmp.name)
    return tmp.name


@app.on_event("startup")
async def startup():
    print("AI Engine started")
    print(f"Speaker DB size: {speaker_db.size}")


@app.post("/inference")
async def run_inference(request: InferenceRequest):
    """Run full inference pipeline on audio"""
    try:
        audio_path = download_from_minio(request.audio_path)
        result = pipeline.process(audio_path, hotwords=request.hotwords)
        os.unlink(audio_path)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/enroll")
async def enroll_speaker(request: EnrollRequest):
    """Enroll a speaker from audio samples"""
    try:
        audio_paths = []
        for path in request.audio_paths:
            audio_paths.append(download_from_minio(path))

        result = enroller.enroll_from_audio(
            speaker_id=request.speaker_id,
            audio_paths=audio_paths,
            name=request.name,
            tags=request.tags,
        )

        # Cleanup temp files
        for path in audio_paths:
            os.unlink(path)

        # Save index
        speaker_db.save()

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/search_speaker")
async def search_speaker(request: SearchRequest):
    """Search for speaker in database"""
    try:
        audio_path = download_from_minio(request.audio_path)

        from .pipeline.speaker_engine import get_speaker_engine
        engine = get_speaker_engine()
        embedding = engine.extract_embedding(audio_path)

        speaker_id, confidence = speaker_db.search(embedding, threshold=request.threshold)

        os.unlink(audio_path)

        return {
            "speaker_id": speaker_id,
            "confidence": confidence,
            "speaker_info": speaker_db.get_info(speaker_id) if speaker_id else None,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/speaker_db/stats")
async def speaker_db_stats():
    """Get speaker database statistics"""
    return {
        "total_speakers": speaker_db.size,
        "index_trained": speaker_db.index.is_trained if speaker_db.index else False,
    }


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)

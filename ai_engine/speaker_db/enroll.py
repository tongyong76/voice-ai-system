import numpy as np
from typing import Optional, List
from .search import get_speaker_db
from ..pipeline.speaker_engine import get_speaker_engine


class SpeakerEnroller:
    def __init__(self):
        self.speaker_db = get_speaker_db()
        self.speaker_engine = get_speaker_engine()

    def enroll_from_audio(
        self,
        speaker_id: int,
        audio_paths: List[str],
        name: str = "",
        tags: List[str] = None,
    ) -> dict:
        """
        Enroll a speaker from one or more audio samples.

        Args:
            speaker_id: Unique speaker ID
            audio_paths: List of audio file paths
            name: Speaker name
            tags: Speaker tags

        Returns:
            {"status": "enrolled", "speaker_id": speaker_id, "num_samples": len(audio_paths)}
        """
        embeddings = []
        for audio_path in audio_paths:
            embedding = self.speaker_engine.extract_embedding(audio_path)
            if not np.all(embedding == 0):
                embeddings.append(embedding)

        if not embeddings:
            return {"status": "error", "message": "No valid embeddings extracted"}

        # Average embeddings for better accuracy
        avg_embedding = np.mean(embeddings, axis=0)

        self.speaker_db.add(
            speaker_id=speaker_id,
            embedding=avg_embedding,
            name=name,
            tags=tags,
        )

        return {
            "status": "enrolled",
            "speaker_id": speaker_id,
            "num_samples": len(embeddings),
        }

    def enroll_from_embedding(
        self,
        speaker_id: int,
        embedding: np.ndarray,
        name: str = "",
        tags: List[str] = None,
    ) -> dict:
        """
        Enroll a speaker from pre-computed embedding.

        Args:
            speaker_id: Unique speaker ID
            embedding: Speaker embedding vector
            name: Speaker name
            tags: Speaker tags

        Returns:
            {"status": "enrolled", "speaker_id": speaker_id}
        """
        self.speaker_db.add(
            speaker_id=speaker_id,
            embedding=embedding,
            name=name,
            tags=tags,
        )
        return {"status": "enrolled", "speaker_id": speaker_id}

    def bulk_enroll(
        self,
        speakers: List[dict],
    ) -> dict:
        """
        Bulk enroll speakers.

        Args:
            speakers: List of {"speaker_id": int, "audio_paths": List[str], "name": str, "tags": List[str]}

        Returns:
            {"total": int, "enrolled": int, "failed": int}
        """
        enrolled = 0
        failed = 0

        for speaker in speakers:
            result = self.enroll_from_audio(
                speaker_id=speaker["speaker_id"],
                audio_paths=speaker.get("audio_paths", []),
                name=speaker.get("name", ""),
                tags=speaker.get("tags"),
            )
            if result["status"] == "enrolled":
                enrolled += 1
            else:
                failed += 1

        return {"total": len(speakers), "enrolled": enrolled, "failed": failed}


# Singleton instance
_enroller: Optional[SpeakerEnroller] = None


def get_enroller() -> SpeakerEnroller:
    global _enroller
    if _enroller is None:
        _enroller = SpeakerEnroller()
    return _enroller

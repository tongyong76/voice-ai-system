from typing import Optional
from .asr_engine import get_asr_engine
from .speaker_engine import get_speaker_engine
from .emotion_engine import get_emotion_engine
from .nlu_engine import get_nlu_engine


class InferencePipeline:
    def __init__(self, speaker_db=None):
        self.asr = get_asr_engine()
        self.speaker = get_speaker_engine()
        self.emotion = get_emotion_engine()
        self.nlu = get_nlu_engine()
        self.speaker_db = speaker_db  # Reference to SpeakerDB instance

    def process(self, audio_path: str, hotwords: Optional[str] = None) -> dict:
        """
        Run full inference pipeline on audio file.

        Args:
            audio_path: Path to audio file
            hotwords: Optional hotwords for ASR

        Returns:
            {
                "asr": {"text": "...", "segments": [...]},
                "speaker": {"speaker_id": 123, "confidence": 0.92},
                "emotions": [{"label": "neutral", "confidence": 0.85, ...}],
                "nlu": {"keywords": [...], "intent": "...", "entities": {...}}
            }
        """
        result = {}

        # 1. ASR Transcription
        print("Running ASR...")
        result["asr"] = self.asr.transcribe(audio_path, hotwords=hotwords)

        # 2. Speaker Identification
        print("Running speaker identification...")
        if self.speaker_db:
            embedding = self.speaker.extract_embedding(audio_path)
            speaker_id, confidence = self.speaker_db.search(embedding)
            result["speaker"] = {
                "speaker_id": speaker_id,
                "confidence": confidence,
            }
        else:
            embedding = self.speaker.extract_embedding(audio_path)
            result["speaker"] = {
                "speaker_id": None,
                "confidence": 0.0,
                "embedding": embedding.tolist(),
            }

        # 3. Emotion Analysis
        print("Running emotion analysis...")
        result["emotions"] = self.emotion.analyze(audio_path)

        # 4. NLU Analysis
        print("Running NLU analysis...")
        if result["asr"]["text"]:
            result["nlu"] = self.nlu.analyze(result["asr"]["text"])
        else:
            result["nlu"] = {"keywords": [], "intent": "other", "entities": {}}

        return result


# Singleton instance
_pipeline: Optional[InferencePipeline] = None


def get_pipeline(speaker_db=None) -> InferencePipeline:
    global _pipeline
    if _pipeline is None:
        _pipeline = InferencePipeline(speaker_db=speaker_db)
    return _pipeline

import gc
import torch
from typing import Optional
from .asr_engine import get_asr_engine
from .speaker_engine import get_speaker_engine
from .emotion_engine import get_emotion_engine
from .nlu_engine import get_nlu_engine


class InferencePipeline:
    def __init__(self, speaker_db=None):
        self.speaker_db = speaker_db
        # 不预加载模型，按需加载以节省显存

    def process(self, audio_path: str, hotwords: Optional[str] = None) -> dict:
        """
        Run full inference pipeline on audio file.
        按需加载模型，用完释放显存，避免 OOM。
        """
        result = {}

        # 1. ASR Transcription (GPU)
        print("Running ASR...")
        asr = get_asr_engine()
        result["asr"] = asr.transcribe(audio_path, hotwords=hotwords)
        # 释放 ASR 模型显存
        del asr
        self._cleanup_gpu()

        # 2. Speaker Identification (CPU)
        print("Running speaker identification...")
        speaker = get_speaker_engine()
        if self.speaker_db:
            embedding = speaker.extract_embedding(audio_path)
            speaker_id, confidence = self.speaker_db.search(embedding)
            result["speaker"] = {
                "speaker_id": speaker_id,
                "confidence": confidence,
            }
        else:
            embedding = speaker.extract_embedding(audio_path)
            result["speaker"] = {
                "speaker_id": None,
                "confidence": 0.0,
                "embedding": embedding.tolist(),
            }
        del speaker
        self._cleanup_gpu()

        # 3. Emotion Analysis (GPU)
        print("Running emotion analysis...")
        emotion = get_emotion_engine()
        result["emotions"] = emotion.analyze(audio_path)
        del emotion
        self._cleanup_gpu()

        # 4. NLU Analysis (CPU, 仅文本处理)
        print("Running NLU analysis...")
        if result["asr"]["text"]:
            nlu = get_nlu_engine()
            result["nlu"] = nlu.analyze(result["asr"]["text"])
        else:
            result["nlu"] = {"keywords": [], "intent": "other", "entities": {}}

        return result

    @staticmethod
    def _cleanup_gpu():
        """释放 GPU 显存"""
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()


# Singleton instance — 注意：按需加载模式下不预加载模型
_pipeline: Optional[InferencePipeline] = None


def get_pipeline(speaker_db=None) -> InferencePipeline:
    global _pipeline
    if _pipeline is None:
        _pipeline = InferencePipeline(speaker_db=speaker_db)
    return _pipeline

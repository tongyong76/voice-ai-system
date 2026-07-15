from typing import Optional
from .asr_engine import get_asr_engine
from .speaker_engine import get_speaker_engine
from .nlu_engine import get_nlu_engine


class InferencePipeline:
    def __init__(self, speaker_db=None):
        self.speaker_db = speaker_db

    def process(self, audio_path: str, hotwords: Optional[str] = None) -> dict:
        """
        Run full inference pipeline on audio file.
        使用 SenseVoice (ASR+情感) + CAM++ (说话人) + NLU。
        """
        result = {}

        # 1. ASR + 情感分析 (SenseVoice, GPU 常驻)
        print("[Pipeline] Running ASR + Emotion (SenseVoice)...")
        asr = get_asr_engine()
        result["asr"] = asr.transcribe(audio_path, hotwords=hotwords)
        result["emotions"] = asr.analyze_emotion(audio_path)

        # 2. Speaker Identification (CAM++, GPU 常驻)
        print("[Pipeline] Running speaker identification...")
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

        # 3. NLU Analysis (纯 CPU 文本处理，常驻)
        print("[Pipeline] Running NLU analysis...")
        if result["asr"]["text"]:
            nlu = get_nlu_engine()
            result["nlu"] = nlu.analyze(result["asr"]["text"])
        else:
            result["nlu"] = {"keywords": [], "intent": "other", "entities": {}}

        print("[Pipeline] Inference complete")
        return result


# Singleton instance
_pipeline: Optional[InferencePipeline] = None


def get_pipeline(speaker_db=None) -> InferencePipeline:
    global _pipeline
    if _pipeline is None:
        _pipeline = InferencePipeline(speaker_db=speaker_db)
    return _pipeline

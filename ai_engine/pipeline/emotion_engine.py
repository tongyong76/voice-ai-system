import torch
import numpy as np
from typing import List, Optional
from funasr import AutoModel

# ModelScope 模型 ID（首次使用自动下载到 ~/.cache/modelscope/，之后走本地缓存）
DEFAULT_EMOTION_MODEL = "iic/emotion2vec_base_finetuned"


class EmotionEngine:
    def __init__(
        self,
        model_name: str = DEFAULT_EMOTION_MODEL,
        device: str = "cpu",
    ):
        self.device = device
        self.emotion_labels = [
            "happy", "sad", "angry", "fear", "surprise", "disgust", "neutral"
        ]
        print(f"[Emotion] Loading model: {model_name} on {self.device}")
        self.model = AutoModel(model=model_name, device=self.device)
        print(f"[Emotion] Model loaded successfully on {self.device}")

    def analyze(self, audio_path: str) -> List[dict]:
        """
        Analyze emotion from audio.

        Args:
            audio_path: Path to audio file

        Returns:
            List of emotion predictions:
            [{"label": "neutral", "confidence": 0.85, "start_ms": 0, "end_ms": 5000}]
        """
        result = self.model.generate(input=audio_path, granularity="utterance")

        emotions = []
        if result and len(result) > 0:
            for item in result:
                scores = item.get("scores", [])
                if scores:
                    # Get top emotion
                    max_idx = np.argmax(scores)
                    emotions.append({
                        "label": self.emotion_labels[max_idx] if max_idx < len(self.emotion_labels) else "unknown",
                        "confidence": float(scores[max_idx]),
                        "start_ms": item.get("start", 0),
                        "end_ms": item.get("end", 0),
                        "all_scores": {
                            self.emotion_labels[i]: float(s)
                            for i, s in enumerate(scores)
                            if i < len(self.emotion_labels)
                        },
                    })

        # Default if no emotion detected
        if not emotions:
            emotions.append({
                "label": "neutral",
                "confidence": 0.0,
                "start_ms": 0,
                "end_ms": 0,
                "all_scores": {},
            })

        return emotions


# ---- 单例：启动时加载一次，常驻显存 ----
_emotion_engine: Optional[EmotionEngine] = None


def get_emotion_engine() -> EmotionEngine:
    """获取情感引擎单例（首次调用时加载模型到 GPU，之后复用）"""
    global _emotion_engine
    if _emotion_engine is None:
        _emotion_engine = EmotionEngine()
    return _emotion_engine


def preload_emotion():
    """启动时预热情感模型"""
    print("[Emotion] Preloading model...")
    get_emotion_engine()
    print("[Emotion] Preload complete")

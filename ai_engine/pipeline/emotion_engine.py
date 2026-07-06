import torch
import numpy as np
from typing import Optional, List
from funasr import AutoModel


class EmotionEngine:
    def __init__(
        self,
        model_name: str = "iic/emotion2vec_base_finetuned",
    ):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.emotion_labels = [
            "happy", "sad", "angry", "fear", "surprise", "disgust", "neutral"
        ]
        print(f"Loading emotion model: {model_name} on {self.device}")
        self.model = AutoModel(model=model_name, device=self.device)
        print("Emotion model loaded successfully")

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


# Singleton instance
_emotion_engine: Optional[EmotionEngine] = None


def get_emotion_engine() -> EmotionEngine:
    global _emotion_engine
    if _emotion_engine is None:
        _emotion_engine = EmotionEngine()
    return _emotion_engine

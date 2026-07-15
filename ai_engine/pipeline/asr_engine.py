import re
import torch
from funasr import AutoModel
from typing import Optional, List

# SenseVoice 模型（集成 ASR + 情感检测 + 语言识别 + 音频事件检测）
DEFAULT_SENSEVOICE_MODEL = "iic/SenseVoiceSmall"

# 情感标签映射
EMOTION_MAP = {
    "HAPPY": "happy",
    "SAD": "sad",
    "ANGRY": "angry",
    "NEUTRAL": "neutral",
    "FEARFUL": "fear",
    "DISGUSTED": "disgust",
    "SURPRISED": "surprise",
}


class ASREngine:
    def __init__(
        self,
        model_name: str = DEFAULT_SENSEVOICE_MODEL,
        device: str = "cuda",  # GPU 常驻
    ):
        self.device = device
        print(f"[ASR] Loading SenseVoice model: {model_name} on {self.device}")
        self.model = AutoModel(
            model=model_name,
            vad_model="fsmn-vad",
            punc_model="ct-punc",
            device=self.device,
        )
        print(f"[ASR] SenseVoice loaded successfully on {self.device}")

    def transcribe(self, audio_path: str, hotwords: Optional[str] = None) -> dict:
        """
        Transcribe audio file to text using SenseVoice.
        SenseVoice 同时输出 ASR 文本和情感标签。

        Returns:
            {
                "text": "纯文本（去掉标签）",
                "language": "zh",
                "segments": [...]
            }
        """
        kwargs = {}
        if hotwords:
            kwargs["hotword"] = hotwords

        result = self.model.generate(input=audio_path, merge_vad=True, **kwargs)

        if not result:
            return {"text": "", "segments": [], "language": "unknown"}

        # Parse SenseVoice output
        full_text = ""
        detected_language = "unknown"
        segments = []

        for item in result:
            raw_text = item.get("text", "")

            # 提取语言标签 <|zh|> <|en|> <|ja|> <|yue|> <|ko|>
            lang_match = re.search(r"<\|(\w{2})\|>", raw_text)
            if lang_match:
                detected_language = lang_match.group(1)

            # 去掉所有 SenseVoice 标签，保留纯文本
            clean_text = re.sub(r"<\|[^|]+\|>", "", raw_text).strip()
            full_text += clean_text

            # 提取时间戳（如果有）
            if "timestamp" in item:
                timestamps = item["timestamp"]
                for ts in timestamps:
                    segments.append({
                        "start": ts[0] / 1000.0,
                        "end": ts[1] / 1000.0,
                        "text": clean_text[ts[2]:ts[3]] if len(ts) > 3 else "",
                        "confidence": item.get("confidence", 0.0),
                    })

        return {
            "text": full_text,
            "segments": segments,
            "language": detected_language,
        }

    def analyze_emotion(self, audio_path: str) -> List[dict]:
        """
        分析音频情感（基于 SenseVoice 内置情感检测）。
        SenseVoice 在 ASR 输出中嵌入情感标签，如 <|HAPPY|> <|NEUTRAL|>。

        Returns:
            [{"label": "neutral", "confidence": 0.85, "start_ms": 0, "end_ms": 0, "all_scores": {...}}]
        """
        result = self.model.generate(input=audio_path, merge_vad=True)

        if not result:
            return [{"label": "neutral", "confidence": 0.0, "start_ms": 0, "end_ms": 0, "all_scores": {}}]

        emotions = []
        for item in result:
            raw_text = item.get("text", "")

            # 提取情感标签
            emotion_match = re.search(r"<\|([A-Z]+)\|>", raw_text)
            if emotion_match:
                tag = emotion_match.group(1)
                # 跳过语言和音频事件标签
                if tag in EMOTION_MAP:
                    emotions.append({
                        "label": EMOTION_MAP[tag],
                        "confidence": 0.9,  # SenseVoice 不输出置信度，默认高置信
                        "start_ms": 0,
                        "end_ms": 0,
                        "all_scores": {EMOTION_MAP[tag]: 0.9},
                    })

        if not emotions:
            emotions.append({
                "label": "neutral",
                "confidence": 0.0,
                "start_ms": 0,
                "end_ms": 0,
                "all_scores": {},
            })

        return emotions


# ---- 单例：启动时加载一次，常驻 CPU ----
_asr_engine: Optional[ASREngine] = None


def get_asr_engine() -> ASREngine:
    """获取 ASR 引擎单例（首次调用时加载模型，之后复用）"""
    global _asr_engine
    if _asr_engine is None:
        _asr_engine = ASREngine()
    return _asr_engine


def preload_asr():
    """启动时预热 ASR 模型"""
    print("[ASR] Preloading SenseVoice model...")
    get_asr_engine()
    print("[ASR] Preload complete")

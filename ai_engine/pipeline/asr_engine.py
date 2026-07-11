import torch
from funasr import AutoModel
from typing import Optional


class ASREngine:
    def __init__(self, model_name: str = "iic/speech_paraformer-large-vad-punc_asr_nat-zh-cn-16k-common-vocab8404-pytorch"):
        # ASR 模型用 CPU（GPU 显存不足以同时加载模型和推理）
        self.device = "cpu"
        print(f"Loading ASR model: {model_name} on {self.device}")
        self.model = AutoModel(
            model=model_name,
            vad_model="iic/speech_fsmn_vad_zh-cn-16k-common-pytorch",
            punc_model="iic/punc_ct-transformer_cn-en-common-vocab471067-large",
            device=self.device,
        )
        print("ASR model loaded successfully")

    def transcribe(self, audio_path: str, hotwords: Optional[str] = None) -> dict:
        """
        Transcribe audio file to text.

        Args:
            audio_path: Path to audio file
            hotwords: Optional hotwords for better recognition

        Returns:
            {
                "text": "full transcript",
                "segments": [
                    {"start": 0.0, "end": 2.5, "text": "segment text", "confidence": 0.95}
                ]
            }
        """
        kwargs = {}
        if hotwords:
            kwargs["hotword"] = hotwords

        result = self.model.generate(input=audio_path, **kwargs)

        if not result:
            return {"text": "", "segments": []}

        # Parse result
        full_text = ""
        segments = []

        for item in result:
            text = item.get("text", "")
            full_text += text

            # Extract segments with timestamps if available
            if "timestamp" in item:
                timestamps = item["timestamp"]
                for ts in timestamps:
                    segments.append({
                        "start": ts[0] / 1000.0,
                        "end": ts[1] / 1000.0,
                        "text": text[ts[2]:ts[3]] if len(ts) > 3 else "",
                        "confidence": item.get("confidence", 0.0),
                    })

        return {
            "text": full_text,
            "segments": segments,
            "language": "zh",
        }


# 按需创建实例（不用单例，便于释放显存）
def get_asr_engine() -> ASREngine:
    return ASREngine()

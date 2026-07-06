import torch
import numpy as np
from typing import Optional, List, Tuple
from funasr import AutoModel


class SpeakerEngine:
    def __init__(
        self,
        model_name: str = "iic/speech_campplus_sv_zh-cn_16k-common",
        embedding_dim: int = 512,
    ):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.embedding_dim = embedding_dim
        print(f"Loading speaker model: {model_name} on {self.device}")
        self.model = AutoModel(model=model_name, device=self.device)
        print("Speaker model loaded successfully")

    def extract_embedding(self, audio_path: str) -> np.ndarray:
        """
        Extract speaker embedding from audio.

        Args:
            audio_path: Path to audio file

        Returns:
            Speaker embedding vector (512-dim)
        """
        result = self.model.generate(input=audio_path)
        if result and len(result) > 0:
            embedding = result[0].get("spk_embedding")
            if embedding is not None:
                if isinstance(embedding, torch.Tensor):
                    embedding = embedding.cpu().numpy()
                return embedding.flatten()
        return np.zeros(self.embedding_dim)

    def identify(
        self,
        audio_path: str,
        speaker_db_embeddings: np.ndarray,
        speaker_db_ids: List[int],
        threshold: float = 0.6,
    ) -> Tuple[Optional[int], float]:
        """
        Identify speaker from audio against speaker database.

        Args:
            audio_path: Path to audio file
            speaker_db_embeddings: NxD array of enrolled speaker embeddings
            speaker_db_ids: List of speaker IDs corresponding to embeddings
            threshold: Minimum similarity threshold

        Returns:
            (speaker_id, confidence) or (None, 0.0) if no match
        """
        embedding = self.extract_embedding(audio_path)
        if np.all(embedding == 0):
            return None, 0.0

        # Cosine similarity
        similarities = np.dot(speaker_db_embeddings, embedding) / (
            np.linalg.norm(speaker_db_embeddings, axis=1) * np.linalg.norm(embedding)
        )

        best_idx = np.argmax(similarities)
        best_score = similarities[best_idx]

        if best_score >= threshold:
            return speaker_db_ids[best_idx], float(best_score)
        return None, float(best_score)


# Singleton instance
_speaker_engine: Optional[SpeakerEngine] = None


def get_speaker_engine() -> SpeakerEngine:
    global _speaker_engine
    if _speaker_engine is None:
        _speaker_engine = SpeakerEngine()
    return _speaker_engine

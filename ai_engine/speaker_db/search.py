import os
import pickle
import numpy as np
import faiss
from typing import Optional, List, Tuple


class SpeakerDB:
    def __init__(
        self,
        index_path: str = "speaker_db/index",
        embedding_dim: int = 512,
        nlist: int = 1000,  # Number of clusters for IVF
    ):
        self.index_path = index_path
        self.embedding_dim = embedding_dim
        self.nlist = nlist

        self.index: Optional[faiss.IndexIVFFlat] = None
        self.speaker_ids: List[int] = []
        self.id_to_info: dict = {}  # speaker_id -> {name, tags, ...}

        os.makedirs(index_path, exist_ok=True)
        self._load_or_create_index()

    def _load_or_create_index(self):
        index_file = os.path.join(self.index_path, "faiss.index")
        ids_file = os.path.join(self.index_path, "speaker_ids.pkl")
        info_file = os.path.join(self.index_path, "speaker_info.pkl")

        if os.path.exists(index_file) and os.path.exists(ids_file):
            print("Loading existing speaker index...")
            self.index = faiss.read_index(index_file)
            with open(ids_file, "rb") as f:
                self.speaker_ids = pickle.load(f)
            if os.path.exists(info_file):
                with open(info_file, "rb") as f:
                    self.id_to_info = pickle.load(f)
            print(f"Loaded {len(self.speaker_ids)} speakers")
        else:
            print("Creating new speaker index...")
            # Create IVF index for 100K scale
            quantizer = faiss.IndexFlatIP(self.embedding_dim)  # Inner product (cosine after normalization)
            self.index = faiss.IndexIVFFlat(quantizer, self.embedding_dim, self.nlist, faiss.METRIC_INNER_PRODUCT)
            self.speaker_ids = []
            self.id_to_info = {}

    def _normalize(self, embeddings: np.ndarray) -> np.ndarray:
        """Normalize embeddings for cosine similarity"""
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1, norms)
        return embeddings / norms

    def train(self, embeddings: np.ndarray):
        """Train the FAISS index (required for IVF)"""
        if not self.index.is_trained:
            normalized = self._normalize(embeddings.astype(np.float32))
            self.index.train(normalized)
            print(f"Index trained with {len(embeddings)} vectors")

    def add(
        self,
        speaker_id: int,
        embedding: np.ndarray,
        name: str = "",
        tags: List[str] = None,
    ):
        """
        Add a speaker embedding to the database.

        Args:
            speaker_id: Unique speaker ID
            embedding: Speaker embedding vector (512-dim)
            name: Speaker name
            tags: Speaker tags
        """
        if embedding.ndim == 1:
            embedding = embedding.reshape(1, -1)

        normalized = self._normalize(embedding.astype(np.float32))

        # Train if needed and enough vectors
        if not self.index.is_trained and len(self.speaker_ids) >= self.nlist:
            self.train(np.array([e for e in normalized]))

        if self.index.is_trained:
            self.index.add(normalized)
        else:
            # Fallback: use flat index for small databases
            if not hasattr(self, '_flat_index'):
                self._flat_index = faiss.IndexFlatIP(self.embedding_dim)
            self._flat_index.add(normalized)

        self.speaker_ids.append(speaker_id)
        self.id_to_info[speaker_id] = {
            "name": name,
            "tags": tags or [],
        }

    def search(
        self,
        embedding: np.ndarray,
        threshold: float = 0.6,
        top_k: int = 1,
    ) -> Tuple[Optional[int], float]:
        """
        Search for the most similar speaker.

        Args:
            embedding: Query embedding (512-dim)
            threshold: Minimum similarity threshold
            top_k: Number of results to return

        Returns:
            (speaker_id, confidence) or (None, 0.0) if no match
        """
        if len(self.speaker_ids) == 0:
            return None, 0.0

        if embedding.ndim == 1:
            embedding = embedding.reshape(1, -1)

        normalized = self._normalize(embedding.astype(np.float32))

        # Search
        if self.index.is_trained and self.index.ntotal > 0:
            distances, indices = self.index.search(normalized, min(top_k, len(self.speaker_ids)))
        elif hasattr(self, '_flat_index') and self._flat_index.ntotal > 0:
            distances, indices = self._flat_index.search(normalized, min(top_k, len(self.speaker_ids)))
        else:
            return None, 0.0

        if len(indices[0]) > 0 and indices[0][0] >= 0:
            idx = indices[0][0]
            score = float(distances[0][0])
            if score >= threshold:
                speaker_id = self.speaker_ids[idx]
                return speaker_id, score

        return None, 0.0

    def save(self):
        """Save index to disk"""
        index_file = os.path.join(self.index_path, "faiss.index")
        ids_file = os.path.join(self.index_path, "speaker_ids.pkl")
        info_file = os.path.join(self.index_path, "speaker_info.pkl")

        if self.index.is_trained:
            faiss.write_index(self.index, index_file)
        with open(ids_file, "wb") as f:
            pickle.dump(self.speaker_ids, f)
        with open(info_file, "wb") as f:
            pickle.dump(self.id_to_info, f)
        print(f"Saved {len(self.speaker_ids)} speakers to disk")

    def get_info(self, speaker_id: int) -> Optional[dict]:
        """Get speaker info by ID"""
        return self.id_to_info.get(speaker_id)

    @property
    def size(self) -> int:
        return len(self.speaker_ids)


# Singleton instance
_speaker_db: Optional[SpeakerDB] = None


def get_speaker_db() -> SpeakerDB:
    global _speaker_db
    if _speaker_db is None:
        _speaker_db = SpeakerDB()
    return _speaker_db

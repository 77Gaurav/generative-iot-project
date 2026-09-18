from functools import lru_cache
from typing import List, Union

import logfire
from sentence_transformers import SentenceTransformer, util

from app.config import settings

EMBEDDING_MODEL = settings.EMBEDDING_MODEL


@lru_cache(maxsize=1)
def _get_model() -> SentenceTransformer:
    """Load the all-mpnet-base-v2 sentence transformer exactly once."""
    return SentenceTransformer(EMBEDDING_MODEL)


class EmbeddingService:
    """Wraps sentence-transformers all-mpnet-base-v2 for queries and batches."""

    @property
    def dimension(self) -> int:
        return _get_model().get_sentence_embedding_dimension()

    @staticmethod
    def _encode(texts: Union[str, List[str]]) -> List[List[float]]:
        inputs = [texts] if isinstance(texts, str) else texts
        vector = _get_model().encode(
            inputs,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        return vector.tolist()

    @logfire.instrument("embeddings.embed_query")
    def embed_query(self, text: str) -> List[float]:
        return self._encode(text)[0]

    @logfire.instrument("embeddings.embed_one")
    def embed_one(self, text: str) -> List[float]:
        return self._encode(text)[0]

    @logfire.instrument("embeddings.embed_batch")
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        return self._encode(texts)

    @staticmethod
    def similarity(a: List[float], b: List[float]) -> float:
        return float(util.cos_sim(a, b).item())


embedding_service = EmbeddingService()
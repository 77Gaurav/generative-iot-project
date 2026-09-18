import uuid
from typing import Any, Dict, List

import logfire
from langchain_core.documents import Document
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from app.config import settings
from app.services.retrieval.embedding import EmbeddingService


class QdrantService:
    """Initializes the Qdrant client and stores/retrieves component embeddings."""

    def __init__(self) -> None:
        self.embedding_service = EmbeddingService()
        self.client = QdrantClient(
            url=settings.QDRANT_URL,
            api_key=settings.QDRANT_API_KEY,
        )
        self.collection_name = settings.QDRANT_COLLECTION

    def ensure_collection(self) -> None:
        dimension = settings.EMBEDDING_DIM
        if not self.client.collection_exists(self.collection_name):
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=dimension,
                    distance=Distance.COSINE,
                ),
            )
            logfire.info(
                "Created Qdrant collection",
                collection=self.collection_name,
                dimension=dimension,
            )

    @staticmethod
    def _to_payload(chunk: Document) -> Dict[str, Any]:
        return {
            "component_id": chunk.metadata.get("component_id"),
            "component_name": chunk.metadata.get("component_name"),
            "type": chunk.metadata.get("type"),
            "text": chunk.page_content,
        }

    @logfire.instrument("qdrant.store_chunks")
    def store_chunks(self, chunks: List[Document]) -> None:
        self.ensure_collection()

        texts = [chunk.page_content for chunk in chunks]
        vectors = self.embedding_service.embed_batch(texts)

        points = []
        for idx, (chunk, vector) in enumerate(zip(chunks, vectors)):
            component_id = chunk.metadata.get("component_id")
            points.append(
                PointStruct(
                    id=str(uuid.uuid5(uuid.NAMESPACE_URL, f"iot://{component_id}:{idx}")),
                    vector=vector,
                    payload=self._to_payload(chunk),
                )
            )

        self.client.upsert(
            collection_name=self.collection_name,
            points=points,
        )
        logfire.info(
            "Upserted chunk embeddings",
            collection=self.collection_name,
            points=len(points),
        )

    @logfire.instrument("qdrant.search")
    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        query_vector = self.embedding_service.embed_query(query)
        result = self.client.query_points(
            collection_name=self.collection_name,
            query=query_vector,
            limit=top_k,
            with_payload=True,
        )
        return [
            {
                "score": scored_point.score,
                "payload": scored_point.payload,
            }
            for scored_point in result.points
        ]

    @logfire.instrument("qdrant.count")
    def count(self) -> int:
        return self.client.count(self.collection_name).count


qdrant_service = QdrantService()
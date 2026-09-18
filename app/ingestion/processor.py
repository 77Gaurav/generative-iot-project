# Configure logfire project as generative-iot-project
# CRITICAL: configure logfire before importing app modules that emit spans
import os

import logfire

from dotenv import load_dotenv

load_dotenv()
logfire.configure(
    service_name="generative-iot-project",
    token=os.getenv("LOGFIRE_TOKEN") or None,
    send_to_logfire="if-token-present",
)

from app.ingestion.chunking.splitter import splitter
from app.ingestion.loader.objects import objects_loader
from app.services.retrieval.qdrant_service import qdrant_service


class IngestionProcessor:
    """End-to-end pipeline: load components -> split into chunks -> embed -> store in Qdrant."""

    @logfire.instrument("ingestion.pipeline.run")
    def run(self) -> dict:
        documents = objects_loader.load()
        chunks = splitter.chunk_documents(documents)
        qdrant_service.store_chunks(chunks)
        return {
            "source_documents": len(documents),
            "chunks": len(chunks),
            "vectors_stored": qdrant_service.count(),
        }


processor = IngestionProcessor()


if __name__ == "__main__":
    result = processor.run()
    logfire.info("Ingestion pipeline finished", **result)
    print(result)
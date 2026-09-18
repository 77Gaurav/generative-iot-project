from typing import List

import logfire
from langchain_core.documents import Document


class Splitter:
    """
    Component ingestion path: 1 component JSON object = 1 Document = 1 chunk = 1 vector.

    RecursiveCharacterTextSplitter (chunk_size / chunk_overlap) is intentionally
    NOT used here so a component object is never broken into multiple vectors.
    This "chunker" is a one-to-one pass-through.
    """

    @logfire.instrument("objects.chunking.chunk_documents")
    def chunk_documents(self, documents: List[Document]) -> List[Document]:
        logfire.info(
            "Chunked component Documents",
            documents=len(documents),
            chunks=len(documents),
        )
        return documents


splitter = Splitter()
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Settings:

    # --- VECTOR DB (QDRANT) ---
    QDRANT_URL = os.getenv("QDRANT_CLUSTER_ENDPOINT")
    QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
    QDRANT_COLLECTION = "generative-iot-project"

    # --- REASONING ENGINE (GROQ) ---
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    GROQ_MODEL = "openai/gpt-oss-120b"

    # --- INGESTION ---
    COMPONENTS_PATH = os.getenv("COMPONENTS_PATH", "DATA/components.json")

    # --- EMBEDDINGS (sentence-transformers) ---
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-mpnet-base-v2")
    EMBEDDING_DIM = int(os.getenv("EMBEDDING_DIM", "768"))

    # --- CHUNKING ---
    CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "800"))
    CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "100"))

settings = Settings()


from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

COMPONENTS_MAP = BASE_DIR / "config" / "components_map.json"

RAW_CODE_DIR = BASE_DIR / "data" / "raw_sofa" / "source_code"
RAW_DOCS_DIR = BASE_DIR / "data" / "raw_sofa" / "official_docs"

INTERMEDIATE_DIR = BASE_DIR / "data" / "intermediate_json"
OUTPUT_DIR = BASE_DIR / "data" / "output_docs"

REQUEST_TIMEOUT = 30

# Scientific RAG configuration
ARTICLES_DIR = BASE_DIR / "data" / "articles"
VECTOR_DB_DIR = BASE_DIR / "data" / "vector_db"

GENERAL_COLLECTION = "general"

# Ollama embedding configuration
EMBEDDING_MODEL = "nomic-embed-text:latest"
EMBEDDING_BASE_URL = "http://localhost:11434"
EMBEDDING_ENDPOINT = "/api/embed"
EMBEDDING_TIMEOUT = 120
EMBEDDING_BATCH_SIZE = 16
EMBEDDING_TRUNCATE = False

# Embedding task prefixes
DOCUMENT_PREFIX = "search_document: "
QUERY_PREFIX = "search_query: "
SEMANTIC_PREFIX = "clustering: "

# Adaptive semantic chunking
MIN_CHUNK_TOKENS = 80
TARGET_CHUNK_TOKENS = 300
MAX_CHUNK_TOKENS = 450

SEMANTIC_SIMILARITY_THRESHOLD = 0.65

# Vector database configuration
VECTOR_DISTANCE_METRIC = "cosine"

# Retrieval configuration
GENERAL_TOP_K = 2
COMPONENT_TOP_K = 3

# RAG activation
RAG_ENABLED = True
RAG_SECTIONS = ("overview", "architecture", "mathematical_formulation")

for directory in [
    RAW_CODE_DIR,
    RAW_DOCS_DIR,
    INTERMEDIATE_DIR,
    OUTPUT_DIR,
]:
    directory.mkdir(parents=True, exist_ok=True)

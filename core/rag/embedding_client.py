
import requests
import numpy as np

from config.settings import (
    EMBEDDING_MODEL,
    EMBEDDING_BASE_URL,
    EMBEDDING_ENDPOINT,
    EMBEDDING_TIMEOUT,
    EMBEDDING_BATCH_SIZE,
    EMBEDDING_TRUNCATE,
)


def embed_texts(texts, prefix=""):
    """Generate local embeddings using Ollama."""

    if not texts:
        return np.array([])

    embeddings = []

    for start in range(0, len(texts), EMBEDDING_BATCH_SIZE):

        batch = texts[start:start + EMBEDDING_BATCH_SIZE]

        response = requests.post(
            EMBEDDING_BASE_URL + EMBEDDING_ENDPOINT,
            json={
                "model": EMBEDDING_MODEL,
                "input": [
                    prefix + text for text in batch
                ],
                "truncate": EMBEDDING_TRUNCATE,
            },
            timeout=EMBEDDING_TIMEOUT,
        )
        if not response.ok:
            print("\n[OLLAMA ERROR]")
            print("[STATUS]", response.status_code)
            print("[RESPONSE]", response.text)
            print("[BATCH START]", start)
            print("[BATCH SIZE]", len(batch))
            print("[TEXT LENGTHS]", [len(text) for text in batch])

            response.raise_for_status()

        vectors = response.json()["embeddings"]

        if len(vectors) != len(batch):
            raise ValueError("Embedding batch size mismatch")

        embeddings.extend(vectors)

    return np.asarray(embeddings, dtype=np.float32)


def cosine_similarity(vector_a, vector_b):
    """Calculate cosine similarity between two vectors."""

    denominator = (
        np.linalg.norm(vector_a)
        * np.linalg.norm(vector_b)
    )

    if denominator == 0:
        return 0.0

    return float(
        np.dot(vector_a, vector_b) / denominator
    )

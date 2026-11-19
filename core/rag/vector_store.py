
import json

import chromadb

from functools import lru_cache
from pathlib import Path
from collections import defaultdict

from config.settings import (
    VECTOR_DB_DIR,
    VECTOR_DISTANCE_METRIC,
    EMBEDDING_MODEL,
    DOCUMENT_PREFIX,
    QUERY_PREFIX,
    EMBEDDING_BATCH_SIZE,
)

from core.rag.embedding_client import embed_texts

from core.rag.article_processor import process_articles
from core.rag.chunker import chunk_documents


@lru_cache(maxsize=1)
def get_vector_client():
    """Initialize the persistent vector database."""

    Path(VECTOR_DB_DIR).mkdir(
        parents=True,
        exist_ok=True,
    )

    return chromadb.PersistentClient(
        path=str(VECTOR_DB_DIR)
    )


def get_collection(name):
    """Create or retrieve a collection."""

    client = get_vector_client()

    return client.get_or_create_collection(
        name=name,
        embedding_function=None,
        configuration={
            "hnsw": {
                "space": VECTOR_DISTANCE_METRIC,
            }
        },
    )


def build_metadata(chunk):
    """Prepare chunk metadata for ChromaDB."""

    return {
        "document": chunk["document"],
        "source_path": chunk["source_path"],
        "document_sha256": chunk["document_sha256"],

        "scope": chunk["scope"],
        "collection": chunk["collection"],
        "source_type": chunk["source_type"],

        "page_start": chunk["page_start"],
        "page_end": chunk["page_end"],

        "chunk_index": chunk["chunk_index"],
        "estimated_tokens": chunk["estimated_tokens"],

        "block_ids": json.dumps(chunk["block_ids"]),

        "embedding_model": EMBEDDING_MODEL,
    }


def index_chunks(chunks):
    """Index chunks and reuse identical embeddings."""

    if not chunks:
        return {}

    grouped_chunks = defaultdict(dict)
    embedding_cache = {}

    for chunk in chunks:

        grouped_chunks[chunk["collection"]][
            chunk["chunk_id"]
        ] = chunk

    statistics = {}

    for collection_name, chunk_map in grouped_chunks.items():

        collection = get_collection(collection_name)
        items = list(chunk_map.values())

        print("\n[COLLECTION]", collection_name)
        print("[CHUNKS]", len(items))

        existing = collection.get(
            include=["metadatas"]
        )

        existing_ids = set(existing["ids"])

        for start in range(
            0, len(items), EMBEDDING_BATCH_SIZE
        ):

            batch = items[
                start:start + EMBEDDING_BATCH_SIZE
            ]

            missing = {
                chunk["chunk_id"]: chunk
                for chunk in batch
                if chunk["chunk_id"] not in embedding_cache
            }

            if missing:

                missing_chunks = list(missing.values())

                vectors = embed_texts(
                    [
                        chunk["text"]
                        for chunk in missing_chunks
                    ],
                    prefix=DOCUMENT_PREFIX,
                )

                for chunk, vector in zip(
                    missing_chunks, vectors
                ):

                    embedding_cache[
                        chunk["chunk_id"]
                    ] = vector.tolist()

            collection.upsert(
                ids=[
                    chunk["chunk_id"]
                    for chunk in batch
                ],
                documents=[
                    chunk["text"]
                    for chunk in batch
                ],
                embeddings=[
                    embedding_cache[chunk["chunk_id"]]
                    for chunk in batch
                ],
                metadatas=[
                    build_metadata(chunk)
                    for chunk in batch
                ],
            )

        current_ids = set(chunk_map.keys())

        obsolete_ids = existing_ids - current_ids

        if obsolete_ids:
            collection.delete(
                ids=list(obsolete_ids)
            )

        statistics[collection_name] = collection.count()

        print("[INDEXED]", statistics[collection_name])
        print("[REMOVED OBSOLETE]", len(obsolete_ids))

    print("\n[UNIQUE EMBEDDINGS]", len(embedding_cache))

    return statistics


def index_articles():
    """Process, chunk and index the complete PDF corpus."""

    print("[PROCESSING ARTICLES]")

    documents = process_articles()

    print("[DOCUMENTS]", len(documents))
    print("[BUILDING SEMANTIC CHUNKS]")

    chunks = chunk_documents(documents)

    print("[TOTAL CHUNKS]", len(chunks))
    print("[INDEXING CHUNKS]")

    return index_chunks(chunks)


def search_collection(collection_name, query, top_k=5):
    """Search a single collection using cosine distance."""

    collection = get_vector_client().get_collection(
        name=collection_name,
        embedding_function=None,
    )

    count = collection.count()

    if count == 0 or top_k <= 0:
        return []

    query_embedding = embed_texts(
        [query],
        prefix=QUERY_PREFIX,
    )[0].tolist()

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=min(top_k, count),
        include=[
            "documents",
            "metadatas",
            "distances",
        ],
    )

    retrieved = []

    for chunk_id, text, metadata, distance in zip(
        results["ids"][0],
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):

        metadata = dict(metadata)

        metadata["block_ids"] = json.loads(
            metadata["block_ids"]
        )

        retrieved.append({
            **metadata,
            "chunk_id": chunk_id,
            "text": text,
            "similarity": 1.0 - float(distance),
        })

    return retrieved


def get_index_statistics():
    """Return the number of chunks in each collection."""

    client = get_vector_client()

    return {
        collection.name: collection.count()
        for collection in client.list_collections()
    }

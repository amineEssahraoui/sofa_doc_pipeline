
from config.settings import (
    GENERAL_COLLECTION,
    GENERAL_TOP_K,
    COMPONENT_TOP_K,
)

from core.rag.vector_store import search_collection


def retrieve_chunks(collection_name, queries, top_k=5):
    """Retrieve, deduplicate and rank chunks from a collection."""

    if isinstance(queries, str):
        queries = [queries]

    if not queries or top_k <= 0:
        return []

    retrieved = {}

    for query in queries:

        if not query.strip():
            continue

        results = search_collection(
            collection_name=collection_name,
            query=query,
            top_k=top_k,
        )

        for result in results:

            chunk_id = result["chunk_id"]

            if chunk_id not in retrieved:

                retrieved[chunk_id] = {
                    **result,
                    "matched_queries": [query],
                }

            else:

                existing = retrieved[chunk_id]

                if query not in existing["matched_queries"]:
                    existing["matched_queries"].append(query)

                existing["similarity"] = max(
                    existing["similarity"],
                    result["similarity"],
                )

    ranked_chunks = sorted(
        retrieved.values(),
        key=lambda chunk: chunk["similarity"],
        reverse=True,
    )

    return ranked_chunks[:top_k]


def retrieve_context(
    component,
    general_queries=None,
    component_queries=None,
    general_top_k=GENERAL_TOP_K,
    component_top_k=COMPONENT_TOP_K,
):
    """Retrieve independent general and component-specific context."""

    general_chunks = retrieve_chunks(
        collection_name=GENERAL_COLLECTION,
        queries=general_queries,
        top_k=general_top_k,
    )

    component_chunks = retrieve_chunks(
        collection_name=component,
        queries=component_queries,
        top_k=component_top_k,
    )

    return {
        "component": component,
        "general": general_chunks,
        "component_specific": component_chunks,
    }

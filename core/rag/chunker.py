
import re
import hashlib
import unicodedata

from config.settings import (
    MIN_CHUNK_TOKENS,
    TARGET_CHUNK_TOKENS,
    MAX_CHUNK_TOKENS,
    SEMANTIC_SIMILARITY_THRESHOLD,
    SEMANTIC_PREFIX,
)

from core.rag.embedding_client import (
    embed_texts,
    cosine_similarity,
)


def clean_block(text):
    """Apply minimal text normalization."""

    text = unicodedata.normalize("NFC", text)

    text = text.replace("\u00ad", "")

    text = re.sub(
        r"(?<=\w)-\n(?=[a-z])",
        "",
        text,
    )

    text = re.sub(r"\s+", " ", text).strip()

    if not text:
        return ""

    if re.fullmatch(r"\d+(\s*/\s*\d+)?", text):
        return ""

    if re.fullmatch(r"[\W_]+", text):
        return ""

    return text


def estimate_tokens(text):
    """Estimate token count without loading a tokenizer."""

    return max(
        len(text.split()),
        (len(text) + 3) // 4,
    )


def split_long_text(text, max_tokens):
    """Split oversized blocks while preserving words."""

    units = []
    current = []

    for word in text.split():

        candidate = " ".join(current + [word])

        if current and estimate_tokens(candidate) > max_tokens:

            units.append(" ".join(current))
            current = []

        current.append(word)

    if current:
        units.append(" ".join(current))

    return units


def prepare_units(blocks):
    """Group small adjacent blocks before semantic analysis."""

    units = []
    current = []

    unit_target = MIN_CHUNK_TOKENS

    def flush():

        if not current:
            return

        units.append({
            "text": "\n".join(
                item["text"] for item in current
            ),
            "page_start": current[0]["page"],
            "page_end": current[-1]["page"],
            "block_ids": list(dict.fromkeys(
                item["block_id"] for item in current
            )),
        })

        current.clear()

    for block in blocks:

        text = clean_block(block["text"])

        if not text:
            continue

        parts = split_long_text(
            text,
            TARGET_CHUNK_TOKENS,
        )

        for part in parts:

            candidate = "\n".join(
                [item["text"] for item in current]
                + [part]
            )

            if current and (
                estimate_tokens(candidate)
                > TARGET_CHUNK_TOKENS
            ):
                flush()

            current.append({
                "text": part,
                "page": block["page"],
                "block_id": block["block_id"],
            })

            current_text = "\n".join(
                item["text"] for item in current
            )

            if estimate_tokens(current_text) >= unit_target:
                flush()

    flush()

    return units


def build_chunk(document, units, chunk_index):
    """Build a traceable scientific chunk."""

    text = "\n\n".join(
        unit["text"] for unit in units
    )

    identifier = (
        document["document_sha256"]
        + ":"
        + str(chunk_index)
        + ":"
        + text
    )

    chunk_id = hashlib.sha256(
        identifier.encode("utf-8")
    ).hexdigest()

    return {
        "chunk_id": chunk_id,
        "chunk_index": chunk_index,

        "document": document["document"],
        "source_path": document["source_path"],
        "document_sha256": document["document_sha256"],

        "scope": document["scope"],
        "collection": document["collection"],
        "source_type": "scientific_reference",

        "page_start": units[0]["page_start"],
        "page_end": units[-1]["page_end"],

        "block_ids": list(dict.fromkeys(
            block_id
            for unit in units
            for block_id in unit["block_ids"]
        )),

        "estimated_tokens": estimate_tokens(text),
        "text": text,
    }


def chunk_document(document):
    """Build adaptive chunks using semantic similarity."""

    units = prepare_units(document["blocks"])

    if not units:
        return []

    embeddings = embed_texts(
        [unit["text"] for unit in units],
        prefix=SEMANTIC_PREFIX,
    )

    chunks = []
    current = [units[0]]

    for index in range(1, len(units)):

        unit = units[index]

        similarity = cosine_similarity(
            embeddings[index - 1],
            embeddings[index],
        )

        current_text = "\n\n".join(
            item["text"] for item in current
        )

        candidate = current_text + "\n\n" + unit["text"]

        exceeds_limit = (
            estimate_tokens(candidate)
            > MAX_CHUNK_TOKENS
        )

        semantic_boundary = (
            similarity < SEMANTIC_SIMILARITY_THRESHOLD
            and estimate_tokens(current_text)
            >= MIN_CHUNK_TOKENS
        )

        if exceeds_limit or semantic_boundary:

            chunks.append(
                build_chunk(
                    document,
                    current,
                    len(chunks),
                )
            )

            current = [unit]

        else:
            current.append(unit)

    if current:

        chunks.append(
            build_chunk(
                document,
                current,
                len(chunks),
            )
        )

    return chunks


def chunk_documents(documents):
    """Chunk all documents and reuse identical PDF results."""

    all_chunks = []
    cache = {}

    for document in documents:

        document_hash = document["document_sha256"]

        if document_hash not in cache:

            cache[document_hash] = chunk_document(
                document
            )

        for chunk in cache[document_hash]:

            all_chunks.append({
                **chunk,
                "document": document["document"],
                "source_path": document["source_path"],
                "scope": document["scope"],
                "collection": document["collection"],
            })

    return all_chunks


import hashlib
from pathlib import Path

import pymupdf

from config.settings import ARTICLES_DIR, GENERAL_COLLECTION


def discover_articles():
    """Discover general and component-specific PDF documents."""

    root = Path(ARTICLES_DIR)
    articles = []

    for path in sorted(root.rglob("*")):

        if not path.is_file() or path.suffix.lower() != ".pdf":
            continue

        relative_path = path.relative_to(root)

        is_general = len(relative_path.parts) == 1

        articles.append({
            "document": path.name,
            "source_path": str(path),
            "scope": "general" if is_general else "component",
            "collection": (
                GENERAL_COLLECTION
                if is_general
                else relative_path.parts[0]
            ),
            "document_sha256": hashlib.sha256(
                path.read_bytes()
            ).hexdigest(),
        })

    return articles


def extract_text_blocks(path):
    """Extract text blocks with their original page numbers."""

    blocks = []

    with pymupdf.open(path) as document:

        for page_number, page in enumerate(document, start=1):

            for block in page.get_text("blocks", sort=True):

                text = block[4].strip()
                block_type = block[6]

                if block_type != 0 or not text:
                    continue

                blocks.append({
                    "block_id": len(blocks),
                    "page": page_number,
                    "text": text,
                })

    return blocks


def process_article(article):
    """Extract text blocks from a single PDF."""

    return {
        **article,
        "blocks": extract_text_blocks(article["source_path"]),
    }


def process_articles():
    """Process all available PDF documents."""

    return [
        process_article(article)
        for article in discover_articles()
    ]

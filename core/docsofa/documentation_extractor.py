
import json
import hashlib
from pathlib import Path

from bs4 import BeautifulSoup

from config.settings import INTERMEDIATE_DIR


OFFICIAL_DOCS_DIR = Path("data/raw_sofa/official_docs")


def extract_documentation_introduction(component):
    """Extract content between h1 and the first h2."""

    links_path = (
        Path(INTERMEDIATE_DIR)
        / component
        / "method_links.json"
    )

    links_data = json.loads(
        links_path.read_text(encoding="utf-8")
    )

    commit = links_data["resolved_commit"]

    html_path = (
        OFFICIAL_DOCS_DIR
        / component
        / commit
        / "official_doc.html"
    )

    soup = BeautifulSoup(
        html_path.read_bytes(),
        "html.parser"
    )

    article = soup.find("article")
    if article is None:
        raise ValueError("Documentation article not found")

    h1 = article.find("h1")
    if h1 is None:
        raise ValueError("Documentation h1 not found")

    content = []

    for element in h1.next_siblings:
        if getattr(element, "name", None) == "h2":
            break

        if getattr(element, "name", None) is None:
            continue

        if element.name == "p":
            text = element.get_text(" ", strip=True)
            if text:
                content.append({
                    "type": "paragraph",
                    "text": text
                })

        elif (
            element.name == "div"
            and "arithmatex" in element.get("class", [])
        ):
            formula = element.get_text("", strip=True)

            if formula:
                content.append({
                    "type": "equation",
                    "latex": formula
                })

        elif element.name in {"ul", "ol"}:
            content.append({
                "type": "list",
                "items": [
                    li.get_text(" ", strip=True)
                    for li in element.find_all(
                        "li", recursive=False
                    )
                ]
            })

    return content



def extract_documentation_tables(component):
    """Extract SOFA Data and Links tables with their section context."""

    links_path = (
        Path(INTERMEDIATE_DIR)
        / component
        / "method_links.json"
    )

    links_data = json.loads(
        links_path.read_text(encoding="utf-8")
    )

    commit = links_data["resolved_commit"]

    html_path = (
        OFFICIAL_DOCS_DIR
        / component
        / commit
        / "official_doc.html"
    )

    if not html_path.is_file():
        raise FileNotFoundError(html_path)

    soup = BeautifulSoup(
        html_path.read_text(encoding="utf-8"),
        "html.parser"
    )

    article = soup.find("article")

    if article is None:
        raise ValueError("Documentation article not found")

    current_section = None
    current_category = None
    tables = []

    # Process headings and tables in document order.
    for element in article.find_all(
        ["h1", "h2", "h3", "table"]
    ):
        if element.name == "h2":
            current_section = element.get_text(" ", strip=True)
            current_category = None

        elif element.name == "h3":
            current_category = element.get_text(" ", strip=True)

        elif element.name == "table":
            rows = []

            for tr in element.find_all("tr"):
                cells = tr.find_all(["th", "td"])

                values = [
                    cell.get_text(" ", strip=True)
                    for cell in cells
                ]

                if values:
                    rows.append(values)

            if not rows:
                continue

            headers = rows[0]
            records = []

            for values in rows[1:]:
                record = {
                    header: value
                    for header, value in zip(headers, values)
                }

                if record:
                    records.append(record)

            tables.append({
                "section": current_section,
                "category": current_category,
                "headers": headers,
                "records": records,
            })

    result = {
        "component": component,
        "resolved_commit": commit,
        "source_file": str(html_path),
        "page_title": (
            soup.title.get_text(" ", strip=True)
            if soup.title else None
        ),
        "tables": tables,
    }

    return result


def extract_documentation_sections(component):
    """Extract textual documentation sections without rewriting their content."""

    links_path = (
        Path(INTERMEDIATE_DIR)
        / component
        / "method_links.json"
    )

    links_data = json.loads(
        links_path.read_text(encoding="utf-8")
    )

    commit = links_data["resolved_commit"]

    html_path = (
        OFFICIAL_DOCS_DIR
        / component
        / commit
        / "official_doc.html"
    )

    if not html_path.is_file():
        raise FileNotFoundError(html_path)

    soup = BeautifulSoup(
        html_path.read_bytes(),
        "html.parser"
    )

    article = soup.find("article")

    if article is None:
        raise ValueError("Documentation article not found")

    sections = []

    for heading in article.find_all("h2"):
        section = {
            "title": heading.get_text(" ", strip=True),
            "content": []
        }

        for element in heading.next_siblings:
            if getattr(element, "name", None) == "h2":
                break

            if getattr(element, "name", None) is None:
                continue

            if (
                element.name == "div"
                and "arithmatex" in element.get("class", [])
            ):
                latex = element.get_text("", strip=True)

                if latex:
                    section["content"].append({
                        "type": "equation",
                        "latex": latex
                    })

                continue

            for node in (
                [element]
                if element.name in {"p", "pre", "ul", "ol", "img"}
                else element.find_all(["p", "pre", "ul", "ol", "img"])
                if element.name not in {"table", "h3"}
                else []
            ):
                if node.name == "p":
                    text = node.get_text(" ", strip=True)
                    if text:
                        section["content"].append({
                            "type": "paragraph",
                            "text": text
                        })
                    for img in node.find_all("img"):
                        section["content"].append({
                            "type": "image_reference",
                            "src": img.get("src"),
                            "alt": img.get("alt", ""),
                            "title": img.get("title", "")
                        })

                elif node.name == "pre":
                    section["content"].append({
                        "type": "code",
                        "text": node.get_text("", strip=False).strip("\n")
                    })

                elif node.name in {"ul", "ol"}:
                    items = [
                        li.get_text(" ", strip=True)
                        for li in node.find_all("li", recursive=False)
                    ]

                    section["content"].append({
                        "type": "list",
                        "items": items
                    })

                elif node.name == "img":
                    section["content"].append({
                        "type": "image",
                        "src": node.get("src"),
                        "alt": node.get("alt", "")
                    })

        sections.append(section)

    return {
        "component": component,
        "resolved_commit": commit,
        "source_file": str(html_path),
        "sections": sections
    }


def build_official_documentation(component):
    """
    Build official documentation JSON from existing SOFA HTML.

    Keeps tables and textual sections separate.
    No LLM calls and no source downloads.
    """

    tables_data = extract_documentation_tables(component)
    sections_data = extract_documentation_sections(component)

    # Ensure both extractions refer to the same component/version.
    if tables_data["component"] != sections_data["component"]:
        raise ValueError("Component mismatch")

    if tables_data["resolved_commit"] != sections_data["resolved_commit"]:
        raise ValueError("Documentation commit mismatch")

    if tables_data["source_file"] != sections_data["source_file"]:
        raise ValueError("Documentation source mismatch")

    introduction = extract_documentation_introduction(component)


    html_path = Path(tables_data["source_file"])
    html_bytes = html_path.read_bytes()

    soup = BeautifulSoup(html_bytes, "html.parser")

    canonical = soup.find(
        "link", rel="canonical"
    )

    canonical_url = (
        canonical.get("href")
        if canonical else None
    )

    html_sha256 = hashlib.sha256(
        html_bytes
    ).hexdigest()

    result = {
        "component": component,
        "resolved_commit": tables_data["resolved_commit"],
        "source_file": tables_data["source_file"],
        "page_title": tables_data["page_title"],
        "sections": sections_data["sections"],
        "tables": tables_data["tables"],
        "statistics": {
            "sections": len(sections_data["sections"]),
            "tables": len(tables_data["tables"]),
        },
        "introduction": introduction,
        "canonical_url": canonical_url,
        "html_sha256": html_sha256,
    }

    folder = Path(INTERMEDIATE_DIR) / component
    folder.mkdir(parents=True, exist_ok=True)

    output_path = folder / "official_documentation.json"

    output_path.write_text(
        json.dumps(result, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    print(f"[DOC] {component}")
    print(f"[SECTIONS] {len(result['sections'])}")
    print(f"[TABLES] {len(result['tables'])}")
    print(f"[SAVED] {output_path}")

    return result

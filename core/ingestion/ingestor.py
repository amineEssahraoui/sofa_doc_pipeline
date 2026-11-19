
import os
from pathlib import Path
import hashlib
import json
from datetime import datetime, timezone
from urllib.parse import urlparse, quote

import requests

from config.settings import (
    COMPONENTS_MAP,
    RAW_CODE_DIR,
    REQUEST_TIMEOUT,
    RAW_DOCS_DIR,
    INTERMEDIATE_DIR,
)


class SofaIngestor:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "SOFA-Documentation-MVP",
            "Accept": "application/vnd.github+json",
        })

    @staticmethod
    def cache_path(path):
        """
        Support Windows long paths without changing
        the physical shared-cache structure.
        """
        path = Path(path).resolve()

        if os.name != "nt":
            return path

        value = str(path)

        if value.startswith("\\\\?\\"):
            return path

        if len(value) < 240:
            return path

        if value.startswith("\\\\"):
            return Path("\\\\?\\UNC\\" + value[2:])

        return Path("\\\\?\\" + value)

    def load_components(self):
        with open(COMPONENTS_MAP, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data["components"]

    def parse_github_url(self, url):
        """Extract owner, repository, Git ref and file path."""
        parsed = urlparse(url)

        if parsed.netloc != "github.com":
            raise ValueError(f"Not a GitHub URL: {url}")

        parts = parsed.path.strip("/").split("/")

        if len(parts) < 5 or parts[2] != "blob":
            raise ValueError(f"Invalid GitHub file URL: {url}")

        owner, repo, _, ref = parts[:4]
        file_path = "/".join(parts[4:])

        if not owner or not repo or not file_path:
            raise ValueError(f"Incomplete GitHub URL: {url}")

        return owner, repo, ref, file_path

    def resolve_commit(self, owner, repo, ref):
        """Resolve a Git ref to an immutable commit SHA."""
        api_url = (
            f"https://api.github.com/repos/"
            f"{owner}/{repo}/commits/{quote(ref, safe='')}"
        )

        response = self.session.get(
            api_url, timeout=REQUEST_TIMEOUT
        )
        response.raise_for_status()

        return response.json()["sha"]

    def download_source(self, owner, repo, sha, file_path):
        """Download a source file from the pinned commit."""
        encoded_path = quote(file_path, safe="/")

        raw_url = (
            f"https://raw.githubusercontent.com/"
            f"{owner}/{repo}/{sha}/{encoded_path}"
        )

        response = self.session.get(
            raw_url, timeout=REQUEST_TIMEOUT
        )
        response.raise_for_status()

        return response.content

    
    def download_documentation(self, component, sha):
        """Download and preserve the official SOFA HTML documentation."""

        name = component["name"]
        url = component.get("documentation_url")

        if not url:
            print(f"[DOC] No documentation URL for {name}")
            return None

        print(f"[DOC] Downloading documentation for {name}")

        response = self.session.get(
            url,
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()

        content_type = response.headers.get(
            "Content-Type", ""
        )

        if "text/html" not in content_type.lower():
            raise ValueError(
                f"Unexpected documentation format: {content_type}"
            )

        content = response.content

        doc_dir = RAW_DOCS_DIR / name / sha
        doc_dir.mkdir(parents=True, exist_ok=True)

        destination = doc_dir / "official_doc.html"
        destination.write_bytes(content)

        print(f"[DOC] Saved: {destination}")

        return {
            "url": response.url,
            "local_path": str(destination),
            "sha256": hashlib.sha256(content).hexdigest(),
            "retrieved_at": datetime.now(
                timezone.utc
            ).isoformat(),
            "version": "unknown",
        }


    def ingest_component(self, component):
        name = component["name"]
        print(f"\n[INGESTOR] Component: {name}")

        source_urls = component["source_urls"]
        if not source_urls:
            raise ValueError(f"No source URLs for {name}")

        parsed_files = [
            self.parse_github_url(url)
            for url in source_urls
        ]

        owner, repo, ref, _ = parsed_files[0]

        # All source files must refer to the same repository and ref.
        for file_owner, file_repo, file_ref, _ in parsed_files:
            if (file_owner, file_repo, file_ref) != (
                owner, repo, ref
            ):
                raise ValueError(
                    f"Inconsistent Git sources for {name}"
                )

        sha = self.resolve_commit(owner, repo, ref)
        print(f"[GIT] {ref} -> {sha}")

        component_dir = RAW_CODE_DIR / name / sha
        component_dir.mkdir(parents=True, exist_ok=True)

        manifest = {
            "component": name,
            "repository": f"{owner}/{repo}",
            "requested_ref": ref,
            "resolved_commit": sha,
            "retrieved_at": datetime.now(
                timezone.utc
            ).isoformat(),
            "files": [],
        }

        for _, _, _, file_path in parsed_files:
            print(f"[DOWNLOAD] {file_path}")

            content = self.download_source(
                owner, repo, sha, file_path
            )

            destination = component_dir / file_path
            destination.parent.mkdir(
                parents=True, exist_ok=True
            )
            destination.write_bytes(content)

            manifest["files"].append({
                "repository_path": file_path,
                "local_path": str(
                    destination.relative_to(component_dir)
                ),
                "sha256": hashlib.sha256(content).hexdigest(),
                "size_bytes": len(content),
            })

        manifest["documentation"] = self.download_documentation(
            component, sha
        )

        manifest_path = component_dir / "manifest.json"
        manifest_path.write_text(
            json.dumps(manifest, indent=2),
            encoding="utf-8",
        )

        print(f"[SUCCESS] {len(manifest['files'])} files saved")
        return manifest

    
    def get_repository_files(self, owner, repo, sha):
        """List repository files at one exact Git commit."""
        url = (
            f"https://api.github.com/repos/{owner}/{repo}"
            f"/git/trees/{sha}"
        )

        response = self.session.get(
            url,
            params={"recursive": 1},
            timeout=REQUEST_TIMEOUT
        )
        response.raise_for_status()
        data = response.json()

        if data.get("truncated"):
            raise RuntimeError(
                "GitHub returned an incomplete repository tree."
            )

        return [
            item["path"]
            for item in data["tree"]
            if item["type"] == "blob"
        ]

    def find_parent_header(self, include_path, repo_files):
        """Find the actual repository path of an included header."""
        # Prefer an exact suffix match.
        matches = [
            path for path in repo_files
            if path == include_path
            or path.endswith("/" + include_path)
        ]

        # Fallback: unique filename match.
        if not matches:
            filename = include_path.rsplit("/", 1)[-1]
            matches = [
                path for path in repo_files
                if path.rsplit("/", 1)[-1] == filename
            ]

        if len(matches) == 1:
            return matches[0], "resolved"

        if len(matches) > 1:
            return None, "ambiguous"

        return None, "unresolved"

    def download_parent_headers(self, component_name):
        """Resolve and download direct parent headers with a shared cache."""
        component_root = RAW_CODE_DIR / component_name

        manifests = list(component_root.glob("*/manifest.json"))
        if not manifests:
            raise FileNotFoundError("Component manifest not found.")

        manifest_path = max(
            manifests,
            key=lambda path: path.stat().st_mtime
        )

        manifest = json.loads(
            manifest_path.read_text(encoding="utf-8")
        )

        sha = manifest["resolved_commit"]
        owner, repo = manifest["repository"].split("/")

        dependencies_path = (
            INTERMEDIATE_DIR / component_name / "includes.json"
        )

        dependencies = json.loads(
            dependencies_path.read_text(encoding="utf-8")
        )

        if dependencies["resolved_commit"] != sha:
            raise ValueError(
                "Extractor and Ingestor commits do not match. "
                "Run the Extractor again on the current sources."
            )

        print("\n[REPOSITORY] Loading GitHub file index")
        repo_files = self.get_repository_files(owner, repo, sha)

        results = []

        for parent in dependencies["parent_dependencies"]:
            name = parent["parent_name"]
            include_path = parent["header_path"]

            if parent["status"] != "resolved" or not include_path:
                print(f"[SKIP] {name}: unresolved include")
                results.append({
                    "parent": name,
                    "status": "unresolved_include"
                })
                continue

            repository_path, status = self.find_parent_header(
                include_path, repo_files
            )

            if status != "resolved":
                print(f"[{status.upper()}] {name}")
                results.append({
                    "parent": name,
                    "status": status
                })
                continue

            # Shared cache: repository + SHA + real file path.
            cache_root = (
                RAW_CODE_DIR / "_shared_cache" / owner / repo / sha
            )

            destination = self.cache_path(cache_root / repository_path)
            destination.parent.mkdir(parents=True, exist_ok=True)

            hash_path = self.cache_path(
                destination.with_name(destination.name + ".sha256")
            )

            cache_valid = False

            if destination.is_file() and hash_path.is_file():
                existing_hash = hashlib.sha256(
                    destination.read_bytes()
                ).hexdigest()

                expected_hash = hash_path.read_text(
                    encoding="utf-8"
                ).strip()

                cache_valid = existing_hash == expected_hash

            if cache_valid:
                print(f"[CACHE HIT] {name}")
                content = destination.read_bytes()
            else:
                print(f"[DOWNLOAD] {name}: {repository_path}")

                content = self.download_source(
                    owner, repo, sha, repository_path
                )

                destination.write_bytes(content)
                hash_path.write_text(
                    hashlib.sha256(content).hexdigest(),
                    encoding="utf-8"
                )

            results.append({
                "parent": name,
                "status": "downloaded" if not cache_valid else "cached",
                "repository_path": repository_path,
                "local_path": str(destination),
                "sha256": hashlib.sha256(content).hexdigest(),
                "resolved_commit": sha
            })

        output_path = (
            INTERMEDIATE_DIR / component_name / "parent_sources.json"
        )

        output_path.write_text(
            json.dumps(results, indent=2),
            encoding="utf-8"
        )

        print(f"\n[SUCCESS] Parent sources saved: {output_path}")

        return results

    
    def download_parent_implementations(self, component_name):
        """Download parent .cpp/.inl files using the shared SHA cache."""

        component_root = RAW_CODE_DIR / component_name
        manifests = list(component_root.glob("*/manifest.json"))

        if not manifests:
            raise FileNotFoundError("Component manifest not found")

        manifest_path = max(
            manifests,
            key=lambda p: p.stat().st_mtime
        )

        manifest = json.loads(
            manifest_path.read_text(encoding="utf-8")
        )

        sha = manifest["resolved_commit"]
        owner, repo = manifest["repository"].split("/")

        parent_sources_path = (
            INTERMEDIATE_DIR / component_name / "parent_sources.json"
        )

        parent_sources = json.loads(
            parent_sources_path.read_text(encoding="utf-8")
        )

        repo_files = set(
            self.get_repository_files(owner, repo, sha)
        )

        cache_root = (
            RAW_CODE_DIR / "_shared_cache" / owner / repo / sha
        )

        results = []

        for parent in parent_sources:

            name = parent["parent"]

            if parent["status"] not in ("cached", "downloaded"):
                print(f"[SKIP] {name}: unresolved parent")
                continue

            if parent["resolved_commit"] != sha:
                raise ValueError(
                    f"Commit mismatch for parent {name}"
                )

            header_path = parent["repository_path"]
            stem = header_path.rsplit(".", 1)[0]

            for extension in (".cpp", ".inl"):

                repository_path = stem + extension

                if repository_path not in repo_files:
                    continue

                destination = self.cache_path(cache_root / repository_path)
                destination.parent.mkdir(
                    parents=True, exist_ok=True
                )

                hash_path = self.cache_path(
                    destination.with_name(destination.name + ".sha256")
                )

                cache_valid = False

                if destination.is_file() and hash_path.is_file():

                    actual_hash = hashlib.sha256(
                        destination.read_bytes()
                    ).hexdigest()

                    expected_hash = hash_path.read_text(
                        encoding="utf-8"
                    ).strip()

                    cache_valid = actual_hash == expected_hash

                if cache_valid:
                    print(
                        f"[CACHE HIT] {name}: "
                        f"{repository_path}"
                    )
                    content = destination.read_bytes()

                else:
                    print(
                        f"[DOWNLOAD] {name}: "
                        f"{repository_path}"
                    )

                    content = self.download_source(
                        owner, repo, sha, repository_path
                    )

                    destination.write_bytes(content)

                    hash_path.write_text(
                        hashlib.sha256(content).hexdigest(),
                        encoding="utf-8"
                    )

                results.append({
                    "parent": name,
                    "repository_path": repository_path,
                    "local_path": str(destination),
                    "resolved_commit": sha,
                    "sha256": hashlib.sha256(content).hexdigest(),
                    "status": (
                        "cached" if cache_valid else "downloaded"
                    )
                })

        output_path = (
            INTERMEDIATE_DIR
            / component_name
            / "parent_implementations.json"
        )

        output_path.write_text(
            json.dumps(results, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )

        print(
            f"\n[SUCCESS] {len(results)} "
            f"parent implementation files available"
        )
        print(f"[SAVED] {output_path}")

        return results

    def run(self):
        components = self.load_components()

        for component in components:
            self.ingest_component(component)


if __name__ == "__main__":
    SofaIngestor().run()

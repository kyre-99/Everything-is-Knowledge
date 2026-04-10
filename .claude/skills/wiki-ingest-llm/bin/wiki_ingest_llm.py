#!/usr/bin/env python3
"""
Wiki ingest LLM CLI - External LLM extraction pipeline.
Fetches sources and extracts entities using OpenAI API.

Usage:
    uv run python wiki_ingest_llm.py raw/paper.pdf
    uv run python wiki_ingest_llm.py https://example.com
    uv run python wiki_ingest_llm.py raw/*.pdf --parallel 5
    uv run python wiki_ingest_llm.py 2409.05591  # arXiv ID
"""

import sys
import json
import os
import re
import argparse
from datetime import datetime
from pathlib import Path
from typing import Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

from openai import OpenAI

# Import from shared location
SHARED_BIN = Path(__file__).parent.parent.parent.parent / "shared" / "bin"
sys.path.insert(0, str(SHARED_BIN))

from pdf_reader import parse_pdf
from web_fetcher import fetch_url
from wiki_config import get_openai_config
from llm_extractor import (
    slugify,
    convert_to_wiki_links,
    extract_two_phase,
)
try:
    from bilibili_fetcher import fetch_bilibili
except ImportError:
    fetch_bilibili = None  # Optional dependency


# ============================================================================
# Wiki Page Writers
# ============================================================================


# ============================================================================
# Wiki Link Conversion
# ============================================================================
# Wiki Page Writers
# ============================================================================

def write_entity_page(
    entity: dict,
    source_slug: str,
    wiki_dir: Path,
    all_entity_names: list[str]
) -> tuple[str, bool]:
    """
    Write or update entity page with new structure.

    New structure:
    ---
    # RAG
    type: artifact

    ## Facts
    - [[RAG]] 是一种为大型语言模型提供外部知识库上下文的技术...

    ## Source Documents
    - [[memorag]]
    ---

    Returns: (slug, is_new)
    """
    name = entity.get("name", "Unknown")
    is_new = entity.get("is_new", True)
    existing_slug = entity.get("existing_slug")

    slug = existing_slug if (not is_new and existing_slug) else slugify(name)

    entities_dir = wiki_dir / "entities"
    entities_dir.mkdir(parents=True, exist_ok=True)

    entity_path = entities_dir / f"{slug}.md"

    # Convert context to wiki links
    context = entity.get("context", "")
    context_with_links = convert_to_wiki_links(context, all_entity_names)

    if is_new or not entity_path.exists():
        # Create new entity page - fact includes source directly
        fact_line = f"- {context_with_links} [[{source_slug}]]"
        content = f"""# {name}
type: {entity.get('type', 'abstract')}

## Facts

{fact_line}
"""
        entity_path.write_text(content, encoding="utf-8")
        return slug, True
    else:
        # Update existing entity page - append fact with source
        existing_content = entity_path.read_text(encoding="utf-8")

        # Format fact with source
        fact_line = f"- {context_with_links} [[{source_slug}]]"

        # Append new fact to Facts section
        if "## Facts" in existing_content:
            lines = existing_content.split("\n")
            new_lines = []
            in_facts = False
            added = False

            for i, line in enumerate(lines):
                new_lines.append(line)
                if line.startswith("## Facts"):
                    in_facts = True
                elif in_facts and (line.startswith("## ") or i == len(lines) - 1):
                    if not added:
                        new_lines.append(fact_line)
                        added = True
                    in_facts = False

            existing_content = "\n".join(new_lines)

        # Remove old Source Documents section if present (migration)
        if "## Source Documents" in existing_content:
            lines = existing_content.split("\n")
            new_lines = []
            skip_until_next_section = False
            for line in lines:
                if line.startswith("## Source Documents"):
                    skip_until_next_section = True
                    continue
                if skip_until_next_section:
                    if line.startswith("## ") or (line.strip() == "" and i < len(lines) - 1):
                        skip_until_next_section = False
                        if line.startswith("## "):
                            new_lines.append(line)
                    continue
                new_lines.append(line)
            existing_content = "\n".join(new_lines).rstrip()

        entity_path.write_text(existing_content + "\n", encoding="utf-8")
        return slug, False


def update_cache_md(new_entity_names: list[str], wiki_dir: Path) -> None:
    """
    Update wiki/cache.md with new entity names.

    Format: One name per line, no duplicates.
    """
    cache_path = wiki_dir / "cache.md"

    existing_names = []
    if cache_path.exists():
        existing_names = [
            line.strip()
            for line in cache_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    # Append new names (avoid duplicates)
    new_names = [name for name in new_entity_names if name and name not in existing_names]

    if new_names:
        content = "\n".join(existing_names + new_names) + "\n"
        cache_path.write_text(content, encoding="utf-8")


def parse_cache_md(cache_path: Path) -> list[dict]:
    """
    Parse wiki/cache.md to extract existing entity names.

    Returns:
        List of {name, slug} dicts
    """
    entities = []

    if not cache_path.exists():
        return entities

    content = cache_path.read_text(encoding="utf-8")

    for line in content.splitlines():
        name = line.strip()
        if name:
            slug = slugify(name)
            entities.append({"name": name, "slug": slug})

    return entities


def append_log_md(results: list[dict], errors: list[dict], wiki_dir: Path) -> None:
    """Append to wiki/log.md."""
    log_path = wiki_dir / "log.md"

    if not log_path.exists():
        log_content = f"""---
title: Wiki Log
created: {datetime.now().strftime('%Y-%m-%d')}
type: log
---

# Wiki Log

"""
    else:
        log_content = log_path.read_text(encoding="utf-8")

    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')

    # Count created/updated entities
    created_entities = sum(1 for r in results for e in r.get("entities", []) if e.get("is_new", True))

    source_titles = [r.get("source", {}).get("title", "unknown") for r in results]

    entry = f"""
## {timestamp} ingest-llm | {', '.join(source_titles[:3])}{'...' if len(source_titles) > 3 else ''}
- Created: entities[{created_entities}]
- Updated: cache.md
- LLM: gpt-4o-mini (or gpt-4o fallback)
- Status: {'success' if results else 'failed'}
- Errors: {len(errors)}
"""

    log_content = log_content.rstrip() + entry + "\n"
    log_path.write_text(log_content, encoding="utf-8")


def write_all_wiki_pages(results: list[dict], wiki_dir: Path) -> dict:
    """
    Write all entity pages from extraction results.

    Returns summary of what was created/updated.
    """
    summary = {
        "entities_created": 0,
        "entities_updated": 0,
    }

    # Collect all entity names for wiki link conversion
    all_entity_names = []
    for result in results:
        for entity in result.get("entities", []):
            all_entity_names.append(entity.get("name", ""))

    for result in results:
        # Use actual file slug from _source_slug (computed in main)
        source_slug = result.get("_source_slug", slugify(result.get("source", {}).get("title", "unknown")))

        # Write entity pages
        for entity in result.get("entities", []):
            entity_slug, entity_is_new = write_entity_page(
                entity, source_slug, wiki_dir, all_entity_names
            )
            if entity_is_new:
                summary["entities_created"] += 1
            else:
                summary["entities_updated"] += 1

    # Update cache.md
    new_entity_names = [
        e.get("name")
        for r in results
        for e in r.get("entities", [])
        if e.get("is_new", True)
    ]
    update_cache_md(new_entity_names, wiki_dir)

    return summary


# ============================================================================
# Source Routing
# ============================================================================

def detect_source_type(source: str) -> tuple[str, str]:
    """
    Detect source type and return (type, normalized_source).

    Types: paper, video, article, arxiv
    """
    # Check if arXiv ID (e.g., 2409.05591 or arxiv:2409.05591)
    arxiv_pattern = r'^(arxiv:)?(\d{4}\.\d{4,5})$'
    arxiv_match = re.match(arxiv_pattern, source.lower())
    if arxiv_match:
        return "arxiv", arxiv_match.group(2)

    # Check if URL
    if source.startswith("http://") or source.startswith("https://"):
        if "bilibili.com/video/" in source:
            return "video", source
        elif source.endswith(".pdf"):
            return "paper", source
        elif "arxiv.org/abs/" in source or "arxiv.org/pdf/" in source:
            # Extract arXiv ID from URL
            arxiv_id_match = re.search(r'(\d{4}\.\d{4,5})', source)
            if arxiv_id_match:
                return "arxiv", arxiv_id_match.group(1)
            return "paper", source
        else:
            return "article", source

    # Check if local file
    path = Path(source)
    if path.exists():
        if source.endswith(".pdf"):
            return "paper", str(path.resolve())
        elif source.endswith(".md") or source.endswith(".txt"):
            return "article", str(path.resolve())
        else:
            # Try as PDF by default for local files
            return "paper", str(path.resolve())

    # Check if bare arXiv ID (without prefix)
    if re.match(r'^\d{4}\.\d{4,5}$', source):
        return "arxiv", source

    # Unknown - treat as URL attempt
    return "article", source


def fetch_source(source: str, source_type: str, raw_dir: Path = None) -> dict:
    """Fetch source content using appropriate fetcher.

    Args:
        source: Source identifier (URL, path, arXiv ID)
        source_type: Type of source (paper, video, article, arxiv)
        raw_dir: Directory to save raw content

    Returns:
        Dict with content, title, metadata, success, saved_slug
    """
    try:
        saved_slug = None
        saved_path = None

        if source_type == "paper":
            result = parse_pdf(source)
            title = result.get("title", Path(source).stem)

            # Save to wiki/raw/
            if raw_dir and result.get("success"):
                raw_dir.mkdir(parents=True, exist_ok=True)
                filename = f"{slugify(title)}.md"
                saved_path = raw_dir / filename
                saved_slug = slugify(title)

                # Check if already cached (skip save if exists)
                if saved_path.exists():
                    return {
                        "content": "",
                        "title": title,
                        "metadata": result.get("metadata", {}),
                        "success": True,
                        "saved_slug": saved_slug,
                        "saved_to": str(saved_path),
                        "_cached": True,
                    }

                saved_path.write_text(result.get("content", ""), encoding="utf-8")

            return {
                "content": result.get("content", ""),
                "title": title,
                "metadata": result.get("metadata", {}),
                "success": result.get("success", True),
                "saved_slug": saved_slug,
                "saved_to": str(saved_path) if saved_path else None
            }
        elif source_type == "video":
            if fetch_bilibili:
                result = fetch_bilibili(source)
                title = result.get("title", "bilibili-video")
                bvid = result.get("bvid", "")
                video_url = result.get("url", source)

                # Initialize defaults
                saved_slug = None
                saved_path = None

                # Save to wiki/raw/ with metadata
                if raw_dir:
                    raw_dir.mkdir(parents=True, exist_ok=True)
                    filename = f"{slugify(title)}.md"
                    saved_path = raw_dir / filename
                    saved_slug = slugify(title)

                    # Check if already cached (skip save if exists)
                    if saved_path.exists():
                        return {
                            "content": "",
                            "title": title,
                            "metadata": result.get("metadata", {}),
                            "success": True,
                            "saved_slug": saved_slug,
                            "saved_to": str(saved_path),
                            "_cached": True,
                        }

                    # Format content with metadata header
                    author = result.get("author", "Unknown")
                    duration = result.get("duration", 0)
                    metadata = result.get("metadata", {})

                    content_with_meta = f"""# {title}

> Source: {video_url}
> Author: {author}
> Duration: {duration}s
> BV ID: {bvid}

---

{result.get("content", "")}
"""
                    saved_path.write_text(content_with_meta, encoding="utf-8")

                return {
                    "content": result.get("content", ""),
                    "title": title,
                    "metadata": result.get("metadata", {}),
                    "success": result.get("success", False),
                    "saved_slug": saved_slug,
                    "saved_to": str(saved_path) if saved_path else None
                }
            else:
                return {"content": "", "title": "", "metadata": {}, "success": False, "error": "bilibili_fetcher not available"}
        elif source_type == "arxiv":
            # Fetch from DeepXiv API
            try:
                from deepxiv_sdk import Reader, APIError
                reader = Reader()
                # Get full paper content
                content = reader.raw(source)
                head = reader.head(source)

                title = head.get("title", source) if head else source

                # Save to wiki/raw/arxiv-{id}.md
                if raw_dir and content:
                    raw_dir.mkdir(parents=True, exist_ok=True)
                    filename = f"arxiv-{source}.md"
                    saved_path = raw_dir / filename
                    saved_slug = f"arxiv-{source}"

                    # Check if already cached (skip save if exists)
                    if saved_path.exists():
                        return {
                            "content": "",
                            "title": title,
                            "metadata": {
                                "arxiv_id": source,
                                "authors": head.get("authors", []) if head else [],
                                "categories": head.get("categories", []) if head else [],
                                "publish_at": head.get("publish_at", "") if head else "",
                            },
                            "success": True,
                            "saved_slug": saved_slug,
                            "saved_to": str(saved_path),
                            "_cached": True,
                        }

                    saved_path.write_text(content, encoding="utf-8")

                return {
                    "content": content,
                    "title": title,
                    "metadata": {
                        "arxiv_id": source,
                        "authors": head.get("authors", []) if head else [],
                        "categories": head.get("categories", []) if head else [],
                        "publish_at": head.get("publish_at", "") if head else "",
                    },
                    "success": bool(content),
                    "saved_slug": saved_slug,
                    "saved_to": str(saved_path) if saved_path else None
                }
            except ImportError:
                return {"content": "", "title": "", "metadata": {}, "success": False, "error": "deepxiv_sdk not installed. Run: pip install deepxiv-sdk"}
            except Exception as e:
                return {"content": "", "title": "", "metadata": {}, "success": False, "error": f"DeepXiv API error: {str(e)}"}
        else:  # article
            # Check if local file
            path = Path(source)
            if path.exists() and not source.startswith("http"):
                # Read local markdown/text file directly
                content = path.read_text(encoding="utf-8")
                title = path.stem  # filename without extension

                # Save to wiki/raw/ (copy the file)
                if raw_dir and content:
                    raw_dir.mkdir(parents=True, exist_ok=True)
                    filename = f"{slugify(title)}.md"
                    saved_path = raw_dir / filename
                    saved_slug = slugify(title)

                    # Check if already cached (skip save if exists)
                    if saved_path.exists():
                        return {
                            "content": "",
                            "title": title,
                            "metadata": {"source": str(path.resolve())},
                            "success": True,
                            "saved_slug": saved_slug,
                            "saved_to": str(saved_path),
                            "_cached": True,
                        }

                    saved_path.write_text(content, encoding="utf-8")

                return {
                    "content": content,
                    "title": title,
                    "metadata": {"source": str(path.resolve())},
                    "success": True,
                    "saved_slug": saved_slug,
                    "saved_to": str(saved_path) if saved_path else None
                }
            else:
                # Fetch from URL
                result = fetch_url(source)
                title = result.get("title", source.split("/")[-1])

                # Save to wiki/raw/
                if raw_dir and result.get("success"):
                    raw_dir.mkdir(parents=True, exist_ok=True)
                    filename = f"{slugify(title)}.md"
                    saved_path = raw_dir / filename
                    saved_slug = slugify(title)

                    # Check if already cached (skip save if exists)
                    if saved_path.exists():
                        return {
                            "content": "",
                            "title": title,
                            "metadata": result.get("metadata", {}),
                            "success": True,
                            "saved_slug": saved_slug,
                            "saved_to": str(saved_path),
                            "_cached": True,
                        }

                    saved_path.write_text(result.get("content", ""), encoding="utf-8")

                return {
                    "content": result.get("content", ""),
                    "title": title,
                    "metadata": result.get("metadata", {}),
                    "success": result.get("success", True),
                    "saved_slug": saved_slug,
                    "saved_to": str(saved_path) if saved_path else None
                }
    except Exception as e:
        return {"content": "", "title": "", "metadata": {}, "success": False, "error": str(e)}


# ============================================================================
# Main Processing
# ============================================================================

def check_source_cached(source_slug: str, wiki_dir: Path) -> bool:
    """
    Check if source has been parsed before.

    Returns True if wiki/raw/{source_slug}.md exists.
    """
    raw_dir = wiki_dir / "raw"
    cached_file = raw_dir / f"{source_slug}.md"
    return cached_file.exists()


def process_source(
    source: str,
    client: OpenAI,
    existing_entities: list[dict],
    model: str = "gpt-4o-mini",
    wiki_dir: Path = None
) -> dict:
    """
    Process a single source: fetch + extract.

    Returns ExtractionResult or error.
    """
    source_type, normalized_source = detect_source_type(source)
    print(f"  [{source_type}] Processing: {source[:50]}...", file=sys.stderr)

    # Determine raw_dir for saving all source content
    raw_dir = wiki_dir / "raw" if wiki_dir else None

    # Check cache BEFORE fetching (for types where slug is predictable)
    if source_type == "arxiv":
        source_slug = f"arxiv-{normalized_source}"
        if raw_dir and check_source_cached(source_slug, wiki_dir):
            print(f"  ⏭️ Already parsed (cached: raw/{source_slug}.md)", file=sys.stderr)
            return {
                "source": {"title": normalized_source, "slug": source_slug},
                "entities": [],
                "_source_slug": source_slug,
                "_cached": True,
            }
    elif source_type == "paper" and not source.startswith("http"):
        # Local PDF file - check cache by filename stem
        path = Path(source)
        if path.exists() and raw_dir:
            preliminary_slug = slugify(path.stem)
            if check_source_cached(preliminary_slug, wiki_dir):
                print(f"  ⏭️ Already parsed (cached: raw/{preliminary_slug}.md)", file=sys.stderr)
                return {
                    "source": {"title": path.stem, "slug": preliminary_slug},
                    "entities": [],
                    "_source_slug": preliminary_slug,
                    "_cached": True,
                }

    # Fetch (saves content to wiki/raw/)
    fetch_result = fetch_source(normalized_source, source_type, raw_dir)

    # Check cache flag from fetch_result (for URL types where slug comes from title)
    if fetch_result.get("_cached"):
        print(f"  ⏭️ Already parsed (cached: raw/{fetch_result['saved_slug']}.md)", file=sys.stderr)
        return {
            "source": {"title": fetch_result.get("title", source), "slug": fetch_result["saved_slug"]},
            "entities": [],
            "_source_slug": fetch_result["saved_slug"],
            "_cached": True,
        }

    if not fetch_result.get("success"):
        return {
            "source": {"title": source, "slug": slugify(source)},
            "entities": [],
            "error": fetch_result.get("error", "Fetch failed")
        }

    content = fetch_result.get("content", "")
    title = fetch_result.get("title", source)

    if not content:
        return {
            "source": {"title": title, "slug": slugify(title)},
            "entities": [],
            "error": "Empty content"
        }

    # Extract using two-phase approach
    result = extract_two_phase(client, content, source_type, existing_entities, model)

    # Store saved slug/path for wiki cross-references
    if fetch_result.get("saved_slug"):
        result["_source_slug"] = fetch_result["saved_slug"]
    if fetch_result.get("saved_to"):
        result["_saved_to"] = fetch_result["saved_to"]

    return result


def main():
    parser = argparse.ArgumentParser(description="Wiki ingest with external LLM extraction")
    parser.add_argument("sources", nargs="+", help="Sources to ingest (PDFs, URLs, markdown files)")
    parser.add_argument("--parallel", "-p", type=int, default=10, help="Max parallel workers (default: 10)")
    parser.add_argument("--model", "-m", default="gpt-4o-mini", help="LLM model (default: gpt-4o-mini)")
    parser.add_argument("--cache", default="wiki/cache.md", help="Path to wiki cache.md")
    parser.add_argument("--write", "-w", action="store_true", default=True, help="Write wiki pages (default: True)")
    parser.add_argument("--no-write", dest="write", action="store_false", help="Skip writing wiki pages, only output JSON")

    args = parser.parse_args()

    # Get OpenAI config (priority: env vars > config file > defaults)
    api_key, base_url = get_openai_config()

    if not api_key:
        print("Error: OpenAI API key not configured", file=sys.stderr)
        print("Set via: export OPENAI_API_KEY=your-key", file=sys.stderr)
        print("Or run: uv run python .claude/shared/bin/wiki_config.py set openai_api_key your-key", file=sys.stderr)
        sys.exit(1)

    client = OpenAI(api_key=api_key, base_url=base_url, timeout=60.0)

    # Parse cache.md
    cache_path = Path(args.cache)
    wiki_dir = cache_path.parent
    existing_entities = parse_cache_md(cache_path)
    print(f"Loaded {len(existing_entities)} entities from cache.md", file=sys.stderr)

    # Process sources
    results = []
    errors = []

    print(f"Processing {len(args.sources)} sources with {args.parallel} workers...", file=sys.stderr)

    with ThreadPoolExecutor(max_workers=args.parallel) as executor:
        futures = {
            executor.submit(process_source, src, client, existing_entities, args.model, wiki_dir): src
            for src in args.sources
        }

        for future in as_completed(futures):
            src = futures[future]
            try:
                result = future.result()
                # Store source type and URL for wiki writing
                source_type, normalized_source = detect_source_type(src)
                result["_source_type"] = source_type
                result["_source_url"] = normalized_source

                # source_slug is already set by process_source() from saved file
                # Fallback only if not set (e.g., fetch failed)
                if not result.get("_source_slug"):
                    if source_type == "arxiv":
                        result["_source_slug"] = f"arxiv-{normalized_source}"
                    else:
                        result["_source_slug"] = slugify(src.split("/")[-1].split("?")[0])

                if "error" in result and result.get("entities") is None:
                    errors.append({"source": src, "error": result.get("error")})
                else:
                    results.append(result)
            except Exception as e:
                errors.append({"source": src, "error": str(e)})

    # Output JSON
    output = {
        "results": results,
        "errors": errors
    }

    print(json.dumps(output, ensure_ascii=False, indent=2))

    # Write wiki pages if requested
    if args.write and results:
        print(f"\nWriting wiki pages to {wiki_dir}...", file=sys.stderr)
        summary = write_all_wiki_pages(results, wiki_dir)
        append_log_md(results, errors, wiki_dir)

        print(f"Created: entities[{summary['entities_created']}]", file=sys.stderr)
        print(f"Updated: entities[{summary['entities_updated']}]", file=sys.stderr)

    # Exit code
    if results:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
Wiki ingest LLM CLI - External LLM extraction pipeline.
Fetches sources and extracts entities/concepts using OpenAI API.

Usage:
    uv run python wiki_ingest_llm.py raw/paper.pdf
    uv run python wiki_ingest_llm.py https://example.com
    uv run python wiki_ingest_llm.py raw/*.pdf --parallel 5
"""

import sys
import json
import os
import re
import argparse
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Any
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed

from openai import OpenAI

# Import fetchers from shared location
SHARED_BIN = Path(__file__).parent.parent.parent.parent / "shared" / "bin"
sys.path.insert(0, str(SHARED_BIN))

from pdf_reader import parse_pdf
from web_fetcher import fetch_url
from wiki_config import get_openai_config, get_config
try:
    from bilibili_fetcher import fetch_bilibili
except ImportError:
    fetch_bilibili = None  # Optional dependency


# ============================================================================
# Slugify Helper
# ============================================================================

def slugify(name: str) -> str:
    """Convert name to slug format."""
    # Lowercase, replace spaces with hyphens, remove special chars
    slug = name.lower().replace(" ", "-").replace("/", "-")
    # Keep letters, numbers, Chinese characters, hyphens
    slug = re.sub(r"[^\w\-\u4e00-\u9fff]", "", slug)
    # Max 60 chars
    return slug[:60]


# ============================================================================
# Wiki Page Writers
# ============================================================================

def write_source_page(result: dict, wiki_dir: Path) -> tuple[str, bool]:
    """
    Write source page to wiki/sources/{slug}.md.

    Returns: (slug, is_new)
    """
    source = result.get("source", {})
    raw_slug = source.get("slug") or slugify(source.get("title", "unknown"))

    # Ensure slug is valid for file path (not a URL)
    slug = slugify(raw_slug) if raw_slug.startswith("http") else raw_slug

    sources_dir = wiki_dir / "sources"
    sources_dir.mkdir(parents=True, exist_ok=True)

    source_path = sources_dir / f"{slug}.md"
    is_new = not source_path.exists()

    source_type = result.get("_source_type", "article")
    source_url = result.get("_source_url", "")

    # Skip if empty content (error case)
    if result.get("error") and not source.get("summary"):
        return slug, False

    # Build source page content
    content = f"""---
title: {source.get('title', 'Unknown')}
date: {datetime.now().strftime('%Y-%m-%d')}
type: {source_type}
tags: []
status: draft
---

# {source.get('title', 'Unknown')}

## Summary

{source.get('summary', '')}

## Key Points

"""
    for point in source.get("key_points", []):
        content += f"- {point}\n"

    content += "\n## Entities Mentioned\n\n"
    for entity in result.get("entities", []):
        content += f"- [[{entity.get('name')}]] -- {entity.get('context', '')}\n"

    content += "\n## Concepts\n\n"
    for concept in result.get("concepts", []):
        content += f"- [[{concept.get('name')}]] -- {concept.get('application', '')}\n"

    content += f"\n## Raw Source\n\n{source_url}\n"

    source_path.write_text(content, encoding="utf-8")
    return slug, is_new


def write_entity_page(entity: dict, source_title: str, wiki_dir: Path) -> tuple[str, bool]:
    """
    Write or update entity page.

    Returns: (slug, is_new)
    """
    name = entity.get("name", "Unknown")
    is_new = entity.get("is_new", True)
    existing_slug = entity.get("existing_slug")

    slug = existing_slug if (not is_new and existing_slug) else slugify(name)

    entities_dir = wiki_dir / "entities"
    entities_dir.mkdir(parents=True, exist_ok=True)

    entity_path = entities_dir / f"{slug}.md"

    if is_new or not entity_path.exists():
        # Create new entity page
        content = f"""---
name: {name}
type: {entity.get('type', 'person')}
aliases: []
---

# {name}

## Overview

{entity.get('context', '')}

## Appearances in Sources

- [[{source_title}]] -- {entity.get('context', '')}

## Related Entities

"""
        entity_path.write_text(content, encoding="utf-8")
        return slug, True
    else:
        # Update existing entity page - append to Appearances in Sources
        existing_content = entity_path.read_text(encoding="utf-8")

        # Find Appearances in Sources section and append
        if "## Appearances in Sources" in existing_content:
            # Append after the section
            lines = existing_content.split("\n")
            new_lines = []
            in_appearances = False
            added = False

            for i, line in enumerate(lines):
                new_lines.append(line)
                if line.startswith("## Appearances in Sources"):
                    in_appearances = True
                elif in_appearances and (line.startswith("## ") or i == len(lines) - 1):
                    if not added:
                        new_lines.append(f"- [[{source_title}]] -- {entity.get('context', '')}")
                        added = True
                    in_appearances = False

            entity_path.write_text("\n".join(new_lines), encoding="utf-8")
        else:
            # Add section if missing
            existing_content += f"\n\n## Appearances in Sources\n\n- [[{source_title}]] -- {entity.get('context', '')}\n"
            entity_path.write_text(existing_content, encoding="utf-8")

        return slug, False


def write_concept_page(concept: dict, source_title: str, wiki_dir: Path) -> tuple[str, bool]:
    """
    Write or update concept page.

    Returns: (slug, is_new)
    """
    name = concept.get("name", "Unknown")
    is_new = concept.get("is_new", True)
    existing_slug = concept.get("existing_slug")

    slug = existing_slug if (not is_new and existing_slug) else slugify(name)

    concepts_dir = wiki_dir / "concepts"
    concepts_dir.mkdir(parents=True, exist_ok=True)

    concept_path = concepts_dir / f"{slug}.md"

    if is_new or not concept_path.exists():
        # Create new concept page
        content = f"""---
name: {name}
type: {concept.get('type', 'idea')}
---

# {name}

## Definition

{concept.get('definition', '')}

## Applications

- [[{source_title}]] -- {concept.get('application', '')}

## Related Concepts

"""
        concept_path.write_text(content, encoding="utf-8")
        return slug, True
    else:
        # Update existing concept page - append to Applications
        existing_content = concept_path.read_text(encoding="utf-8")

        if "## Applications" in existing_content:
            lines = existing_content.split("\n")
            new_lines = []
            in_applications = False
            added = False

            for i, line in enumerate(lines):
                new_lines.append(line)
                if line.startswith("## Applications"):
                    in_applications = True
                elif in_applications and (line.startswith("## ") or i == len(lines) - 1):
                    if not added:
                        new_lines.append(f"- [[{source_title}]] -- {concept.get('application', '')}")
                        added = True
                    in_applications = False

            concept_path.write_text("\n".join(new_lines), encoding="utf-8")
        else:
            existing_content += f"\n\n## Applications\n\n- [[{source_title}]] -- {concept.get('application', '')}\n"
            concept_path.write_text(existing_content, encoding="utf-8")

        return slug, False


def update_index_md(results: list[dict], wiki_dir: Path) -> None:
    """Update wiki/index.md with new entries."""
    index_path = wiki_dir / "index.md"

    if not index_path.exists():
        # Create basic index if missing
        index_content = """---
title: Wiki Index
created: {}
type: index
---

# Wiki Index

Last updated: {}

## Sources

## Entities

## Concepts
""".format(datetime.now().strftime('%Y-%m-%d'), datetime.now().strftime('%Y-%m-%d'))
    else:
        index_content = index_path.read_text(encoding="utf-8")

    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')

    # Collect new entries
    new_sources = []
    new_entities = []
    new_concepts = []

    for result in results:
        source = result.get("source", {})
        if result.get("_source_is_new", True):
            new_sources.append(source)

        for entity in result.get("entities", []):
            if entity.get("is_new", True):
                new_entities.append(entity)

        for concept in result.get("concepts", []):
            if concept.get("is_new", True):
                new_concepts.append(concept)

    # Build additions
    additions = []

    for source in new_sources:
        slug = source.get("slug") or slugify(source.get("title", ""))
        additions.append(f"\n## {timestamp} Added sources/{slug}.md")
        entity_names = [e.get("name") for e in results[0].get("entities", [])[:3]]
        concept_names = [c.get("name") for c in results[0].get("concepts", [])[:3]]
        if entity_names:
            additions.append(f"- Entities: [[{', '.join(entity_names)}]]")
        if concept_names:
            additions.append(f"- Concepts: [[{', '.join(concept_names)}]]")

    # Add to Sources section
    for source in new_sources:
        slug = source.get("slug") or slugify(source.get("title", ""))
        additions.append(f"\n## Sources\n- [[{source.get('title')}]] -- article, {datetime.now().strftime('%Y-%m-%d')} -- {source.get('summary', '')[:50]}...")

    # Add to Entities section
    for entity in new_entities:
        additions.append(f"\n## Entities\n- [[{entity.get('name')}]] -- {entity.get('context', '')[:50]}...")

    # Add to Concepts section
    for concept in new_concepts:
        additions.append(f"\n## Concepts\n- [[{concept.get('name')}]] -- {concept.get('definition', '')[:50]}...")

    # Append to index
    if additions:
        # Find where to insert (after each section)
        lines = index_content.split("\n")

        # Simple approach: append at end before closing
        index_content = index_content.rstrip()
        index_content += "\n" + "\n".join(additions) + "\n"

        index_path.write_text(index_content, encoding="utf-8")


def append_log_md(results: list[dict], errors: list[dict], wiki_dir: Path) -> None:
    """Append to wiki/log.md."""
    log_path = wiki_dir / "log.md"

    if not log_path.exists():
        log_content = """---
title: Wiki Log
created: {}
type: log
---

# Wiki Log

""".format(datetime.now().strftime('%Y-%m-%d'))
    else:
        log_content = log_path.read_text(encoding="utf-8")

    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')

    # Count created/updated
    created_sources = sum(1 for r in results if r.get("_source_is_new", True))
    created_entities = sum(1 for r in results for e in r.get("entities", []) if e.get("is_new", True))
    created_concepts = sum(1 for r in results for c in r.get("concepts", []) if c.get("is_new", True))

    source_titles = [r.get("source", {}).get("title", "unknown") for r in results]

    entry = f"""
## {timestamp} ingest-llm | {', '.join(source_titles[:3])}{'...' if len(source_titles) > 3 else ''}
- Created: sources/[{created_sources}], entities/[{created_entities}], concepts/[{created_concepts}]
- Updated: index.md
- LLM: gpt-4o-mini (or gpt-4o fallback)
- Status: {'success' if results else 'failed'}
- Errors: {len(errors)} (if any)
"""

    log_content = log_content.rstrip() + entry + "\n"
    log_path.write_text(log_content, encoding="utf-8")


def write_all_wiki_pages(results: list[dict], wiki_dir: Path) -> dict:
    """
    Write all wiki pages from extraction results.

    Returns summary of what was created/updated.
    """
    summary = {
        "sources_created": 0,
        "sources_updated": 0,
        "entities_created": 0,
        "entities_updated": 0,
        "concepts_created": 0,
        "concepts_updated": 0
    }

    for result in results:
        # Write source page
        source_slug, source_is_new = write_source_page(result, wiki_dir)
        result["_source_is_new"] = source_is_new
        if source_is_new:
            summary["sources_created"] += 1
        else:
            summary["sources_updated"] += 1

        source_title = result.get("source", {}).get("title", "Unknown")

        # Write entity pages
        for entity in result.get("entities", []):
            entity_slug, entity_is_new = write_entity_page(entity, source_title, wiki_dir)
            if entity_is_new:
                summary["entities_created"] += 1
            else:
                summary["entities_updated"] += 1

        # Write concept pages
        for concept in result.get("concepts", []):
            concept_slug, concept_is_new = write_concept_page(concept, source_title, wiki_dir)
            if concept_is_new:
                summary["concepts_created"] += 1
            else:
                summary["concepts_updated"] += 1

    # Update index.md and log.md
    errors = []  # Will be passed from main
    update_index_md(results, wiki_dir)

    return summary


# ============================================================================
# Extraction Prompt (from wiki-extract-agent/SKILL.md)
# ============================================================================

EXTRACTION_PROMPT = """You are extracting knowledge from a {source_type} for a wiki.

SOURCE CONTENT:
{markdown_content}

EXISTING ENTITIES (from wiki index):
{existing_entities_json}

EXISTING CONCEPTS (from wiki index):
{existing_concepts_json}

TASK:
1. Write a 2-3 paragraph summary of this source
2. Extract 3-5 key points
3. Identify entities (people, orgs, products, events) mentioned
4. Identify concepts (ideas, frameworks, patterns) discussed
5. For each entity/concept, check if it matches an existing one

OUTPUT FORMAT (JSON only, no markdown):
{{
  "schema_version": "1.0",
  "source": {{
    "title": "...",
    "summary": "2-3 paragraph summary",
    "key_points": ["point 1", "point 2", "point 3"],
    "slug": "source-slug",
    "is_new": true
  }},
  "entities": [
    {{
      "name": "Entity Name",
      "type": "person | org | product | event",
      "context": "How this entity appears in this source",
      "is_new": true,
      "existing_slug": null
    }}
  ],
  "concepts": [
    {{
      "name": "Concept Name",
      "type": "idea | framework | pattern | methodology",
      "definition": "1-2 sentence definition",
      "application": "How applied in this source",
      "is_new": true,
      "existing_slug": null
    }}
  ]
}}

Entity matching rules (v1 - exact match only):
- Exact name match (case-insensitive) -> is_new: false, existing_slug: "matched-slug"
- Match against aliases in existing entities -> is_new: false, existing_slug: "matched-slug"
- Otherwise -> is_new: true, existing_slug: null

Do NOT use fuzzy matching. When in doubt, mark as new.
"""


# ============================================================================
# wiki/index.md Parser
# ============================================================================

def parse_index_md(index_path: Path) -> tuple[list[dict], list[dict], list[dict]]:
    """
    Parse wiki/index.md to extract existing entities, concepts, and sources.

    Returns:
        (entities, concepts, sources) - each is a list of {name, slug, description}
    """
    entities = []
    concepts = []
    sources = []

    if not index_path.exists():
        return entities, concepts, sources

    content = index_path.read_text(encoding="utf-8")

    # Parse ## Entities section
    in_entities = False
    in_concepts = False
    in_sources = False

    for line in content.split("\n"):
        line = line.strip()

        if line == "## Entities":
            in_entities = True
            in_concepts = False
            in_sources = False
            continue
        elif line == "## Concepts":
            in_entities = False
            in_concepts = True
            in_sources = False
            continue
        elif line == "## Sources":
            in_entities = False
            in_concepts = False
            in_sources = True
            continue
        elif line.startswith("## "):
            in_entities = False
            in_concepts = False
            in_sources = False
            continue

        # Parse list items: - [[Name]] -- description
        if line.startswith("- [["):
            match = re.match(r"- \[\[([^\]]+)\]\]\s*--\s*(.+)", line)
            if match:
                name = match.group(1)
                description = match.group(2)
                slug = name.lower().replace(" ", "-").replace("/", "-")
                slug = re.sub(r"[^\w\-\u4e00-\u9fff]", "", slug)[:60]

                if in_entities:
                    entities.append({"name": name, "slug": slug, "description": description})
                elif in_concepts:
                    concepts.append({"name": name, "slug": slug, "description": description})
                elif in_sources:
                    sources.append({"name": name, "slug": slug, "description": description})

    return entities, concepts, sources


# ============================================================================
# Source Routing
# ============================================================================

def detect_source_type(source: str) -> tuple[str, str]:
    """
    Detect source type and return (type, normalized_source).

    Types: paper, video, article, arxiv
    """
    import re

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


def fetch_source(source: str, source_type: str) -> dict:
    """Fetch source content using appropriate fetcher."""
    try:
        if source_type == "paper":
            result = parse_pdf(source)
            return {
                "content": result.get("content", ""),
                "title": result.get("title", ""),
                "metadata": result.get("metadata", {}),
                "success": result.get("success", True)
            }
        elif source_type == "video":
            if fetch_bilibili:
                result = fetch_bilibili(source)
                return {
                    "content": result.get("content", ""),
                    "title": result.get("title", ""),
                    "metadata": result.get("metadata", {}),
                    "success": result.get("success", True)
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

                return {
                    "content": content,
                    "title": title,
                    "metadata": {
                        "arxiv_id": source,
                        "authors": head.get("authors", []) if head else [],
                        "categories": head.get("categories", []) if head else [],
                        "publish_at": head.get("publish_at", "") if head else "",
                    },
                    "success": bool(content)
                }
            except ImportError:
                return {"content": "", "title": "", "metadata": {}, "success": False, "error": "deepxiv_sdk not installed. Run: pip install deepxiv-sdk"}
            except APIError as e:
                return {"content": "", "title": "", "metadata": {}, "success": False, "error": f"DeepXiv API error: {str(e)}"}
        else:  # article
            # Check if local file
            path = Path(source)
            if path.exists() and not source.startswith("http"):
                # Read local markdown/text file directly
                content = path.read_text(encoding="utf-8")
                title = path.stem  # filename without extension
                return {
                    "content": content,
                    "title": title,
                    "metadata": {"source": str(path.resolve())},
                    "success": True
                }
            else:
                # Fetch from URL
                result = fetch_url(source)
                return {
                    "content": result.get("content", ""),
                    "title": result.get("title", ""),
                    "metadata": result.get("metadata", {}),
                    "success": result.get("success", True)
                }
    except Exception as e:
        return {"content": "", "title": "", "metadata": {}, "success": False, "error": str(e)}


# ============================================================================
# LLM Extraction
# ============================================================================

def call_openai_extract(
    client: OpenAI,
    content: str,
    source_type: str,
    existing_entities: list[dict],
    existing_concepts: list[dict],
    model: str = "gpt-4o-mini",
    timeout: int = 60
) -> dict:
    """
    Call OpenAI API for entity/concept extraction.

    Returns ExtractionResult dict or error.
    """
    prompt = EXTRACTION_PROMPT.format(
        source_type=source_type,
        markdown_content=content[:30000],  # Truncate to avoid token limits
        existing_entities_json=json.dumps(existing_entities, ensure_ascii=False, indent=2),
        existing_concepts_json=json.dumps(existing_concepts, ensure_ascii=False, indent=2)
    )

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a knowledge extraction assistant. Output only valid JSON, no markdown formatting."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            timeout=timeout
        )

        result_text = response.choices[0].message.content
        result = json.loads(result_text)

        # Validate schema
        if "schema_version" not in result:
            result["schema_version"] = "1.0"

        return result

    except json.JSONDecodeError as e:
        return {"error": f"JSON parse error: {str(e)}", "raw": result_text if 'result_text' in dir() else ""}
    except Exception as e:
        return {"error": str(e)}


def check_extraction_quality(result: dict) -> bool:
    """
    Check if extraction quality is acceptable.

    Returns True if quality is LOW (needs gpt-4o fallback).
    """
    if "error" in result:
        return True  # Low quality - had error

    entities = result.get("entities", [])
    source = result.get("source", {})
    summary = source.get("summary", "")

    # Quality criteria from eng review:
    # - entities array empty
    # - summary <50 chars
    # - missing is_new fields
    if not entities:
        return True
    if len(summary) < 50:
        return True
    if not source.get("is_new") is not None:
        return True

    return False


def extract_with_retry(
    client: OpenAI,
    content: str,
    source_type: str,
    existing_entities: list[dict],
    existing_concepts: list[dict],
    model: str = "gpt-4o-mini",
    max_retries: int = 2
) -> dict:
    """
    Extract with retry and quality fallback to gpt-4o.
    """
    result = call_openai_extract(client, content, source_type, existing_entities, existing_concepts, model)

    # Check quality - if low, retry with gpt-4o
    if check_extraction_quality(result):
        print(f"  [WARN] Low quality extraction, retrying with gpt-4o...", file=sys.stderr)
        result = call_openai_extract(client, content, source_type, existing_entities, existing_concepts, "gpt-4o")

    # Retry on error
    retries = 0
    while "error" in result and retries < max_retries:
        retries += 1
        wait_time = 30 * retries  # Linear backoff
        print(f"  [RETRY {retries}/{max_retries}] Error: {result['error']}. Waiting {wait_time}s...", file=sys.stderr)
        time.sleep(wait_time)
        result = call_openai_extract(client, content, source_type, existing_entities, existing_concepts, model)

    return result


# ============================================================================
# Main Processing
# ============================================================================

def process_source(
    source: str,
    client: OpenAI,
    existing_entities: list[dict],
    existing_concepts: list[dict],
    model: str = "gpt-4o-mini"
) -> dict:
    """
    Process a single source: fetch + extract.

    Returns ExtractionResult or error.
    """
    source_type, normalized_source = detect_source_type(source)
    print(f"  [{source_type}] Processing: {source[:50]}...", file=sys.stderr)

    # Fetch
    fetch_result = fetch_source(normalized_source, source_type)
    if not fetch_result.get("success"):
        return {
            "source": {"title": source, "slug": source, "is_new": True},
            "entities": [],
            "concepts": [],
            "error": fetch_result.get("error", "Fetch failed")
        }

    content = fetch_result.get("content", "")
    title = fetch_result.get("title", source)

    if not content:
        return {
            "source": {"title": title, "slug": source, "is_new": True},
            "entities": [],
            "concepts": [],
            "error": "Empty content"
        }

    # Extract
    result = extract_with_retry(client, content, source_type, existing_entities, existing_concepts, model)

    # Ensure source title is set
    if "source" in result:
        result["source"]["title"] = result["source"].get("title") or title
        result["source"]["is_new"] = True  # Default to new

    return result


def main():
    parser = argparse.ArgumentParser(description="Wiki ingest with external LLM extraction")
    parser.add_argument("sources", nargs="+", help="Sources to ingest (PDFs, URLs, markdown files)")
    parser.add_argument("--parallel", "-p", type=int, default=10, help="Max parallel workers (default: 10)")
    parser.add_argument("--model", "-m", default="gpt-4o-mini", help="LLM model (default: gpt-4o-mini)")
    parser.add_argument("--index", default="wiki/index.md", help="Path to wiki index.md")
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

    # Parse index.md
    index_path = Path(args.index)
    wiki_dir = index_path.parent
    existing_entities, existing_concepts, existing_sources = parse_index_md(index_path)
    print(f"Loaded {len(existing_entities)} entities, {len(existing_concepts)} concepts from index.md", file=sys.stderr)

    # Process sources
    results = []
    errors = []

    print(f"Processing {len(args.sources)} sources with {args.parallel} workers...", file=sys.stderr)

    with ThreadPoolExecutor(max_workers=args.parallel) as executor:
        futures = {
            executor.submit(process_source, src, client, existing_entities, existing_concepts, args.model): src
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

        print(f"Created: sources/[{summary['sources_created']}], entities/[{summary['entities_created']}], concepts/[{summary['concepts_created']}]", file=sys.stderr)
        print(f"Updated: entities/[{summary['entities_updated']}], concepts/[{summary['concepts_updated']}]", file=sys.stderr)

    # Exit code
    if results:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
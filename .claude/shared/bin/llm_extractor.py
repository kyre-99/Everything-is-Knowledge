#!/usr/bin/env python3
"""
LLM Extractor - Two-phase entity extraction using OpenAI API.

Phase 1: Discover entities (name, type)
Phase 2: Generate detailed context for each entity

Usage:
    from llm_extractor import extract_two_phase

    result = extract_two_phase(
        client=OpenAI(),
        content=document_content,
        source_type="paper",
        existing_entities=[{"name": "RAG", "slug": "RAG"}],
    )
"""

import re
import json
from typing import Optional
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from openai import OpenAI


# ============================================================================
# Extraction Prompts
# ============================================================================

DISCOVERY_PROMPT = """You are discovering entities from a {source_type} for a wiki.

SOURCE CONTENT:
{markdown_content}

EXISTING ENTITIES (from wiki cache):
{existing_entities_json}

TASK:
1. Scan the entire document and identify all entities mentioned
2. Entity types: person, org, artifact, event, abstract
3. Focus on finding entities - do NOT write detailed context yet

Entity type definitions:
- person: 具体人物（研究者、作者、历史人物等）
- org: 组织机构（公司、高校、研究机构等）
- artifact: 人造产物（论文、代码库、产品、技术框架等）
- event: 具体事件（会议、发布会、历史事件等）
- abstract: 抽象概念（方法论、思想、模式等）

OUTPUT FORMAT (JSON only, no markdown):
{{
  "schema_version": "2.1",
  "entities": [
    {{
      "name": "Entity Name",
      "type": "person | org | artifact | event | abstract"
    }}
  ]
}}

IMPORTANT:
- Be thorough - scan the entire document
- Include entities that are mentioned even briefly
- Entity names should be the exact names used in the document
- Do NOT include context in this phase
"""

CONTEXT_PROMPT = """You are writing a detailed context paragraph for a wiki entity.

ENTITY: {entity_name}
TYPE: {entity_type}

SOURCE CONTENT:
{markdown_content}

OTHER ENTITIES IN THIS DOCUMENT (for cross-references):
{other_entities_json}

TASK:
Write ONE detailed context paragraph (100-200 Chinese characters) that includes:
- 定义: What is this entity?
- 作用: What does it do in this source document?
- 关键细节: Important characteristics, features, or contributions
- 关系: How does it relate to other entities mentioned?


OUTPUT FORMAT (JSON only, no markdown):
{{
  "name": "{entity_name}",
  "context": "100-200字详细描述，包含定义、作用、细节、关系"
}}

IMPORTANT:
- Focus only on this entity's role in THIS document
- Do NOT use [[Entity Name]] format - just write plain entity names
- Wiki links will be added automatically after extraction
- Be specific and detailed - not generic descriptions
"""


# ============================================================================
# Slugify Helper
# ============================================================================

def slugify(name: str) -> str:
    """Use original name as slug, preserving all characters."""
    # Remove only characters that are invalid for filenames: / \ : * ? " < > |
    slug = re.sub(r'[/\\:*?"<>|]', '', name)
    # Max 60 chars
    return slug[:60] if len(slug) > 60 else slug


# ============================================================================
# Wiki Link Conversion
# ============================================================================

def convert_to_wiki_links(text: str, entity_names: list[str]) -> str:
    """
    Convert entity names in text to Wiki Links.

    Matches by length descending to avoid partial matches.
    e.g., "MemoRAG" should match before "RAG"

    Skips text that is already inside [[...]] brackets.

    Args:
        text: Original text to convert
        entity_names: List of entity names to match

    Returns:
        Text with [[Entity Name]] wiki links
    """
    if not entity_names:
        return text

    # Sort by length descending for proper matching
    sorted_names = sorted(entity_names, key=len, reverse=True)

    result = text
    for name in sorted_names:
        if not name:
            continue

        # Find all positions of [[...]] brackets to skip
        bracket_ranges = []
        for match in re.finditer(r'\[\[[^\]]*\]\]', result):
            bracket_ranges.append((match.start(), match.end()))

        def is_inside_bracket(pos):
            for start, end in bracket_ranges:
                if start <= pos < end:
                    return True
            return False

        # Case-insensitive matching
        pattern = re.compile(re.escape(name), re.IGNORECASE)

        # Build new string, skipping matches inside brackets
        new_result = []
        last_end = 0
        for match in pattern.finditer(result):
            if not is_inside_bracket(match.start()):
                new_result.append(result[last_end:match.start()])
                new_result.append(f'[[{name}]]')
                last_end = match.end()

        new_result.append(result[last_end:])
        result = ''.join(new_result)

        # Update bracket ranges for next iteration
        bracket_ranges = []
        for match in re.finditer(r'\[\[[^\]]*\]\]', result):
            bracket_ranges.append((match.start(), match.end()))

    return result


# ============================================================================
# LLM API Calls
# ============================================================================

def call_discovery(
    client: OpenAI,
    content: str,
    source_type: str,
    existing_entities: list[dict],
    model: str = "gpt-4o-mini",
    timeout: int = 60
) -> dict:
    """
    Phase 1: Discover entities from content.

    Returns: {"entities": [{name, type}]} or {"error": ...}
    """
    prompt = DISCOVERY_PROMPT.format(
        source_type=source_type,
        markdown_content=content[:30000],
        existing_entities_json=json.dumps([e.get("name") for e in existing_entities], ensure_ascii=False)
    )

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are an entity discovery assistant. Output only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            timeout=timeout
        )

        result_text = response.choices[0].message.content
        result = json.loads(result_text)

        return result

    except json.JSONDecodeError as e:
        return {"error": f"JSON parse error: {str(e)}"}
    except Exception as e:
        return {"error": str(e)}


def call_context_generation(
    client: OpenAI,
    content: str,
    entity_name: str,
    entity_type: str,
    other_entities: list[str],
    model: str = "gpt-4o-mini",
    timeout: int = 60
) -> dict:
    """
    Phase 2: Generate context for a single entity.

    Returns: {"name": ..., "context": ...} or {"error": ...}
    """
    prompt = CONTEXT_PROMPT.format(
        entity_name=entity_name,
        entity_type=entity_type,
        markdown_content=content[:30000],
        other_entities_json=json.dumps(other_entities, ensure_ascii=False)
    )

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a knowledge context writer. Output only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            timeout=timeout
        )

        result_text = response.choices[0].message.content
        result = json.loads(result_text)

        return result

    except json.JSONDecodeError as e:
        return {"error": f"JSON parse error: {str(e)}"}
    except Exception as e:
        return {"error": str(e)}


# ============================================================================
# Entity Processing
# ============================================================================

def check_existing_entities(
    discovered_entities: list[dict],
    existing_entities: list[dict]
) -> list[dict]:
    """
    Check which discovered entities are new vs existing.

    Args:
        discovered_entities: [{name, type}] from Phase 1
        existing_entities: [{name, slug}] from cache.md

    Returns:
        [{name, type, is_new, existing_slug}]
    """
    existing_names = {e.get("name").lower(): e.get("slug") for e in existing_entities}

    result = []
    for entity in discovered_entities:
        name = entity.get("name", "")
        name_lower = name.lower()

        if name_lower in existing_names:
            result.append({
                "name": name,
                "type": entity.get("type", "abstract"),
                "is_new": False,
                "existing_slug": existing_names[name_lower]
            })
        else:
            result.append({
                "name": name,
                "type": entity.get("type", "abstract"),
                "is_new": True,
                "existing_slug": None
            })

    return result


# ============================================================================
# Main Extraction Function
# ============================================================================

def extract_two_phase(
    client: OpenAI,
    content: str,
    source_type: str,
    existing_entities: list[dict],
    model: str = "gpt-4o-mini",
    parallel_context: int = 5
) -> dict:
    """
    Two-phase extraction: discover entities, then generate contexts.

    Args:
        client: OpenAI client
        content: Document content
        source_type: Type of source (paper, article, video, etc.)
        existing_entities: List of existing entities from cache.md
        model: LLM model to use
        parallel_context: Max parallel context generation calls

    Returns:
        {"entities": [{name, type, context, is_new, existing_slug}]}
    """
    # Phase 1: Discovery
    discovery_result = call_discovery(client, content, source_type, existing_entities, model)

    if "error" in discovery_result:
        return discovery_result

    discovered_entities = discovery_result.get("entities", [])

    if not discovered_entities:
        return {"entities": [], "warning": "No entities discovered"}

    # Check existing entities
    entities_with_status = check_existing_entities(discovered_entities, existing_entities)

    # Phase 2: Generate context for each entity (parallel)
    entity_names = [e.get("name") for e in entities_with_status]

    contexts = {}
    with ThreadPoolExecutor(max_workers=parallel_context) as executor:
        futures = {
            executor.submit(
                call_context_generation,
                client, content,
                e.get("name"), e.get("type"),
                entity_names, model
            ): e.get("name")
            for e in entities_with_status
        }

        for future in as_completed(futures):
            entity_name = futures[future]
            try:
                context_result = future.result()
                if "error" not in context_result:
                    contexts[entity_name] = context_result.get("context", "")
                else:
                    contexts[entity_name] = f"[Context generation failed: {context_result.get('error')}]"
            except Exception as e:
                contexts[entity_name] = f"[Context generation error: {str(e)}]"

    # Combine results
    final_entities = []
    for entity in entities_with_status:
        entity["context"] = contexts.get(entity.get("name"), "")
        final_entities.append(entity)

    return {"entities": final_entities}
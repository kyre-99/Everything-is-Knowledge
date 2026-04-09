---
name: wiki-extract-agent
description: Extract entities from a Markdown source (DEPRECATED - use shared/bin/llm_extractor.py instead)
---

# Wiki Extract Agent

**DEPRECATED**: This skill is no longer used. Entity extraction is now handled by `shared/bin/llm_extractor.py`.

## Current Approach

Extraction is done via the shared LLM extractor module:

```python
from llm_extractor import extract_two_phase

result = extract_two_phase(
    client=OpenAI(),
    content=document_content,
    source_type="paper",
    existing_entities=[{"name": "RAG", "slug": "RAG"}],
)
```

See `shared/bin/llm_extractor.py` for the implementation.

## Two-Phase Extraction

1. **Phase 1: Discovery** - Identify all entities (name, type)
2. **Phase 2: Context** - Generate detailed context for each entity (parallel)

## Why Changed

- Old approach: Single prompt generating all entities and contexts
- Problem: Information loss, entities could be missed
- New approach: Two phases focus on different tasks
  - Phase 1: "Find who" - thorough entity discovery
  - Phase 2: "Describe who" - detailed context for each entity
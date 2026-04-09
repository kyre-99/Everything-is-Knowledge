---
name: wiki-ingest-llm
description: Ingest sources into the wiki using external LLM extraction (faster batch processing). Fully automated - fetches, extracts, and writes wiki pages in one command.
---

# Wiki Ingest LLM Skill

Ingest one or more sources into the wiki using external OpenAI LLM calls for extraction. Fully automated pipeline - fetches sources, extracts entities/concepts, and writes all wiki pages.

## Usage

```
/wiki-ingest-llm <source>
/wiki-ingest-llm raw/paper.pdf
/wiki-ingest-llm https://example.com/article
/wiki-ingest-llm raw/article.md

# Batch mode
/wiki-ingest-llm raw/paper1.pdf raw/paper2.pdf https://example.com
/wiki-ingest-llm raw/*.pdf --parallel 5

# JSON only (skip wiki writing)
/wiki-ingest-llm raw/paper.pdf --no-write
```

## Architecture

```
/wiki-ingest-llm workflow:
|
|-- [CLI] Python: wiki_ingest_llm.py
|   |-- Parse CLI args (sources, --parallel, --model, --write)
|   |-- Load wiki/index.md (existing entities/concepts)
|   |-- Load OpenAI config from ~/.wiki-config.json
|   |-- ThreadPoolExecutor (max 10 workers)
|   |   |-- Detect source type (PDF/URL/Video/Markdown)
|   |   |-- Fetch source (pdf_reader/web_fetcher/bilibili_fetcher)
|   |   |-- Call OpenAI API for extraction
|   |   |-- Quality check → retry with gpt-4o if needed
|   |-- Write wiki pages:
|   |   |-- wiki/sources/{slug}.md
|   |   |-- wiki/entities/{slug}.md (new or update)
|   |   |-- wiki/concepts/{slug}.md (new or update)
|   |   |-- wiki/index.md (append entries)
|   |   |-- wiki/log.md (append entry)
|   |-- Output JSON: {"results": [...], "errors": [...]}
|
|-- [MAIN] Report summary to user
```

## Workflow

The skill runs a single Python CLI command that handles everything:

```bash
uv run python .claude/skills/wiki-ingest-llm/bin/wiki_ingest_llm.py <sources>
```

### What the CLI does

1. **Load config** - Read OpenAI API key from `~/.wiki-config.json` or env vars
2. **Load existing wiki** - Parse `wiki/index.md` for entity/concept matching
3. **Fetch sources** - PDF/URL/Video/Markdown detection and fetching (parallel)
4. **Extract** - Call OpenAI API (gpt-4o-mini default, gpt-4o fallback for low quality)
5. **Write wiki pages** - Create source, entity, concept pages automatically
6. **Update index & log** - Append entries to `wiki/index.md` and `wiki/log.md`
7. **Output JSON** - Results and errors to stdout

### CLI Flags

| Flag | Default | Description |
|------|---------|-------------|
| `--parallel`, `-p` | 10 | Max parallel workers |
| `--model`, `-m` | gpt-4o-mini | LLM model for extraction |
| `--write`, `-w` | True | Write wiki pages |
| `--no-write` | - | Skip writing, only output JSON |
| `--index` | wiki/index.md | Path to wiki index |

### Example Output

```
Loaded 19 entities, 12 concepts from index.md
Processing 1 sources with 10 workers...
  [article] Processing: raw/test-article.md...

Writing wiki pages to wiki...
Created: sources/[1], entities/[4], concepts/[4]
Updated: entities/[0], concepts/[0]
{
  "results": [...],
  "errors": []
}
```

## Page Templates

### Source Page: `wiki/sources/{slug}.md`

```markdown
---
title: [Source Title]
date: YYYY-MM-DD
type: article
tags: []
status: draft
---

# [Source Title]

## Summary
[2-3 paragraph summary]

## Key Points
- [Point 1]
- [Point 2]

## Entities Mentioned
- [[Entity Name]] -- [context]

## Concepts
- [[Concept Name]] -- [application]

## Raw Source
[path or URL]
```

### Entity Page: `wiki/entities/{slug}.md`

```markdown
---
name: [Entity Name]
type: person | org | product | event
aliases: []
---

# [Entity Name]

## Overview
[context]

## Appearances in Sources
- [[Source Title]] -- [context]

## Related Entities
```

### Concept Page: `wiki/concepts/{slug}.md`

```markdown
---
name: [Concept Name]
type: idea | framework | pattern | methodology
---

# [Concept Name]

## Definition
[definition]

## Applications
- [[Source Title]] -- [application]

## Related Concepts
```

## Configuration

OpenAI API configuration is read from `~/.wiki-config.json` (via wiki_config module).

**Priority:** Environment variables > Config file > Defaults

| Source | Field | Notes |
|--------|-------|-------|
| `OPENAI_API_KEY` (env) | `openai_api_key` | Highest priority |
| `OPENAI_BASE_URL` (env) | `openai_base_url` | Override endpoint |
| `~/.wiki-config.json` | `openai_api_key`, `openai_base_url` | Set via /wiki-init or wiki_config.py |

**Setup:**
```bash
# Via wiki-init (interactive setup)
/wiki-init

# Or via CLI
uv run python .claude/shared/bin/wiki_config.py set openai_api_key your-key
uv run python .claude/shared/bin/wiki_config.py set openai_base_url https://api.openai.com/v1

# Or via environment variable
export OPENAI_API_KEY="your-key"
export OPENAI_BASE_URL="https://api.openai.com/v1"
```

## Quality Fallback

If extraction quality is low (entities empty OR summary <50 chars OR missing is_new), the CLI automatically retries with `gpt-4o`.

## Error Handling

- Missing OpenAI API key: Exit 1, show setup instructions
- Fetch failure: Continue batch, add to errors array
- LLM timeout: Retry 2x with 30s delay
- Rate limit: Exponential backoff
- All sources fail: Exit 1

## Output

Report to user:
```
Ingested: [Source Title] (or batch summary)
Created: sources/[slug].md, entities/[n], concepts/[n]
Updated: index.md, [other pages]
LLM: gpt-4o-mini (or gpt-4o fallback)
Errors: [count] (if any)
```
---
name: wiki-ingest
description: Ingest a source (PDF, URL, or markdown) into the knowledge wiki
---

# Wiki Ingest Skill

Ingest one or more sources into the wiki. Uses sub-agents for extraction to keep main context clean. Supports parallel batch ingestion.

## Usage

```
/wiki-ingest <source>
/wiki-ingest raw/paper.pdf
/wiki-ingest https://example.com/article
/wiki-ingest raw/article.md 


# Batch mode (multiple sources in parallel)
/wiki-ingest raw/paper1.pdf raw/paper2.pdf raw/paper3.pdf
/wiki-ingest https://a.com https://b.com https://c.com
/wiki-ingest raw/paper.pdf https://example.com/video
```

## Architecture

```
/wiki-ingest workflow:
|
|-- [MAIN] Parse source list (CLI args)
|   |
|   |-- [PYTHON] Fetchers run (parallel for batch)
|   |   |-- shared/bin/pdf_reader.py paper1.pdf -> paper1.md
|   |   |-- shared/bin/pdf_reader.py paper2.pdf -> paper2.md
|   |   |-- shared/bin/bilibili_fetcher.py URL -> video.md
|   |
|   |-- [MAIN] Read index.md (entity/concept registry)
|   |
|   |-- [MAIN] Dispatch sub-agents in parallel (max 5)
|   |   |
|   |   |-- [SUB-AGENT] Extract paper1.md
|   |   |   |-- Input: Markdown + source metadata + index.md
|   |   |   |-- Output: ExtractionResult JSON
|   |   |
|   |   |-- [SUB-AGENT] Extract paper2.md
|   |   |   |-- ...
|   |   |
|   |   |-- [SUB-AGENT] Extract video.md
|   |       |-- ...
|   |
|-- [MAIN] Collect all ExtractionResults
    |-- Merge entities (dedupe with index.md)
    |-- Merge concepts
    |-- Write wiki pages (sources, entities, concepts)
    |-- Update index.md, append log.md
```

## Workflow

### Step 1: Determine source types

For each source argument:
- Ends with `.pdf` -> Use `pdf_reader.py`
- Starts with `http://` or `https://`:
  - Contains `bilibili.com/video/` -> Use `bilibili_fetcher.py`
  - Otherwise -> Use `web_fetcher.py`
- Ends with `.md` or `.txt` -> Read directly and go to Step 3
- Otherwise -> Try as file path, error if not found

Track sources with their type: paper, article, video, book.

### Step 2: Fetch/parse sources

**For batch mode:** Run fetchers in parallel using multiple Bash calls in one message.

**All fetchers now auto-save parsed markdown to `raw/` folder:**
- `pdf_reader.py` → saves to `raw/{pdf-name}.md`
- `web_fetcher.py` → saves to `raw/{title-slug}.md`
- `bilibili_fetcher.py` → saves to `raw/{title-slug}.md`

This ensures:
1. Original parsed content is preserved for future re-processing
2. No need to re-parse PDFs (save MinerU API costs)
3. Raw markdown can be reviewed or edited before ingestion

**For PDF:**
```bash
uv run python .claude/shared/bin/pdf_reader.py "raw/paper.pdf" --pages 1-20
# Auto-saves to raw/paper.md (returns JSON with saved_to path)
```

**For Bilibili video:**
```bash
uv run python .claude/shared/bin/bilibili_fetcher.py "https://www.bilibili.com/video/BV1xx..."
# Auto-saves to raw/{title-slug}.md
```

**For URL:**
```bash
uv run python .claude/shared/bin/web_fetcher.py "https://example.com"
# Auto-saves to raw/{title-slug}.md
```

**For Markdown:**
```bash
# Read directly with Read tool (already in raw/)
```

**Skip auto-save (use --no-save flag):**
```bash
uv run python .claude/shared/bin/pdf_reader.py "raw/paper.pdf" --no-save
```

Store results in memory:
- `fetched_sources`: list of `{type, title, content, url, metadata, saved_to}`

### Step 3: Read index.md

Read `wiki/index.md` to get existing entities and concepts.

Parse into:
- `existing_entities`: list of `{name, slug, aliases}`
- `existing_concepts`: list of `{name, slug}`

If index.md doesn't exist, initialize empty lists.

### Step 4: Dispatch extraction sub-agents

**MAX_PARALLEL_SUBAGENTS = 5**

For each fetched source, prepare extraction input:
- `source_type`: paper | article | video | book
- `source_title`: title from fetcher
- `source_url`: URL or file path
- `markdown_content`: fetched content
- `existing_entities_json`: JSON string of existing entities
- `existing_concepts_json`: JSON string of existing concepts

**Single source:**
- Dispatch one sub-agent via Agent tool
- Wait for ExtractionResult

**Batch mode (<=5 sources):**
- Dispatch all sub-agents in one message (parallel)
- Collect all ExtractionResults

**Batch mode (>5 sources):**
- Split into batches of 5
- Process batches sequentially
- Report progress after each batch

Sub-agent invocation:
```
Agent(
  description: "Extract entities from {source_title}",
  prompt: wiki-extract-agent template with filled variables,
  subagent_type: "general-purpose"
)
```

### Step 5: Collect ExtractionResults

Parse JSON from each sub-agent result.

**Error handling:**
- If JSON parse fails: log error, continue with successful results
- If entity extraction fails but summary succeeds: save partial result, flag in log.md

Collect into:
- `extraction_results`: list of ExtractionResult objects

### Step 6: Merge entities and concepts

**Entity conflicts:**
- Same entity in multiple sources -> append both contexts
- First-encountered context becomes primary
- Subsequent contexts appended as "Also described in..."

**Concept conflicts:**
- Same concept, different definitions -> flag in log.md for review
- v1 does NOT auto-merge conflicting definitions

**Deduplication:**
- Entities marked `is_new: false` -> update existing page
- Entities marked `is_new: true` -> create new page
- Concepts same logic

### Step 7: Write wiki pages

For each ExtractionResult:

**Create source page:** `wiki/sources/{slug}.md`
```markdown
---
title: [Source Title]
date: YYYY-MM-DD
type: paper | article | video | book
tags: []
status: draft
---

# [Source Title]

## Summary
[2-3 paragraph summary from ExtractionResult]

## Key Points
- [Point 1]
- [Point 2]
- [Point 3]

## Entities Mentioned
- [[Entity Name]] -- [context from this source]

## Concepts
- [[Concept Name]] -- [how this concept appears]

## Raw Source
[path or URL]
```

**Create/update entity pages:** For each entity in ExtractionResult:
- If `is_new: true`: Create `wiki/entities/{slug}.md`
- If `is_new: false`: Update existing `wiki/entities/{existing_slug}.md`

**Entity page template (new):**
```markdown
---
name: [Entity Name]
type: person | org | product | event
aliases: []
---

# [Entity Name]

## Overview
[context from source]

## Appearances in Sources
- [[Source Title]] -- [context]

## Related Entities
- [[Other Entity]] -- [relationship]
```

**Entity page update (existing):**
Append to "Appearances in Sources" section:
```markdown
- [[Source Title]] -- [context]
```

**Create/update concept pages:** Same logic as entities, but for `wiki/concepts/`.

**Concept page template (new):**
```markdown
---
name: [Concept Name]
type: idea | framework | pattern | methodology
---

# [Concept Name]

## Definition
[definition from ExtractionResult]

## Applications
- [[Source Title]] -- [how applied]

## Related Concepts
- [[Other Concept]]
```

### Step 8: Update index.md

Append entries to `wiki/index.md`:
```markdown
## [YYYY-MM-DD HH:MM] Added sources/[slug].md
- Entities: [[Entity1]], [[Entity2]]
- Concepts: [[Concept1]]

## Entities
- [[New Entity]] -- [one-line summary]

## Sources
- [[Source Title]] -- [type, date] -- [one-line summary]
```

### Step 9: Append to log.md

Append to `wiki/log.md`:
```markdown
## [YYYY-MM-DD HH:MM] ingest | [Source Title] (or batch)
- Created: sources/[slug].md, entities/[n], concepts/[n]
- Updated: index.md, entities/[existing-entity].md
- Sub-agents: [count] extraction agents dispatched
- Status: [success | partial | failed]
- Notes: [any errors or flags]
```

## Error Handling

- **Source not found:** Report error, suggest checking path
- **API failure (PDF/URL):** Report error, suggest retry or manual download
- **Sub-agent timeout:** Log partial results, offer retry
- **Invalid JSON from sub-agent:** Parse what's available, log error, continue
- **Partial failure:** Report which pages created, which failed
- **Duplicate source:** Check index.md, ask user to "update existing" or "skip"

## File Naming (Slugs)

- Lowercase
- Replace spaces with hyphens
- Remove special characters (keep letters, numbers, Chinese, hyphens)
- Max 60 characters
- Chinese characters preserved: `注意力机制综述` -> `注意力机制综述.md`

## Output

Report to user:
```
Ingested: [Source Title] (or batch summary)
Created: sources/[slug].md, entities/[n], concepts/[n]
Updated: index.md, [other pages]
Sub-agents: [count] dispatched, [count] succeeded
```

## Sub-Agent Prompt Template

The extraction agent receives this prompt (from wiki-extract-agent/SKILL.md):

```
You are extracting knowledge from a {source_type} for a wiki.

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
{
  "schema_version": "1.0",
  "source": {"title": "...", "summary": "...", "key_points": [...], "slug": "..."},
  "entities": [...],
  "concepts": [...]
}

Entity matching rules (v1 - exact match only):
- Exact name match (case-insensitive) -> is_new: false, existing_slug: "matched-slug"
- Match against aliases in existing entities -> is_new: false, existing_slug: "matched-slug"
- Otherwise -> is_new: true, existing_slug: null
```
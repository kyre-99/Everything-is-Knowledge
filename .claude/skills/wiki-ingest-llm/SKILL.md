---
name: wiki-ingest-llm
description: Ingest sources into the wiki using external LLM extraction (faster batch processing). Fully automated - fetches, extracts, and writes wiki pages in one command.
---

# Wiki Ingest LLM Skill

Ingest one or more sources into the wiki using external OpenAI LLM calls for extraction. Fully automated pipeline - fetches sources, extracts entities, and writes all wiki pages.

## Usage

```
/wiki-ingest-llm <source>
/wiki-ingest-llm wiki/raw/paper.pdf
/wiki-ingest-llm https://example.com/article
/wiki-ingest-llm wiki/raw/article.md

# arXiv papers
/wiki-ingest-llm 2409.05591
/wiki-ingest-llm arxiv:2409.05591
/wiki-ingest-llm https://arxiv.org/abs/2409.05591

# Batch mode
/wiki-ingest-llm wiki/raw/paper1.pdf wiki/raw/paper2.pdf https://example.com
/wiki-ingest-llm wiki/raw/*.pdf --parallel 5
```

## Supported Source Types

| Type | Example | Fetcher | Output |
|------|---------|---------|--------|
| **PDF file** | `wiki/raw/paper.pdf` | pdf_reader.py | `wiki/raw/paper.md` |
| **arXiv paper** | `2409.05591` | DeepXiv API | `wiki/raw/arxiv-2409.05591.md` |
| **Web URL** | `https://example.com` | web_fetcher.py | `wiki/raw/{title}.md` |
| **Bilibili video** | `https://bilibili.com/video/...` | bilibili_fetcher.py | `wiki/raw/{title}.md` |
| **Markdown file** | `wiki/raw/article.md` | Direct read | - |

## Two-Phase Extraction

LLM extraction uses a two-phase approach for better quality:

```
Phase 1: Discovery
├── Input: document content + existing entities from cache.md
├── Output: list of entities [{name, type}]
└── Task: identify all entities (no context yet)

Phase 2: Context Generation (parallel)
├── Input: each entity + document content + other entity names
├── Output: detailed context (100-200 chars)
└── Task: write context with definition, role, details, relationships
```

**Why two phases?**
- Phase 1 focuses on "finding who" - less likely to miss entities
- Phase 2 focuses on "describing who" - each entity gets full attention
- Existing entities also get new facts from new documents

## Architecture

```
/wiki-ingest-llm workflow:
|
|-- [CLI] wiki_ingest_llm.py
|   |-- Parse CLI args
|   |-- Load cache.md (existing entities)
|   |-- Load OpenAI config
|   |
|   |-- [FETCH] Parallel (max 10)
|   |   |-- Detect source type
|   |   |-- Fetch content (pdf_reader/web_fetcher/deepxiv/bilibili)
|   |   |-- Save raw to wiki/raw/
|   |
|   |-- [EXTRACT] Call shared/bin/llm_extractor.py
|   |   |-- Phase 1: Discovery (1 API call)
|   |   |-- Check existing entities
|   |   |-- Phase 2: Context generation (N API calls, parallel)
|   |
|   |-- [WRITE]
|   |   |-- wiki/entities/{slug}.md (create or update)
|   |   |-- wiki/cache.md (append new entity names)
|   |   |-- wiki/log.md (append entry)
|   |
|   |-- Output JSON
```

## Shared Module

Core extraction logic is in `shared/bin/llm_extractor.py`:

```python
from llm_extractor import extract_two_phase, slugify, convert_to_wiki_links

result = extract_two_phase(
    client=OpenAI(),
    content=document_content,
    source_type="paper",
    existing_entities=[{"name": "RAG", "slug": "RAG"}],
    model="gpt-4o-mini",
)
# Returns: {"entities": [{name, type, context, is_new, existing_slug}]}
```

## Wiki Structure

```
wiki/
├── cache.md        # Entity names (one per line)
├── entities/       # Entity pages
│   ├── RAG.md
│   ├── Hongjin Qian.md
│   └── ...
├── raw/            # Original documents
│   ├── arxiv-2409.05591.md
│   ├── test-article.md
│   └── ...
└── log.md          # Operation log
```

## Entity Page Structure

Each fact includes its source directly:

```markdown
# RAG
type: artifact

## Facts

- [[RAG]] 是一种为大型语言模型提供外部知识库上下文的技术，通过检索相关文档增强生成的准确性和时效性，有效缓解模型幻觉问题 [[arxiv-2409.05591]]
- [[MemoRAG]] 在传统 [[RAG]] 基础上引入全局记忆模块... [[test-article]]
```

**Note:** No separate Source Documents section - source is attached to each fact.

## Entity Types (5 types)

| Type | Description | Examples |
|------|-------------|----------|
| `person` | 人物 | Andrew Ng, Geoffrey Hinton |
| `org` | 组织机构 | Google, Peking University |
| `artifact` | 人造物 | TensorFlow, PyTorch, MemoRAG |
| `event` | 事件 | Turing Award |
| `abstract` | 抽象概念 | Machine Learning, RAG |

## cache.md Format

```
Andrew Ng
Geoffrey Hinton
TensorFlow
PyTorch
```

Each line is one entity name (exact name, preserves case and spaces).

## CLI Flags

| Flag | Default | Description |
|------|---------|-------------|
| `--parallel`, `-p` | 10 | Max parallel workers |
| `--model`, `-m` | gpt-4o-mini | LLM model for extraction |
| `--cache` | wiki/cache.md | Path to wiki cache.md |
| `--no-write` | - | Skip writing, only output JSON |

## Configuration

OpenAI API configuration is read from `~/.wiki-config.json`.

**Priority:** Environment variables > Config file

| Source | Field | Notes |
|--------|-------|-------|
| `OPENAI_API_KEY` (env) | API key | Highest priority |
| `OPENAI_BASE_URL` (env) | Base URL | Override endpoint |
| `~/.wiki-config.json` | API config | Set via wiki_config.py |

## Wiki Link Conversion

After extraction, entity names in context are automatically converted to Wiki Links.

**Matching rule:** By entity name length descending.

Example: `MemoRAG` matches before `RAG` (longer first).

**Nesting prevention:** Text already inside `[[...]]` is skipped.
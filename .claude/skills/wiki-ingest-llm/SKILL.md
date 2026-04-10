---
name: wiki-ingest-llm
description: Ingest sources into the wiki using external LLM extraction (faster batch processing). Fully automated - fetches, extracts, and writes wiki pages in one command.
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
  - AskUserQuestion
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

## Workflow

### Step 1: Parse arguments

Determine source type from the input:
- **PDF file**: Path ending in `.pdf` → use `pdf_reader.py`
- **arXiv ID**: `2409.05591` or `arxiv:2409.05591` → use DeepXiv API
- **Web URL**: `https://...` → use `web_fetcher.py`
- **Bilibili video**: `https://bilibili.com/video/...` → use `bilibili_fetcher.py`
- **Markdown file**: Path ending in `.md` → read directly

### Step 2: Run the ingest script

```bash
# Single source
uv run python .claude/skills/wiki-ingest-llm/bin/wiki_ingest_llm.py <source>

# Multiple sources (batch)
uv run python .claude/skills/wiki-ingest-llm/bin/wiki_ingest_llm.py <source1> <source2> --parallel 5

# With specific model
uv run python .claude/skills/wiki-ingest-llm/bin/wiki_ingest_llm.py <source> --model gpt-4o
```

### Step 3: Parse output

The script outputs JSON with:
```json
{
  "results": [
    {
      "source": {"title": "...", "slug": "..."},
      "entities": [
        {"name": "...", "type": "...", "context": "...", "is_new": true}
      ]
    }
  ],
  "errors": []
}
```

### Step 4: Report results

Tell the user:
- Number of sources processed
- Entities created vs updated
- Any errors encountered

## CLI Flags

| Flag | Default | Description |
|------|---------|-------------|
| `--parallel`, `-p` | 10 | Max parallel workers |
| `--model`, `-m` | gpt-4o-mini | LLM model for extraction |
| `--cache` | wiki/cache.md | Path to wiki cache.md |
| `--no-write` | - | Skip writing, only output JSON |

## Supported Source Types

| Type | Example | Fetcher | Saved to wiki/raw |
|------|---------|---------|-------------------|
| **PDF file** | `wiki/raw/paper.pdf` | pdf_reader.py | `{title}.md` |
| **arXiv paper** | `2409.05591` | DeepXiv API | `arxiv-{id}.md` |
| **Web URL** | `https://example.com` | web_fetcher.py | `{title}.md` |
| **Bilibili video** | `https://bilibili.com/video/...` | bilibili_fetcher.py | `{title}.md` |
| **Markdown file** | `wiki/raw/article.md` | Direct read | `{filename}.md` |

All sources are automatically saved to `wiki/raw/` for cross-referencing.

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

## Wiki Structure

```
wiki/
├── cache.md        # Entity names (one per line)
├── entities/       # Entity pages with facts
├── raw/            # Source documents
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

## Entity Types (5 types)

| Type | Description | Examples |
|------|-------------|----------|
| `person` | 人物 | Andrew Ng, Geoffrey Hinton |
| `org` | 组织机构 | Google, Peking University |
| `artifact` | 人造物 | TensorFlow, PyTorch, MemoRAG |
| `event` | 事件 | Turing Award |
| `abstract` | 抽象概念 | Machine Learning, RAG |

## Configuration

OpenAI API configuration is read from `~/.wiki-config.json`.

**Priority:** Environment variables > Config file

| Source | Field | Notes |
|--------|-------|-------|
| `OPENAI_API_KEY` (env) | API key | Highest priority |
| `OPENAI_BASE_URL` (env) | Base URL | Override endpoint |
| `~/.wiki-config.json` | API config | Set via wiki_config.py |

## Error Handling

If the script fails:
1. Check if OpenAI API key is configured
2. Check if the source is accessible
3. Report the error to the user

```bash
# Check configuration
uv run python .claude/shared/bin/wiki_config.py status
```
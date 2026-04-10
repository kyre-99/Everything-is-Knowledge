---
name: wiki-ingest-llm
description: Ingest sources into the wiki using external LLM extraction (faster batch processing). Fully automated - fetches, extracts, and writes wiki pages in one command.
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
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


### Step 3: Report results

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
| **PDF file** | `wiki/raw/paper.pdf` | pdf_reader.py (精准API) | `{title}.md` |
| **arXiv paper** | `2409.05591` | DeepXiv API | `arxiv-{id}.md` |
| **Web URL** | `https://example.com` | web_fetcher.py | `{title}.md` |
| **Bilibili video** | `https://bilibili.com/video/...` | bilibili_fetcher.py | `{title}.md` |
| **Markdown file** | `wiki/raw/article.md` | Direct read | `{filename}.md` |

All sources are automatically saved to `wiki/raw/` for cross-referencing.

## Error Handling

If the script fails:
1. Check if Configuration is configured

```bash
# Check configuration
uv run python .claude/shared/bin/wiki_config.py status
```
2. if pdf is parsed failed, try agent mode
```bash
# Check pdf_parser code to try agent mode
v run python .claude/shared/bin//pdf_reader.py "small.pdf" --agent
```
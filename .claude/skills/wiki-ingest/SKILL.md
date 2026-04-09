---
name: wiki-ingest
description: Ingest a source (PDF, URL, or markdown) into the knowledge wiki
---

# Wiki Ingest Skill

Ingest one or more sources into the wiki. Simply calls `/wiki-ingest-llm` for automated extraction.

## Usage

```
/wiki-ingest <source>
/wiki-ingest wiki/raw/paper.pdf
/wiki-ingest https://example.com/article
/wiki-ingest wiki/raw/article.md

# arXiv papers
/wiki-ingest 2409.05591

# Batch mode
/wiki-ingest wiki/raw/paper1.pdf wiki/raw/paper2.pdf https://example.com
```

## How It Works

This skill is a simple wrapper that calls `/wiki-ingest-llm` with your sources.

See `/wiki-ingest-llm` for:
- Supported source types
- Two-phase extraction details
- Wiki structure
- CLI options

## Quick Reference

| Source Type | Example | Output |
|-------------|---------|--------|
| PDF | `wiki/raw/paper.pdf` | `wiki/raw/paper.md` + entities |
| arXiv | `2409.05591` | `wiki/raw/arxiv-2409.05591.md` + entities |
| URL | `https://example.com` | `wiki/raw/{title}.md` + entities |
| Markdown | `wiki/raw/article.md` | entities only |

## Alternative Skills

- **`/wiki-ingest-llm`** - Direct CLI access with more options (parallel, model selection)
- **`/wiki-ingest-paper`** - Search arXiv papers before ingesting
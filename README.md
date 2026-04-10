# Everything is Knowledge

[English](README.md) | [中文](README_CN.md)

> Turn your scattered knowledge into a structured, queryable wiki — powered by Claude Code and LLM extraction.

**Everything is Knowledge** is a knowledge management system that transforms documents, papers, URLs, and videos into a structured wiki with entities and cross-references. Use natural language queries to retrieve synthesized answers from your personal knowledge base.

## Table of Contents

- [Why This Project?](#why-this-project)
- [Features](#features)
- [Quick Start](#quick-start)
- [Prerequisites](#prerequisites)
- [Supported Source Types](#supported-source-types)
- [Usage Examples](#usage-examples)
- [Wiki Structure](#wiki-structure)
- [Entity Types](#entity-types)
- [Configuration](#configuration)
- [API Key Sources](#api-key-sources)
- [Two-Phase LLM Extraction](#two-phase-llm-extraction)
- [Project Structure](#project-structure)
- [Dependencies](#dependencies)

## Why This Project?

- ** fragmented knowledge** → Papers, articles, videos scattered across devices
- **Hard to recall** → "Which paper discussed GRPO?" — you know you read it, but where?
- **No synthesis** → Information stays isolated, never connected

This project solves these by:
- **Auto-extraction** → LLM identifies entities (people, concepts, methods) from sources
- **Cross-referencing** → Obsidian-style `[[Entity]]` links connect everything
- **Natural queries** → Ask questions, get synthesized answers with citations

## Features

| Skill | Description | Example |
|-------|-------------|---------|
| `/wiki-init` | Initialize wiki structure and configure API keys | `/wiki-init` |
| `/wiki-ingest-llm` | Ingest sources using LLM extraction (PDF, URL, arXiv, Bilibili) | `/wiki-ingest-llm wiki/raw/paper.pdf` |
| `/wiki-ingest-paper` | Search and ingest academic papers from arXiv/PMC | `/wiki-ingest-paper --search "RAG memory"` |
| `/wiki-query` | Query the wiki and get synthesized answers | `/wiki-query What is MemoRAG?` |
| `/wiki-lint` | Check wiki health (orphans, broken links) | `/wiki-lint` |
| `/wiki-disambiguate` | Merge duplicate entities and manage aliases | `/wiki-disambiguate` |

## Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/kyre-99/everything-is-knowledge.git
cd everything-is-knowledge

# 2. Run setup (installs dependencies, configures API keys)
./setup

# 3. Open Obsidian and select wiki/ as your vault

# 4. Start Claude Code
claude

# 5. Ingest your first source
> /wiki-ingest-llm https://arxiv.org/abs/2409.05591

# 6. Query the wiki
> /wiki-query What is MemoRAG?
```

## Prerequisites

Before running `./setup`, ensure these are installed:

| Tool | Website | Install Command |
|------|---------|-----------------|
| **Claude Code CLI** | [claude.ai/code](https://claude.ai/code) | `npm install -g @anthropic-ai/claude-code` |
| **Obsidian** | [obsidian.md](https://obsidian.md) | macOS: `brew install --cask obsidian` |
| **Python 3.12+** | [python.org](https://python.org) | System install or `brew install python` |

> **Note:** The setup script will install `uv` (Python package manager) and project dependencies automatically.

## Supported Source Types

| Type | Example | How it works |
|------|---------|--------------|
| **PDF files** | `wiki/raw/paper.pdf` | MinerU API → Markdown |
| **arXiv papers** | `2409.05591` | DeepXiv API → Markdown |
| **Web URLs** | `https://example.com/article` | Scrapling → Markdown |
| **Bilibili videos** | `https://bilibili.com/video/BV...` | Whisper → Transcript |
| **Markdown files** | `wiki/raw/article.md` | Direct read |

## Usage Examples

### Ingest Sources

```bash
# Single source
/wiki-ingest-llm wiki/raw/paper.pdf
/wiki-ingest-llm https://arxiv.org/abs/2409.05591
/wiki-ingest-llm https://bilibili.com/video/BV1vyDpBEESx

# Batch processing
/wiki-ingest-llm wiki/raw/*.pdf --parallel 5
/wiki-ingest-llm wiki/raw/paper1.pdf wiki/raw/paper2.pdf https://example.com

# Use different LLM model
/wiki-ingest-llm wiki/raw/paper.pdf --model gpt-4o
```

### Search & Ingest Papers

```bash
# Keyword search
/wiki-ingest-paper --search "agent memory" --limit 20

# Filter by category
/wiki-ingest-paper --search "RAG" --categories cs.CL,cs.AI

# Direct import by arXiv ID
/wiki-ingest-paper --arxiv 2409.05591 2409.05592

# Trending papers
/wiki-ingest-paper --trending --days 7
```

### Query the Wiki

```bash
/wiki-query What is RAG?
/wiki-query Which papers discuss GRPO?
/wiki-query How does MemoRAG differ from traditional RAG?
/wiki-query What organizations are working on agent memory?
```

Returns synthesized answers with citations:
```
## Answer

MemoRAG is a memory-augmented RAG framework that introduces a global memory
module to cache retrieved knowledge across queries...

## Sources
- [[arxiv-2409.05591]] — Introduced MemoRAG architecture
- [[RAG]] — Definition and traditional approach
- [[Hongjin Qian]] — Lead author of MemoRAG paper
```

### Check Wiki Health

```bash
/wiki-lint
```

Detects and reports:
- Orphan entities (no inbound links)
- Broken `[[...]]` cross-references
- Missing source documents
- Index inconsistencies

## Wiki Structure

```
wiki/
├── index.md              # Catalog (auto-updated)
├── cache.md              # Entity names cache
├── log.md                # Operation log
├── entities/             # Knowledge entities
│   ├── RAG.md
│   ├── MemoRAG.md
│   ├── Hongjin Qian.md
│   └── ...
└── raw/                  # Source documents
    ├── arxiv-2409.05591.md
    ├── test-article.md
    └── ...
```

### Entity Page Format

```markdown
# EntityName
type: person | org | artifact | event | abstract

## Facts

- [[RAG]] is a technique that provides external knowledge context to LLMs... [[arxiv-2409.05591]]
- [[MemoRAG]] builds on [[RAG]] by adding global memory module... [[test-article]]
```

Cross-references use Obsidian `[[Entity]]` syntax for navigation.

## Entity Types

| Type | Description | Examples |
|------|-------------|----------|
| `person` | Researchers, authors | Andrew Ng, Geoffrey Hinton |
| `org` | Organizations | Google DeepMind, Peking University |
| `artifact` | Tools, frameworks, datasets | TensorFlow, PyTorch, MemoRAG |
| `event` | Conferences, milestones | NeurIPS 2024, Turing Award |
| `abstract` | Concepts, methods, theories | RAG, Reinforcement Learning, GRPO |

## Configuration

API keys are stored in `~/.wiki-config.json`.

```bash
# Check current configuration
uv run python .claude/shared/bin/wiki_config.py status

# Set OpenAI API key (required for LLM extraction)
uv run python .claude/shared/bin/wiki_config.py set openai_api_key YOUR_KEY

# Set custom endpoint (optional, for proxies)
uv run python .claude/shared/bin/wiki_config.py set openai_base_url https://api.zhizengzheng.com/v1

# Set MinerU API key (optional, for PDF parsing)
uv run python .claude/shared/bin/wiki_config.py set mineru_api_key YOUR_KEY

# Set DeepXiv token (optional, auto-registers on first use)
uv run python .claude/shared/bin/wiki_config.py set deepxiv_token YOUR_TOKEN
```

### Priority Order

Environment variables > Config file > Defaults

| Variable | Config Field |
|----------|--------------|
| `OPENAI_API_KEY` | `openai_api_key` |
| `OPENAI_BASE_URL` | `openai_base_url` |
| `MINERU_API_KEY` | `mineru_api_key` |
| `DEEPXIV_TOKEN` | `deepxiv_token` |

## API Key Sources

| Service | Purpose | Get Key |
|---------|---------|---------|
| **OpenAI** | LLM extraction (required) | [platform.openai.com/api-keys](https://platform.openai.com/api-keys) |
| **MinerU** | PDF to Markdown (optional) | [mineru.net](https://mineru.net) |
| **DeepXiv** | arXiv search (optional) | Auto-registers, or [data.rag.ac.cn](https://data.rag.ac.cn/register) |

> **Tip:** DeepXiv free tier = 10,000 requests/day. First use auto-registers a token.

## Two-Phase LLM Extraction

For better extraction quality:

```
Phase 1: Discovery
├── Input: document + existing entity cache
├── Output: list of entity names + types
└── LLM identifies entities without generating context

Phase 2: Context Generation (parallel)
├── Input: each entity + document + other entity names
├── Output: detailed context (100-200 chars per entity)
└── LLM writes facts with source citations
```

This separation improves accuracy and enables parallel processing.

## Project Structure

```
everything-is-knowledge/
├── .claude/
│   ├── CLAUDE.md                   # Project instructions
│   ├── skills/
│   │   ├── wiki-init/
│   │   ├── wiki-ingest-llm/
│   │   ├── wiki-ingest-paper/
│   │   ├── wiki-query/
│   │   ├── wiki-lint/
│   │   └── wiki-disambiguate/
│   └── shared/bin/
│       ├── wiki_config.py          # Configuration CLI
│       ├── pdf_reader.py           # MinerU PDF parser
│       ├── web_fetcher.py          # Scrapling web fetcher
│       ├── bilibili_fetcher.py     # Bilibili transcript fetcher
│       ├── deepxiv_fetcher.py      # DeepXiv paper fetcher
│       └── llm_extractor.py        # OpenAI extraction
├── wiki/                           # Your knowledge base
├── setup                           # One-click setup script
├── pyproject.toml                  # Python dependencies
└── README.md
```

## Dependencies

- **uv** — Fast Python package manager
- **Scrapling** — Web scraping with anti-bot stealth
- **MinerU** — PDF parsing to Markdown
- **OpenAI** — LLM extraction (gpt-4o-mini default)
- **DeepXiv SDK** — arXiv paper search
- **yt-dlp + Whisper** — Bilibili video transcription

## Contributing

PRs welcome! Key areas:
- Additional source types (YouTube, Twitter, podcasts)
- Better entity disambiguation
- Query optimization

## License

MIT

---

**Made with Claude Code** — [claude.ai/code](https://claude.ai/code)
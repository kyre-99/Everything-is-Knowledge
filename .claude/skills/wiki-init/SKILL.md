---
name: wiki-init
description: Initialize the Everything is Knowledge wiki. Creates directories, configures API keys, and sets up PDF parsing options. Run once to set up a new wiki.
allowed-tools:
  - Bash
  - Read
  - Write
---

# Wiki Init Skill

Initialize the wiki with one command. Checks and configures the environment.

## Usage

```
/wiki-init
```

## Workflow

### Step 1: Check current configuration

```bash
uv run python .claude/shared/bin/wiki_config.py status
```

This shows:
- Config file location
- PDF Parser setting
- MinerU API Key status
- OpenAI API Key status
- OpenAI Base URL

### Step 2: Configure API keys (if needed)

If API keys are not set, prompt the user:

**Ask the user:** "Do you want to configure API keys now?"

### API Keys

| Key | Required? | How to Get |
|-----|-----------|------------|
| **OpenAI API Key** | Required for LLM extraction | https://platform.openai.com/api-keys |
| **MinerU API Key** | Optional (PDF parsing) | https://mineru.net |
| **DeepXiv Token** | Optional (paper search) | Auto-registers on first use |

### DeepXiv Token (Optional)

DeepXiv is used for paper search (`/wiki-ingest-paper`). Token is optional:

- **Auto-registration**: First use will automatically register a free token
- **Free tier**: 10,000 requests/day (sufficient for most users)
- **Higher limits**: Visit https://data.rag.ac.cn/register and contact tommy@chien.io

Configure if desired (can skip):
```bash
# Set DeepXiv token (optional - auto-registers on first use)
uv run python .claude/shared/bin/wiki_config.py set deepxiv_token YOUR_TOKEN
# Or via environment: export DEEPXIV_TOKEN=YOUR_TOKEN
```

Configure required keys:
```bash
# Set OpenAI API key (required for LLM extraction)
uv run python .claude/shared/bin/wiki_config.py set openai_api_key YOUR_KEY

# Set MinerU API key (optional, for PDF parsing)
uv run python .claude/shared/bin/wiki_config.py set mineru_api_key YOUR_KEY
```

### Step 3: Create wiki directory structure

```bash
mkdir -p wiki/entities wiki/raw
touch wiki/cache.md wiki/log.md
```

### Step 4: Verify setup

```bash
uv run python .claude/shared/bin/wiki_config.py status
ls -la wiki/
```

## Wiki Directory Structure

```
wiki/
├── cache.md        # Entity names (one per line)
├── entities/       # Entity pages
│   ├── RAG.md
│   ├── Hongjin Qian.md
│   └── ...
├── raw/            # Source documents
│   ├── arxiv-2409.05591.md
│   ├── test-article.md
│   └── ...
└── log.md          # Operation log
```

## Config File

Configuration is stored in `~/.wiki-config.json`.

**Priority:** Environment variables > Config file > Defaults

| Environment Variable | Config Field |
|---------------------|--------------|
| `MINERU_API_KEY` | `mineru_api_key` |
| `OPENAI_API_KEY` | `openai_api_key` |
| `OPENAI_BASE_URL` | `openai_base_url` |
| `DEEPXIV_TOKEN` | `deepxiv_token` |

## Completion

After setup, tell the user:

"The wiki is ready. You can now use:"
- `/wiki-ingest-llm <source>` - Ingest PDFs, URLs, or arXiv papers
- `/wiki-ingest-paper --search "query"` - Search and ingest academic papers
- `/wiki-query <question>` - Query the knowledge wiki
- `/wiki-lint` - Check wiki health
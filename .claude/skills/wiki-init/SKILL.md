---
name: wiki-init
description: Initialize the Everything is Knowledge wiki. Creates directories, configures API keys, and sets up PDF parsing options. Run once to set up a new wiki.
---

# Wiki Init Skill

Initialize the wiki with one command. Runs the interactive setup script.

## Usage

```
/wiki-init
```

## Workflow

### Step 1: Run setup script

```bash
./setup
```

The setup script handles everything interactively:
- ✓ Check Python version (3.12+)
- ✓ Install uv package manager
- ✓ Install Python dependencies
- ✓ Create wiki directory structure
- ✓ Configure MinerU API key (PDF parsing)
- ✓ Configure OpenAI API key (LLM extraction)
- ✓ Show final configuration status

### Step 2: Done

The user now has:
- `wiki/entities/` - Entity pages
- `wiki/raw/` - Source documents
- `wiki/cache.md` - Entity name catalog
- `wiki/log.md` - Operation log
- API keys saved to `~/.wiki-config.json`

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

**Simplified structure:** Only entities, no separate sources/concepts pages.

## Config CLI

After setup, use wiki_config.py to view/update config:

```bash
# View current config
uv run python .claude/shared/bin/wiki_config.py status

# Update a key
uv run python .claude/shared/bin/wiki_config.py set mineru_api_key your-key
uv run python .claude/shared/bin/wiki_config.py set openai_api_key your-key
```

## Environment Variables

Override config file with environment variables:

| Variable | Config Field |
|----------|-------------|
| `MINERU_API_KEY` | `mineru_api_key` |
| `OPENAI_API_KEY` | `openai_api_key` |
| `OPENAI_BASE_URL` | `openai_base_url` |
| `DEEPXIV_TOKEN` | `deepxiv_token` |

## Files Created

| File | Purpose |
|------|---------|
| `wiki/cache.md` | Entity name catalog (one per line) |
| `wiki/log.md` | Append-only operation log |
| `wiki/entities/` | Entity pages (person, org, artifact, event, abstract) |
| `wiki/raw/` | Source documents (PDFs, URLs, videos parsed to markdown) |
| `~/.wiki-config.json` | Configuration file |
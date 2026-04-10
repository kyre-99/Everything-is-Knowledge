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
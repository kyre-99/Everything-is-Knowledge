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
- ✓ Configure OpenAI API key (video transcription)
- ✓ Show final configuration status

### Step 2: Done

The user now has:
- `wiki/entities/`, `wiki/concepts/`, `wiki/sources/`, `wiki/synthesis/`
- `raw/` directory for source files
- `wiki/index.md` and `wiki/log.md`
- API keys saved to `~/.wiki-config.json`

## Config CLI

After setup, use wiki_config.py to view/update config:

```bash
# View current config
uv run python .claude/skills/wiki-ingest/bin/wiki_config.py status

# Update a key
uv run python .claude/skills/wiki-ingest/bin/wiki_config.py set mineru_api_key your-key
uv run python .claude/skills/wiki-ingest/bin/wiki_config.py set openai_api_key your-key
```

## Environment Variables

Override config file with environment variables:

| Variable | Config Field |
|----------|-------------|
| `MINERU_API_KEY` | `mineru_api_key` |
| `OPENAI_API_KEY` | `openai_api_key` |
| `OPENAI_BASE_URL` | `openai_base_url` |

## Files Created

| File | Purpose |
|------|---------|
| `wiki/index.md` | Catalog of all sources, entities, concepts |
| `wiki/log.md` | Append-only operation log |
| `wiki/entities/` | Entity pages |
| `wiki/concepts/` | Concept pages |
| `wiki/sources/` | Source pages |
| `wiki/synthesis/` | Synthesis pages |
| `raw/` | Source files before processing |
| `~/.wiki-config.json` | Configuration file |
---
name: wiki-ingest-paper
description: Search and ingest academic papers from arXiv/PMC into the wiki. Supports keyword search, trending papers, and direct arXiv ID lookup.
allowed-tools:
  - Bash
  - Read
  - Write
  - AskUserQuestion
---

# Wiki Ingest Paper Skill

Search for academic papers and ingest them into the wiki with full extraction pipeline.

## Usage

```
# Search and interactively select papers
/wiki-ingest-paper --search "agent memory"
/wiki-ingest-paper --search "RAG" --categories cs.CL,cs.AI --limit 20

# Direct import by arXiv ID
/wiki-ingest-paper --arxiv 2409.05591
/wiki-ingest-paper --arxiv 2409.05591 2409.05592 2409.05593

# Trending papers
/wiki-ingest-paper --trending --days 7 --limit 20
```

## Workflow

### Step 1: Parse arguments

Determine the action:
- `--search <query>` → Search papers, show results, let user select
- `--arxiv <id>` → Direct import by arXiv ID
- `--trending` → Show trending papers, let user select

### Step 2: Run the ingest script

```bash
# Search for papers
uv run python .claude/skills/wiki-ingest-paper/bin/wiki_ingest_paper.py --search "agent memory"

# Direct import
uv run python .claude/skills/wiki-ingest-paper/bin/wiki_ingest_paper.py --arxiv 2409.05591

# Trending papers
uv run python .claude/skills/wiki-ingest-paper/bin/wiki_ingest_paper.py --trending --days 7
```

### Step 3: Interactive selection (for search/trending)

The script will display results and prompt for selection:
```
1. Paper Title Here
   arXiv: 2409.05591 | Citations: 50
   Abstract preview...

Enter paper numbers to ingest (e.g., '1,3,5' or '1-3' or 'all'):
```

### Step 4: Report results

After ingestion, report:
- Number of papers ingested
- Entities created
- Any errors

## CLI Flags

| Flag | Description |
|------|-------------|
| `--search`, `-s` | Search query for papers |
| `--arxiv`, `-a` | arXiv paper ID(s) to ingest directly |
| `--trending`, `-t` | Get trending papers |
| `--limit`, `-l` | Number of results (default: 10, max: 100) |
| `--categories`, `-c` | Filter by arXiv categories (comma-separated) |
| `--min-citations` | Minimum citation count |
| `--days` | Trending days (7, 14, 30) |
| `--model`, `-m` | LLM model for extraction (default: gpt-4o-mini) |

## Common arXiv Categories

- `cs.AI` - 人工智能
- `cs.CL` - 计算与语言 (NLP)
- `cs.CV` - 计算机视觉
- `cs.LG` - 机器学习
- `cs.RO` - 机器人
- `cs.SE` - 软件工程
- `stat.ML` - 机器学习 (统计)

## Example Output

```
📚 Ingesting 3 papers...

[1/3] Processing arXiv:2409.05591...
  ✅ MemoRAG: 15 entities

[2/3] Processing arXiv:2409.05592...
  ✅ Another Paper: 8 entities

📝 Writing wiki pages...
Created: entities[23]
Updated: cache.md
```

## Wiki Output

Papers are saved to:
- **Raw document**: `wiki/raw/arxiv-{id}.md` - Full paper markdown
- **Entity pages**: `wiki/entities/{name}.md` - Authors, methods, frameworks

## Two-Phase Extraction

Uses shared LLM extractor (`shared/bin/llm_extractor.py`):

1. **Phase 1: Discovery** - Find all entities (authors, methods, frameworks, concepts)
2. **Phase 2: Context** - Generate detailed context for each entity (parallel)

## Configuration

DeepXiv token is optional (auto-registers on first use, 10,000 requests/day free tier).

```bash
# Check configuration
uv run python .claude/shared/bin/wiki_config.py status

# Set OpenAI API key (required for LLM extraction)
uv run python .claude/shared/bin/wiki_config.py set openai_api_key YOUR_KEY

# Set DeepXiv token (optional - skip for auto-registration)
uv run python .claude/shared/bin/wiki_config.py set deepxiv_token YOUR_TOKEN
# Or: export DEEPXIV_TOKEN=YOUR_TOKEN

# For higher DeepXiv limits: https://data.rag.ac.cn/register
```

### Token Priority

DeepXiv token is fetched in order:
1. `~/.wiki-config.json` (`deepxiv_token` field)
2. Environment variable `DEEPXIV_TOKEN`
3. `~/.env` (where deepxiv CLI stores auto-registered tokens)
4. Auto-registration on first use (if none found)

## Error Handling

If the script fails:
1. Check if OpenAI API key is configured
2. Check if deepxiv-sdk is installed (`pip install deepxiv-sdk`)
3. Report the error to the user
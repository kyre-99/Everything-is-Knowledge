---
name: wiki-ingest-paper
description: Search and ingest academic papers from arXiv/PMC into the wiki. Supports keyword search, trending papers, and direct arXiv ID lookup.
---

# Wiki Ingest Paper Skill

Search for academic papers and ingest them into the wiki. Uses DeepXiv API for paper discovery and content retrieval.

## Usage

```
/wiki-ingest-paper --search "agent memory"
/wiki-ingest-paper --search "transformer" --limit 10 --categories cs.AI,cs.CL
/wiki-ingest-paper --trending --days 7
/wiki-ingest-paper --arxiv 2409.05591
/wiki-ingest-paper --pmc PMC544940
```

## Workflow

### Step 1: Paper Discovery

Use DeepXiv to find relevant papers:

**Search by keyword:**
```bash
uv run python .claude/shared/bin/deepxiv_fetcher.py --search "agent memory" --limit 10
```

**Get trending papers:**
```bash
uv run python .claude/shared/bin/deepxiv_fetcher.py --trending --days 7 --limit 20
```

**Filter options:**
- `--categories cs.AI,cs.CL` - Filter by arXiv categories
- `--min-citations 50` - Minimum citation count
- `--date-from 2024-01-01 --date-to 2024-12-31` - Date range

### Step 2: Paper Selection

Present search results to user:

```
Found 10 papers for "agent memory":

1. MemGPT: Towards LLMs as Operating Systems (arXiv:2310.08560)
   Citations: 156 | 2023-10-12
   Abstract: This paper introduces MemGPT, a system that...

2. Generative Agents: Interactive Simulacra of Human Behavior (arXiv:2304.03442)
   Citations: 289 | 2023-04-07
   ...

Which papers would you like to ingest? (Enter numbers or arXiv IDs)
```

### Step 3: Fetch Full Content

For each selected paper, fetch the full markdown content:

```bash
# Full paper
uv run python .claude/shared/bin/deepxiv_fetcher.py --arxiv 2409.05591

# Or preview first (faster)
uv run python .claude/shared/bin/deepxiv_fetcher.py --arxiv 2409.05591 --preview

# Or specific section
uv run python .claude/shared/bin/deepxiv_fetcher.py --arxiv 2409.05591 --section Introduction
```

The fetcher automatically saves to `raw/` directory:
- `raw/{paper-title}.md` - Markdown content
- Returns `saved_to` path in JSON

### Step 4: Extract Knowledge

Use existing extraction pipeline:

**Option A: Use wiki-ingest-llm (recommended for batch)**
```bash
uv run python .claude/skills/wiki-ingest-llm/bin/wiki_ingest_llm.py raw/paper1.md raw/paper2.md
```

**Option B: Use wiki-ingest (sub-agent extraction)**
Invoke `/wiki-ingest raw/paper.md` for each paper.

### Step 5: Report Results

Summarize what was ingested:

```
Ingested 3 papers:
- MemGPT (arXiv:2310.08560) → sources/memgpt.md, 5 entities, 3 concepts
- Generative Agents (arXiv:2304.03442) → sources/generative-agents.md, 4 entities, 2 concepts
- Attention Is All You Need (arXiv:1706.03762) → sources/attention-is-all-you-need.md, 6 entities, 4 concepts

Total: 3 sources, 15 entities, 9 concepts created
```

## Paper Content Modes

| Mode | Flag | Content | Use Case |
|------|------|---------|----------|
| Full | (default) | Complete markdown | Full analysis |
| Brief | `--brief` | Title, TLDR, keywords, citations | Quick evaluation |
| Preview | `--preview` | First 10k characters | Quick scan |
| Section | `--section NAME` | Specific section only | Targeted reading |
| Head | `--head` | Metadata + structure | Overview |

## Search Parameters

| Parameter | Example | Description |
|-----------|---------|-------------|
| `--search` | "agent memory" | Search query |
| `--limit` | 20 | Max results (default: 10, max: 100) |
| `--categories` | cs.AI,cs.CL | Filter by arXiv categories |
| `--min-citations` | 50 | Minimum citation count |
| `--date-from` | 2024-01-01 | Publication date from |
| `--date-to` | 2024-12-31 | Publication date to |

## Common arXiv Categories

- `cs.AI` - Artificial Intelligence
- `cs.CL` - Computation and Language (NLP)
- `cs.CV` - Computer Vision
- `cs.LG` - Machine Learning
- `cs.RO` - Robotics
- `cs.SE` - Software Engineering
- `stat.ML` - Machine Learning (Statistics)

## Configuration

DeepXiv token is auto-registered on first use. To configure manually:

```bash
# Via environment variable
export DEEPXIV_TOKEN="your-token"

# Or run any deepxiv command (auto-registers)
uv run python .claude/shared/bin/deepxiv_fetcher.py --search "test"
```

## Error Handling

- **No token**: Auto-register a free token
- **Rate limit**: Daily limit 10,000 requests. Wait or request higher limit at https://data.rag.ac.cn/register
- **Paper not found**: Check arXiv ID format (e.g., `2409.05591`)
- **Empty content**: Paper may be too new or not parsed yet

## Examples

### Example 1: Research a new topic

```
User: I want to learn about RAG systems

/wiki-ingest-paper --search "retrieval augmented generation" --limit 10 --categories cs.CL,cs.AI

[Present results, user selects papers 1, 3, 5]

[Fetch and ingest selected papers]
```

### Example 2: Track recent trends

```
User: What are the hot papers this week?

/wiki-ingest-paper --trending --days 7 --limit 20

[Present trending papers with social metrics]

User: Ingest the top 5

[Fetch and ingest top 5 papers]
```

### Example 3: Direct paper lookup

```
User: Add paper 2310.08560 to the wiki

/wiki-ingest-paper --arxiv 2310.08560

[Fetch full paper, save to raw/, then ingest]
```

## Integration with Wiki

Papers are ingested as:
- **Source page**: `wiki/sources/{paper-title}.md`
- **Entities**: Authors, datasets, methods mentioned
- **Concepts**: Key ideas, frameworks, techniques

Cross-references use Obsidian syntax: `[[Attention Mechanism]]`, `[[Transformer]]`
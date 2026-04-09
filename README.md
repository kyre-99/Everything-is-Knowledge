# Everything is Knowledge

A knowledge management system for Claude Code that transforms your wiki into a structured knowledge graph with entities, concepts, and cross-references.

## Features

- **Wiki Ingest** (`/wiki-ingest`) — Import PDFs, URLs, or markdown into your knowledge base
- **Wiki Query** (`/wiki-query`) — Search and synthesize answers from your wiki
- **Wiki Lint** (`/wiki-lint`) — Health check for orphan pages, broken links, and missing cross-references

## Quick Start

```bash
# Clone and setup
git clone https://github.com/yourname/everything-is-knowledge.git
cd everything-is-knowledge
./setup

# Start using with Claude Code
claude
> /wiki-ingest raw/paper.pdf
> /wiki-ingest https://example.com/article
> /wiki-query What is RAG?
```

## Installation

### Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) package manager
- Claude Code CLI

### Manual Setup

```bash
# Install uv if not present
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync

# Configure MinerU API key (optional, for PDF parsing)
echo "your-api-key" > ~/.mineru_api_key
# or set environment variable:
export MINERU_API_KEY="your-api-key"
```

## Project Structure

```
everything-is-knowledge/
├── .claude/
│   ├── CLAUDE.md              # Project instructions
│   └── skills/wiki/
│       ├── bin/
│       │   ├── pdf_reader.py  # MinerU PDF parser
│       │   └── web_fetcher.py # Scrapling web fetcher
│       ├── wiki-ingest/SKILL.md
│       ├── wiki-query/SKILL.md
│       └── wiki-lint/SKILL.md
├── wiki/
│   ├── index.md               # Catalog of all pages
│   ├── log.md                 # Append-only activity log
│   ├── entities/              # People, orgs, products
│   ├── concepts/              # Ideas, frameworks, patterns
│   ├── sources/               # Papers, articles, videos
│   └── synthesis/             # Combined answers
├── raw/                       # Place source files here
├── setup                      # Quick deployment script
└── pyproject.toml
```

## Usage

### Ingest a Source

```
/wiki-ingest raw/paper.pdf
/wiki-ingest https://arxiv.org/abs/2301.07041
/wiki-ingest raw/article.md
```

The skill will:
1. Parse the source (PDF via MinerU, URL via Scrapling)
2. Extract key entities and concepts
3. Create wiki pages with Obsidian-style cross-references
4. Update the index automatically

### Query the Wiki

```
/wiki-query What is multi-hop reasoning?
/wiki-query Which papers discuss GRPO?
/wiki-query How does CP-Search work?
```

Returns synthesized answers with source citations.

### Check Wiki Health

```
/wiki-lint
```

Detects:
- Orphan pages (no inbound links)
- Missing cross-references
- Index discrepancies
- Broken `[[...]]` links

## Wiki Conventions

- **Cross-references**: Use Obsidian `[[Page Title]]` syntax
- **Frontmatter**: All pages have YAML metadata
- **Chinese support**: UTF-8 filenames preserved
- **Index-first**: Always read `wiki/index.md` before operations

### Entity Template

```markdown
---
name: [Entity Name]
type: person | org | product | event
aliases: []
---

# [Entity Name]

## Overview
[Description]

## Key Attributes
- attribute: value

## Appearances in Sources
- [[Source Title]] — context

## Related Entities
- [[Other Entity]] — relationship
```

### Concept Template

```markdown
---
name: [Concept Name]
type: idea | framework | pattern | methodology
---

# [Concept Name]

## Definition
[Description]

## Key Principles
- Principle 1

## Applications
- [[Source Title]] — how applied

## Related Concepts
- [[Other Concept]]
```

## API Keys

### MinerU (PDF Parsing)

Register at [mineru.net](https://mineru.net) to get an API key.

```bash
# Save to file
echo "your-api-key" > ~/.mineru_api_key

# Or environment variable
export MINERU_API_KEY="your-api-key"
```

## Dependencies

- **Scrapling** — Web scraping with anti-bot stealth
- **MinerU API** — PDF parsing to Markdown
- **markdownify** — HTML to Markdown conversion

## License

MIT
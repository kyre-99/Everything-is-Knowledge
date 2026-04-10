---
name: wiki-query
description: Query the knowledge wiki and get synthesized answers
allowed-tools:
  - Read
  - Bash
---

# Wiki Query Skill

Query the wiki to find information. Uses Obsidian CLI for fast search and link graph traversal.

## Usage

```
/wiki-query <question>
/wiki-query What is React?
/wiki-query How do attention mechanisms work?
/wiki-query What papers discuss agentic memory?
```

## Workflow

### Step 1: Search using Obsidian CLI

Use `obsidian search` to find relevant pages:

```bash
obsidian search query="<keywords>" format=json
```

Examples:
- `obsidian search query="RAG" format=json` → returns files mentioning RAG
- `obsidian search query="reinforcement learning" format=json` → returns RL-related pages

The search returns a JSON array of file paths like:
```json
["wiki/entities/RAG.md", "wiki/entities/Reinforcement Learning.md"]
```

### Step 2: Build context graph with backlinks

For each relevant entity, get its backlinks to understand context:

```bash
obsidian backlinks file="Entity Name" format=json
```

This shows which other pages reference this entity — useful for:
- Finding related concepts
- Understanding how the entity is used
- Discovering additional context sources

### Step 3: Read relevant pages

Read the content of relevant pages:

```bash
obsidian read path="wiki/entities/Entity.md"
```

Or use the Read tool for direct file access if Obsidian CLI is slow.

### Step 4: Synthesize answer

Combine information from the pages into a coherent answer.

### Step 5: Output format

```
## Answer

[Synthesized answer based on the wiki pages]

## Sources Consulted
- [[Entity Page]] — [what it contributed]
- [[Another Page]] — [what it contributed]

## Related Entities (via backlinks)
- [[RelatedEntity]] — linked from X pages
```

## Obsidian CLI Commands Reference

| Command | Purpose |
|---------|---------|
| `obsidian search query="X"` | Full-text search across all wiki files |
| `obsidian search query="X" path=wiki/entities` | Search only in entities folder |
| `obsidian backlinks file="X"` | Find pages linking to entity X |
| `obsidian links file="X"` | Find outgoing links from entity X |
| `obsidian read path="wiki/entities/X.md"` | Read page content |
| `obsidian files folder=wiki/entities` | List all entity pages |

## Wiki Structure

```
wiki/
├── cache.md        # Entity names (one per line)
├── entities/       # Entity pages with facts
├── raw/            # Source documents
└── log.md          # Operation log
```

## Entity Page Format

```markdown
# EntityName
type: artifact/abstract/person/concept

## Facts

- [[Entity]] description... [[source-file]]
- [[Entity]] another fact... [[another-source]]
```

## Edge Cases

- **No search results:** Return "No relevant information found in the wiki. Consider ingesting sources on this topic with `/wiki-ingest-llm`."
- **Contradictory information:** Note the contradiction, present both views
- **Partial information:** Answer what's available, note gaps
- **Entity doesn't exist:** Suggest ingesting more sources

## Fallback (if Obsidian not available)

If Obsidian CLI fails or is not installed, use traditional approach:
1. Read `wiki/cache.md` for entity list
2. Use Grep: `grep -l "keyword" wiki/entities/*.md`
3. Use Read tool for file contents
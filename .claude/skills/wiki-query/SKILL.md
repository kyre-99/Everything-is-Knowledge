---
name: wiki-query
description: Query the knowledge wiki and get synthesized answers
---

# Wiki Query Skill

Query the wiki to find information. Reads relevant pages and synthesizes an answer.

## Usage

```
/wiki-query <question>
/wiki-query What is React?
/wiki-query How do attention mechanisms work?
/wiki-query What papers discuss agentic memory?
```

## Workflow

### Step 1: Read cache.md

Read `wiki/cache.md` to get list of all entity names.

### Step 2: Identify relevant pages

Match keywords from the question against:
- Entity names in cache.md
- File names in wiki/raw/

Select up to 5 most relevant entity pages.

### Step 3: Read relevant pages

Read each selected entity page using the Read tool.

### Step 4: Synthesize answer

Combine information from the pages into a coherent answer.

### Step 5: Output format

```
## Answer

[Synthesized answer]

## Sources Consulted
- [[Entity Page]] — [what it contributed]
```

Each entity page has facts with source references like `[[arxiv-2409.05591]]`.

## Wiki Structure

```
wiki/
├── cache.md        # Entity names (one per line)
├── entities/       # Entity pages with facts
├── raw/            # Source documents
└── log.md          # Operation log
```

## Edge Cases

- **No relevant pages found:** Return "No relevant information found in the wiki. Consider ingesting sources on this topic."
- **Contradictory information:** Note the contradiction, present both views
- **Partial information:** Answer what's available, note gaps
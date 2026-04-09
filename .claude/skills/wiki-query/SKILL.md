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

### Step 1: Read index.md

Read `index.md` to understand what's in the wiki.

### Step 2: Identify relevant pages

Scan the index for:
- Entity names matching keywords in the question
- Concept names matching keywords
- Source titles that might contain relevant information

Select up to 5 most relevant pages.

### Step 3: Read relevant pages

Read each selected page using the Read tool.

### Step 4: Synthesize answer

Combine information from the pages into a coherent answer.

**Simple question** (1-2 sources, < 500 words):
- Return inline answer directly
- List sources consulted at the end

**Complex synthesis** (3+ sources, or > 500 words):
- Create a synthesis page in `wiki/synthesis/`
- Return link to the page

### Step 5: Output format

```
## Answer

[Synthesized answer]

## Sources Consulted
- [[Source Title]] — [what it contributed]
- [[Entity Page]] — [what it contributed]
```

## Creating Synthesis Pages

If the answer is complex, create `wiki/synthesis/{slug}.md`:

```markdown
---
title: [Question Topic]
date: YYYY-MM-DD
query: [original question]
sources_used: [[Source 1]], [[Source 2]]
---

# [Question Topic]

## Question
[original question]

## Answer
[synthesized answer]

## Sources Consulted
- [[Source Title]] — [contribution to answer]

## Related Synthesis Pages
- [[Other Synthesis]] — [relationship]
```

## Edge Cases

- **No relevant pages found:** Return "No relevant information found in the wiki. Consider ingesting sources on this topic."
- **Contradictory information:** Note the contradiction, present both views
- **Partial information:** Answer what's available, note gaps

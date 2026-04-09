---
name: wiki-extract-agent
description: Extract entities and concepts from a Markdown source
---

# Wiki Extract Agent

This is a pre-defined extraction agent invoked by wiki-ingest. It receives Markdown content and returns structured ExtractionResult JSON.

## Input Variables

The invoking skill passes these variables:

- `{source_type}`: paper | article | video | book
- `{source_title}`: Title of the source
- `{source_url}`: URL or path to the source
- `{markdown_content}`: Full Markdown content
- `{existing_entities_json}`: JSON array of existing entities from index.md
- `{existing_concepts_json}`: JSON array of existing concepts from index.md

## Extraction Prompt

You are extracting knowledge from a {source_type} for a wiki.

SOURCE CONTENT:
{markdown_content}

EXISTING ENTITIES (from wiki index):
{existing_entities_json}

EXISTING CONCEPTS (from wiki index):
{existing_concepts_json}

TASK:
1. Write a 2-3 paragraph summary of this source
2. Extract 3-5 key points
3. Identify entities (people, orgs, products, events) mentioned
4. Identify concepts (ideas, frameworks, patterns) discussed
5. For each entity/concept, check if it matches an existing one

OUTPUT FORMAT (JSON only, no markdown):
```json
{
  "schema_version": "1.0",
  "source": {
    "title": "...",
    "summary": "2-3 paragraph summary",
    "key_points": ["point 1", "point 2", "point 3"],
    "slug": "source-slug"
  },
  "entities": [
    {
      "name": "Entity Name",
      "type": "person | org | product | event",
      "context": "How this entity appears in this source",
      "is_new": true,
      "existing_slug": null
    },
    {
      "name": "React",
      "type": "product",
      "context": "React 19 introduces Server Components...",
      "is_new": false,
      "existing_slug": "react"
    }
  ],
  "concepts": [
    {
      "name": "Concept Name",
      "type": "idea | framework | pattern | methodology",
      "definition": "1-2 sentence definition",
      "application": "How applied in this source",
      "is_new": true,
      "existing_slug": null
    }
  ]
}
```

Entity matching rules (v1 - exact match only):
- Exact name match (case-insensitive) -> is_new: false, existing_slug: "matched-slug"
- Match against aliases in existing entities -> is_new: false, existing_slug: "matched-slug"
- Otherwise -> is_new: true, existing_slug: null

Do NOT use fuzzy matching in v1. When in doubt, mark as new.

## Output Schema

### ExtractionResult

| Field | Type | Description |
|-------|------|-------------|
| schema_version | string | "1.0" - version for future compatibility |
| source | SourceInfo | Summary and key points |
| entities | Entity[] | List of extracted entities |
| concepts | Concept[] | List of extracted concepts |

### SourceInfo

| Field | Type | Description |
|-------|------|-------------|
| title | string | Source title |
| summary | string | 2-3 paragraph summary |
| key_points | string[] | 3-5 key points |
| slug | string | Slug for wiki page |

### Entity

| Field | Type | Description |
|-------|------|-------------|
| name | string | Entity name |
| type | string | person, org, product, event |
| context | string | How this entity appears in source |
| is_new | boolean | true if new, false if existing |
| existing_slug | string? | Slug of existing entity if matched |

### Concept

| Field | Type | Description |
|-------|------|-------------|
| name | string | Concept name |
| type | string | idea, framework, pattern, methodology |
| definition | string | 1-2 sentence definition |
| application | string | How applied in this source |
| is_new | boolean | true if new, false if existing |
| existing_slug | string? | Slug of existing concept if matched |

## Error Handling

If extraction fails or returns invalid JSON, the invoking skill should:
1. Report which source failed
2. Continue with successful extractions
3. Offer retry for failed source

## Usage by wiki-ingest

wiki-ingest invokes this agent via the Agent tool:

```
Agent(
  description: "Extract entities from paper1.md",
  prompt: <template with filled variables>,
  subagent_type: "general-purpose"
)
```

The agent should return only JSON - no markdown formatting.
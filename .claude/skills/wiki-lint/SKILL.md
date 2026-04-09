---
name: wiki-lint
description: Check wiki health and suggest fixes
---

# Wiki Lint Skill

Scan the wiki for issues and suggest fixes.

## Usage

```
/wiki-lint
```

## Workflow

### Step 1: Scan all wiki pages

Read all files in:
- `wiki/entities/*.md`
- `wiki/concepts/*.md`
- `wiki/sources/*.md`
- `wiki/synthesis/*.md`

### Step 2: Check for issues

#### Orphan pages

Pages with no inbound links (no other page references them).

Check: For each page, search for `[[Page Title]]` in all other pages.
Report pages with zero references.

```
Orphan pages:
- wiki/entities/SomeEntity.md — no pages link to it
```

#### Missing cross-references

Entities/concepts mentioned in sources but don't have their own pages.

Check: Scan source pages for `[[Entity]]` or `[[Concept]]` patterns. Verify each has a corresponding page.

```
Missing pages:
- [[SomeEntity]] mentioned in sources/paper.md but page doesn't exist
```

#### Index accuracy

Verify index.md matches actual pages.

Check:
- Count of entities in index matches count of files in `wiki/entities/`
- Count of concepts matches `wiki/concepts/`
- Count of sources matches `wiki/sources/`

```
Index discrepancies:
- Index shows 10 entities, found 12 files
- Missing from index: [[NewEntity]], [[AnotherEntity]]
```

#### Broken cross-references

`[[Page Name]]` that don't match any existing page.

Check: Extract all `[[...]]` patterns. Verify each matches a page title (frontmatter `name` or `title`).

```
Broken references:
- [[NonExistent]] in sources/paper.md — no matching page
```

### Step 3: Report findings

```
## Wiki Health Report

### Summary
- Total pages: [N]
- Entities: [N]
- Concepts: [N]
- Sources: [N]
- Synthesis: [N]

### Issues Found

#### Orphan Pages (N)
- [[Entity]] — add links from related sources

#### Missing Pages (N)
- [[Concept]] mentioned but doesn't exist — create it?

#### Index Discrepancies (N)
- Index shows X, found Y files

#### Broken References (N)
- [[Name]] doesn't exist — typo or create?

### Suggested Actions
1. [Action 1]
2. [Action 2]
```

### Step 4: Offer fixes

For each issue, ask if user wants to fix:

```
Fix orphan [[SomeEntity]]?
A) Add link from [[RelatedSource]]
B) Delete the entity (not used)
C) Skip
```

## Scope (v1)

v1 `/wiki-lint` checks:
- Orphan pages
- Missing pages
- Index accuracy
- Broken references

NOT checked (post-wedge):
- Outdated summaries
- Contradiction detection
- Content quality
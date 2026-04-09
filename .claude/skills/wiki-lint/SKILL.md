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
- `wiki/raw/*.md`

Read catalog files:
- `wiki/cache.md` - entity names

### Step 2: Check for issues

#### Cache accuracy

Verify cache.md matches actual entity pages.

Check:
- Count of names in cache.md matches count of files in `wiki/entities/`
- Each name in cache.md has a corresponding file

```
Cache discrepancies:
- Cache shows 10 entities, found 12 files
- Missing from cache: [[NewEntity]], [[AnotherEntity]]
```

#### Orphan pages

Entity pages with no inbound links (no other page references them).

Check: For each entity page, search for `[[Entity Name]]` in all other pages.

```
Orphan pages:
- wiki/entities/SomeEntity.md — no pages link to it
```

#### Missing entity pages

Entities mentioned in facts but don't have their own pages.

Check: Scan all entity pages for `[[Entity Name]]` patterns. Verify each has a corresponding page.

```
Missing pages:
- [[SomeEntity]] mentioned in entities/AnotherEntity.md but page doesn't exist
```

#### Broken cross-references

`[[Entity Name]]` that don't match any existing page.

```
Broken references:
- [[NonExistent]] in entities/RAG.md — no matching page
```

### Step 3: Report findings

```
## Wiki Health Report

### Summary
- Entity pages: [N]
- Raw documents: [N]
- Cache entries: [N]

### Issues Found

#### Cache Discrepancies (N)
- Cache shows X, found Y files

#### Orphan Pages (N)
- [[Entity]] — add links from related pages

#### Missing Pages (N)
- [[Entity]] mentioned but doesn't exist — create it?

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
A) Add link from [[RelatedEntity]]
B) Delete the entity (not used)
C) Skip
```
---
name: wiki-lint
description: Check wiki health and suggest fixes
allowed-tools:
  - Read
  - Grep
  - Bash
  - AskUserQuestion
---

# Wiki Lint Skill

Scan the wiki for issues using Obsidian CLI for fast, accurate analysis.

## Usage

```
/wiki-lint
/wiki-lint --fix  # Auto-fix simple issues
```

## Workflow

### Step 1: Check wiki exists

```bash
obsidian vault
```

If no vault is open, prompt user to:
1. Open Obsidian with this project as vault
2. Or run `/wiki-init` first

### Step 2: Gather wiki statistics

Use Obsidian CLI for fast statistics:

```bash
# Total entity pages
obsidian files folder=wiki/entities total

# Total raw documents
obsidian files folder=wiki/raw total

# Vault info
obsidian vault info=files
obsidian vault info=size
```

### Step 3: Find orphan pages (no inbound links)

Orphans are pages no other page references.

```bash
obsidian orphans format=json
```

Returns array of orphan file paths. Filter to wiki/entities:

```bash
obsidian orphans format=json | grep "wiki/entities"
```

### Step 4: Find unresolved links (broken wikilinks)

Unresolved links reference pages that don't exist.

```bash
obsidian unresolved format=json verbose
```

Returns:
```json
[
  {"link": "MissingEntity", "files": ["wiki/entities/SomePage.md", ...]}
]
```

### Step 5: Check cache accuracy

Compare cache.md with actual entities:

```bash
# Count cache entries
obsidian read path=wiki/cache.md | wc -l

# Count entity files
obsidian files folder=wiki/entities total

# Check for discrepancies
```

### Step 6: Analyze link graph health

Get overall link statistics:

```bash
# Total links in vault
obsidian tags total

# Most referenced entities (by backlink count)
for entity in $(obsidian files folder=wiki/entities format=json | jq -r '.[]'); do
  count=$(obsidian backlinks file="$entity" format=json total)
  echo "$count $entity"
done | sort -rn | head -10
```

### Step 7: Report findings

```markdown
## Wiki Health Report

### Summary
- Entity pages: 66
- Raw documents: 5
- Vault size: 27MB

### Issues Found

#### Orphan Pages (16)
Pages with no inbound links:
- [[Calculation of F1 score]] — add links from related entities
- [[Cognitive behaviors]] — consider merging or linking
- [[Knowledge Graphs]] — commonly referenced concept, should have links

#### Unresolved Links (0)
All wikilinks resolve correctly ✓

#### Cache Discrepancies (0)
cache.md matches entity files ✓

### Link Graph Stats
- Most referenced: [[CP-Search]] (27 backlinks)
- Least referenced: [orphans above]

### Suggested Actions
1. Link orphans to related entities
2. Consider merging similar concepts
3. Review entities with high backlink counts for accuracy
```

### Step 8: Interactive Fix Workflow

For each orphan page, run the interactive fix workflow:

#### 8.1 Detect orphans with backlink count

```bash
# For each entity in wiki/entities, check backlink count
obsidian backlinks file="EntityName" total
```

Entities with 0 backlinks are orphans.

#### 8.2 For each orphan, gather context

```bash
# Read orphan content
obsidian read path="wiki/entities/OrphanName.md"

# Find related pages via search
obsidian search query="keywords from orphan content" format=json
```

#### 8.3 Ask user for fix action

Use AskUserQuestion tool:

```
如何处理孤儿 [[OrphanName]]？

- 添加链接：在相关页面添加引用
- 合并：合并到相关实体并删除此页
- 删除：内容不重要的，删除此实体
- 跳过：不处理，保留原样
```

#### 8.4 Execute fix based on user choice

**Option A: Add Link**

1. Identify best related page from search results
2. Read the related page content
3. Use Edit tool to add `[[OrphanName]]` reference to the related page
4. Verify with `obsidian backlinks file="OrphanName" total` (should be > 0)

**Option B: Merge**

1. Read both orphan and target page
2. Add orphan content to target with `> Merged from [[OrphanName]]` marker
3. Delete orphan file: `rm "wiki/entities/OrphanName.md"`
4. Rebuild cache: `ls wiki/entities/*.md | xargs -I {} basename {} .md > wiki/cache.md`

**Option C: Delete**

1. Delete orphan file: `rm "wiki/entities/OrphanName.md"`
2. Rebuild cache: `ls wiki/entities/*.md | xargs -I {} basename {} .md > wiki/cache.md`

**Option D: Skip**

No action, move to next orphan.

#### 8.5 After processing all orphans

```bash
# Rebuild cache.md
ls wiki/entities/*.md | xargs -I {} basename {} .md > wiki/cache.md

# Final verification
obsidian files folder=wiki/entities total
```

### Step 9: Final Report

```markdown
## Wiki Lint Complete

### Changes Made
- ✅ Merged: [[OrphanA]] → [[TargetEntity]]
- ⏭️ Skipped: [[OrphanB]] (kept as-is)
- 🗑️ Deleted: [[OrphanC]] (not useful)
- 🔗 Linked: Added [[OrphanD]] reference to [[RelatedEntity]]

### Final Stats
- Entity pages: N (was M)
- Orphan pages remaining: N
- Unresolved links: N
- Cache synchronized: ✓
```

## Orphan Fix Decision Guide

| Orphan Type | Recommended Action |
|-------------|-------------------|
| Core concept (RAG, LLM, etc.) | Add link from related entities |
| Niche detail | Merge into parent concept |
| Duplicate content | Delete and add reference |
| Important standalone | Add links to establish connections |
| Low-value content | Delete |

## Example: Merge Orphan to Target

```markdown
# In target entity page (e.g., [[Retrieval-Augmented Generation]])

## Related: Knowledge Graphs

> Merged from [[Knowledge Graphs]] (orphan page)

- Knowledge graphs are structured data models... [[source]]
- Key benefit: provides semantic context for reasoning... [[source]]
```

## Example: Add Link to Orphan

```markdown
# In related entity page (e.g., [[CP-Search]])

## Facts

- CP-Search uses [[Knowledge Graphs]] for structured reasoning... [[source]]
```

## Obsidian CLI Commands Reference

| Command | Purpose |
|---------|---------|
| `obsidian vault` | Check current vault info |
| `obsidian files folder=X total` | Count files in folder |
| `obsidian orphans` | Find pages with no inbound links |
| `obsidian unresolved` | Find broken wikilinks `[[Missing]]` |
| `obsidian backlinks file="X" total` | Count pages linking to X |
| `obsidian search query="X"` | Find related pages for suggestions |

## Issue Types

### Orphan Pages
**Symptom:** Entity page exists but no other page references it.

**Fix:**
- Search for related pages: `obsidian search query="keyword"`
- Add `[[Entity]]` reference to related pages
- Or delete if not useful

### Unresolved Links
**Symptom:** `[[Entity Name]]` referenced but page doesn't exist.

**Fix:**
- Create the missing entity page
- Or fix typo in the reference

### Cache Discrepancies
**Symptom:** cache.md count ≠ entity file count.

**Fix:**
```bash
# Rebuild cache from entities
ls wiki/entities/*.md | xargs -I {} basename {} .md > wiki/cache.md
```

## Quick Fix Commands

```bash
# Rebuild cache.md
ls wiki/entities/*.md | xargs -I {} basename {} .md > wiki/cache.md

# Create missing entity page
obsidian create name="MissingEntity" content="# MissingEntity\ntype: concept\n\n## Facts\n\n- " open

# Open orphan in Obsidian for editing
obsidian open file="OrphanEntity"
```

## Fallback (if Obsidian CLI unavailable)

Use traditional shell approach:

```bash
# Count entities
ls wiki/entities/*.md 2>/dev/null | wc -l

# Check for orphans (slow)
for f in wiki/entities/*.md; do
  name=$(basename "$f" .md)
  grep -q "\[\[$name\]\]" wiki/entities/*.md || echo "Orphan: $name"
done

# Check for unresolved (slow)
grep -oh '\[\[[^]]*\]\]' wiki/entities/*.md | sort -u | while read ref; do
  name=$(echo "$ref" | sed 's/\[\[\(.*\)\]\]/\1/')
  [ ! -f "wiki/entities/${name}.md" ] && echo "Missing: $name"
done
```
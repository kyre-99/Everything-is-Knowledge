---
name: wiki-disambiguate
description: Disambiguate entities and manage aliases for the knowledge wiki
allowed-tools:
  - Read
  - Grep
  - Bash
  - Edit
  - AskUserQuestion
---

# Wiki Disambiguate Skill

Manage entity aliases and resolve naming conflicts in the wiki. Uses Obsidian CLI's alias system to handle synonyms, abbreviations, and multi-language terms.

## Usage

```
/wiki-disambiguate                    # Interactive: scan for disambiguation opportunities
/wiki-disambiguate --auto             # Auto-add common aliases
/wiki-disambiguate "RAG"              # Disambiguate specific term
/wiki-disambiguate --merge            # Find and merge duplicate entities
```

## What is Disambiguation?

### Synonyms (Same entity, different names)
```
[[RAG]] → [[Retrieval-Augmented Generation]]
[[LLM]] → [[Large Language Models]]
[[大语言模型]] → [[Large Language Models]]
```

### Polysemy (Same name, different entities)
```
[[Apple]] → Company? Fruit?
[[Transformer]] → Architecture? Movie? Device?
```

### Solution: Aliases

```yaml
---
aliases: ["RAG", "检索增强生成"]
---
# Retrieval-Augmented Generation
```

With aliases, `[[RAG]]` automatically resolves to `[[Retrieval-Augmented Generation]]`.

## Workflow

### Step 1: Scan for potential duplicates

Find entities that might be the same concept:

```bash
# Get all entities
obsidian files folder=wiki/entities format=json
```

Detection strategies:
- Similar names (edit distance, singular/plural)
- One name is abbreviation of another
- Same type + shared sources

### Step 2: Compare entity pairs

```bash
# Read both entities
obsidian read path="wiki/entities/EntityA.md"
obsidian read path="wiki/entities/EntityB.md"
```

Compare:
- Content overlap
- Same type
- Shared [[source]] references

### Step 3: Interactive disambiguation

```
Potential duplicate detected:

[[Entity A]] (primary)
- Type: abstract
- Facts: 3

[[Entity B]] (similar)
- Type: abstract
- Facts: 2

Actions:
A) Link B to A (add alias + reference in A)
B) Link A to B (add alias + reference in B)
C) Keep separate (different concepts)
D) Skip
```

### Step 4: Execute linking

When user chooses to link:

```bash
# 1. Add alias to primary entity
obsidian property:set name="aliases" value="EntityB" file="EntityA"

# 2. Add reference line in primary entity
# Edit EntityA to add:
# > See also: [[EntityB]]
```

**Result:**
- `[[EntityB]]` resolves to EntityA via alias
- EntityB file kept intact (no broken links)
- Cross-references preserved

### Step 5: Update cache

```bash
ls wiki/entities/*.md | xargs -I {} basename {} .md > wiki/cache.md
```

## Common Alias Patterns

### Academic/Technical Terms

| Entity Name | Suggested Aliases |
|-------------|------------------|
| Retrieval-Augmented Generation | `RAG`, `检索增强生成` |
| Large Language Models | `LLM`, `大语言模型` |
| Chain of Thought | `CoT`, `思维链` |
| Supervised Fine-Tuning | `SFT`, `监督微调` |
| Reinforcement Learning | `RL`, `强化学习` |
| Knowledge Graphs | `KG`, `知识图谱` |
| Markov Decision Process | `MDP`, `马尔可夫决策过程` |

### Person Names

| Entity Name | Suggested Aliases |
|-------------|------------------|
| Geoffrey Hinton | `Hinton`, `杰弗里·辛顿` |
| Andrew Ng | `Ng`, `吴恩达` |

### Organization/Project Names

| Entity Name | Suggested Aliases |
|-------------|------------------|
| OpenAI | `openai` |
| DeepSeek | `deepseek`, `深度求索` |

## Disambiguation Report

```markdown
## Disambiguation Report

### Aliases Added
- [[Retrieval-Augmented Generation]] ← `RAG`, `检索增强生成`
- [[Large Language Models]] ← `LLM`, `大语言模型`
- [[Chain of Thought]] ← `CoT`

### Potential Duplicates (needs review)
- [[Knowledge Graph]] vs [[Knowledge Graphs]] — similar content, consider merging
- [[Language Model]] vs [[Large Language Models]] — different scope, keep separate

### Polysemy Detected
- [[Transformer]] — multiple meanings detected:
  - [[Transformer (Architecture)]] — neural network architecture
  - Suggest creating separate pages with disambiguation page
```

## Obsidian CLI Commands Reference

| Command | Purpose |
|---------|---------|
| `obsidian aliases` | List all aliases in vault |
| `obsidian aliases file="X"` | Get aliases for specific entity |
| `obsidian property:set name="aliases" value='[...]' file="X"` | Set aliases |
| `obsidian property:read name="aliases" file="X"` | Read aliases |
| `obsidian search query="X"` | Find potential synonym matches |

## Workflow Examples

### Example 1: Auto-add common abbreviations

```bash
# Detect LLM-related entities
obsidian search query="Large Language Model" format=json

# Add alias
obsidian property:set name="aliases" value="LLM" file="Large Language Models"
```

### Example 2: Merge duplicate entities

```
Detected potential duplicates:
- [[Knowledge Graph]] (47 words)
- [[Knowledge Graphs]] (32 words)

Both describe structured data representation.

Merge action:
1. Keep [[Knowledge Graphs]] as primary (better fit with plural convention)
2. Add alias "Knowledge Graph"
3. Merge content
4. Delete [[Knowledge Graph]]
```

### Example 3: Handle polysemy

```
Found multiple meanings for "Transformer":

1. [[Transformer (Architecture)]] — neural network, attention mechanism
2. No page for: Transformer (Electrical) — power distribution device

Actions:
A) Rename to [[Transformer (Architecture)]], add alias "Transformer"
B) Keep as is, note that it's AI-focused
C) Create disambiguation page listing all meanings
```

## Edge Cases

### Circular Aliases

Avoid: Entity A has alias B, Entity B has alias A.

```
Wrong:
  [[RAG]] aliases: ["Retrieval-Augmented Generation"]
  [[Retrieval-Augmented Generation]] aliases: ["RAG"]

Correct:
  [[Retrieval-Augmented Generation]] aliases: ["RAG"]
  No separate [[RAG]] page needed
```

### Alias Conflicts

If alias already exists on different entity:

```
Conflict: "CoT" already aliased to [[Chain of Thought]]

New candidate: [[Chain-of-Thought Reasoning]] also wants "CoT"

Options:
1. Keep current assignment
2. Move alias to new entity
3. Use longer form "CoTR" for new entity
```

### Partial Name Matching

```
Query: "language model"
Results:
- [[Large Language Models]] ← add alias "Language Model"?
- [[Language Model]] ← separate entity?

Decision: Different scopes (large vs general), keep separate
```
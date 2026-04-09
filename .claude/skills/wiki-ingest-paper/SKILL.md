---
name: wiki-ingest-paper
description: Search and ingest academic papers from arXiv/PMC into the wiki. Supports keyword search, trending papers, and direct arXiv ID lookup.
---

# Wiki Ingest Paper Skill

Search for academic papers and ingest them into the wiki with full extraction pipeline.

## Usage

```
# Search and interactively select papers
/wiki-ingest-paper --search "agent memory"
/wiki-ingest-paper --search "RAG" --categories cs.CL,cs.AI --limit 20

# Direct import by arXiv ID
/wiki-ingest-paper --arxiv 2409.05591
/wiki-ingest-paper --arxiv 2409.05591 2409.05592 2409.05593

# Trending papers
/wiki-ingest-paper --trending --days 7 --limit 20
```

## CLI Command

```bash
uv run python .claude/skills/wiki-ingest-paper/bin/wiki_ingest_paper.py [options]
```

## Workflow

```
/wiki-ingest-paper --search "agent memory"
         │
         ▼
    ┌─────────────────┐
    │  DeepXiv Search │  ← 搜索论文
    └────────┬────────┘
             │
             ▼
    ┌─────────────────┐
    │ 显示搜索结果     │  ← 展示标题、引用数、摘要
    │ 让用户选择论文   │
    └────────┬────────┘
             │
             ▼
    ┌─────────────────┐
    │  获取论文全文    │  ← DeepXiv API 返回 Markdown
    └────────┬────────┘
             │
             ▼
    ┌─────────────────┐
    │  LLM 知识提取    │  ← OpenAI API 提取实体/概念
    └────────┬────────┘
             │
             ▼
    ┌─────────────────┐
    │  写入 Wiki      │  ← sources/, entities/, concepts/
    └─────────────────┘
```

## Search Options

| 参数 | 示例 | 说明 |
|------|------|------|
| `--search` | "agent memory" | 搜索关键词 |
| `--limit` | 20 | 返回结果数 (默认 10, 最大 100) |
| `--categories` | cs.AI,cs.CL | 按类别筛选 |
| `--min-citations` | 50 | 最少引用数 |

## Direct Import

直接传入 arXiv ID，跳过搜索步骤：

```bash
# 单篇论文
/wiki-ingest-paper --arxiv 2409.05591

# 多篇论文
/wiki-ingest-paper --arxiv 2409.05591 2409.05592 2409.05593
```

## Trending Papers

获取近期热门论文：

```bash
/wiki-ingest-paper --trending --days 7 --limit 20
```

`--days` 可选值：7, 14, 30

## Common arXiv Categories

- `cs.AI` - 人工智能
- `cs.CL` - 计算与语言 (NLP)
- `cs.CV` - 计算机视觉
- `cs.LG` - 机器学习
- `cs.RO` - 机器人
- `cs.SE` - 软件工程
- `stat.ML` - 机器学习 (统计)

## Interactive Selection

搜索后会显示结果列表，用户可以：

```
Enter paper numbers to ingest (e.g., '1,3,5' or '1-3' or 'all'):
```

- `1,3,5` - 选择第 1、3、5 篇
- `1-3` - 选择第 1 到第 3 篇
- `all` 或回车 - 选择全部

## Example Output

```
🔍 Searching for: 'agent memory'...

Found 10000 papers (showing 10):

1. Memory Intelligence Agent
   arXiv: 2604.04503 | Citations: None
   Deep research agents (DRAs) integrate LLM reasoning...

2. Agent Workflow Memory
   arXiv: 2409.07429 | Citations: 73
   Despite the potential of language model-based agents...

Enter paper numbers to ingest: 1,2

📚 Ingesting 2 papers...

[1/2] Processing arXiv:2604.04503...
  ✅ Memory Intelligence Agent: 5 entities, 3 concepts

[2/2] Processing arXiv:2409.07429...
  ✅ Agent Workflow Memory: 4 entities, 2 concepts

📝 Writing wiki pages to wiki...
Created: sources[2], entities[9], concepts[5]

✅ Successfully ingested 2 papers!
```

## Configuration

DeepXiv token 自动注册（首次使用时）。OpenAI API key 需要配置：

```bash
export OPENAI_API_KEY="your-key"
# 或运行 /wiki-init 配置
```

## Integration with Wiki

论文导入后生成：

- **Source page**: `wiki/sources/{paper-title}.md`
  - 完整摘要
  - 关键要点
  - 提及的实体和概念

- **Entity pages**: `wiki/entities/{name}.md`
  - 作者、数据集、方法等

- **Concept pages**: `wiki/concepts/{name}.md`
  - 关键思想、框架、技术

交叉引用使用 Obsidian 语法：`[[MemoRAG]]`, `[[RAG]]`
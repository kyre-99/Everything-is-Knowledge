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

## Workflow

```
/wiki-ingest-paper --search "agent memory"
         │
         ▼
    ┌─────────────────┐
    │  DeepXiv Search │
    └────────┬────────┘
             │
             ▼
    ┌─────────────────┐
    │ 显示搜索结果     │
    │ 让用户选择论文   │
    └────────┬────────┘
             │
             ▼
    ┌─────────────────┐
    │  获取论文全文    │
    │ 保存到 wiki/raw │
    └────────┬────────┘
             │
             ▼
    ┌─────────────────┐
    │  两阶段 LLM 提取 │
    │  (shared module)│
    └────────┬────────┘
             │
             ▼
    ┌─────────────────┐
    │  写入 Entity 页 │
    └─────────────────┘
```

## Two-Phase Extraction

Uses shared LLM extractor (`shared/bin/llm_extractor.py`):

1. **Phase 1: Discovery** - Find all entities (authors, methods, frameworks, concepts)
2. **Phase 2: Context** - Generate detailed context for each entity (parallel)

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

## Wiki Output

论文导入后生成：

- **Raw document**: `wiki/raw/arxiv-{id}.md` - 论文全文 markdown
- **Entity pages**: `wiki/entities/{name}.md` - 作者、方法、框架等

Entity 页面示例：

```markdown
# MemoRAG
type: artifact

## Facts

- [[MemoRAG]]是一个创新的长文本处理框架，由北京大学和人民大学的研究团队于2024年提出。该框架通过全局记忆模块增强检索能力... [[arxiv-2409.05591]]
```

每个 fact 直接附带来源文件。

## Configuration

DeepXiv token 自动注册（首次使用时）。OpenAI API key 需要配置：

```bash
export OPENAI_API_KEY="your-key"
# 或运行 /wiki-init 配置
```
# 🧠 Everything is Knowledge

[English](README.md) | [中文](README_CN.md)

> ✨ **Turn scattered knowledge into a structured, queryable wiki** — powered by Claude Code and LLM extraction.

**Everything is Knowledge** transforms your documents, papers, URLs, and videos into an interconnected wiki with automatic entity extraction and cross-references. Query your knowledge base naturally and get synthesized answers with citations.

---

## 🎯 Why This Project?

| 😰 The Problem | ✅ The Solution |
|----------------|-----------------|
| 📄 **Fragmented knowledge** — Papers, articles, videos scattered everywhere | 🤖 **Auto-extraction** — LLM identifies entities (people, concepts, methods) |
| 🤔 **Hard to recall** — "Which paper discussed GRPO? I know I read it..." | 🔗 **Cross-referencing** — Obsidian-style `[[Entity]]` links connect everything |
| 🏝️ **No synthesis** — Information stays isolated, never connected | 💬 **Natural queries** — Ask questions, get synthesized answers |

---

## ⚡ Quick Start

```bash
# 1️⃣ Clone the repository
git clone https://github.com/kyre-99/everything-is-knowledge.git
cd everything-is-knowledge

# 2️⃣ Run setup (installs dependencies, configures API keys)
./setup

# 3️⃣ Open Obsidian and select wiki/ as your vault

# 4️⃣ Start Claude Code
claude

# 5️⃣ Ingest your first source
> /wiki-ingest-llm https://arxiv.org/abs/2409.05591

# 6️⃣ Query the wiki
> /wiki-query What is MemoRAG?
```

---

## 🛠️ Skills

| Skill | Description | Example |
|:-----:|-------------|---------|
| 🚀 `/wiki-init` | Initialize wiki structure and configure API keys | `/wiki-init` |
| 📥 `/wiki-ingest-llm` | Ingest sources using LLM extraction | `/wiki-ingest-llm wiki/raw/paper.pdf` |
| 📚 `/wiki-ingest-paper` | Search and ingest academic papers from arXiv | `/wiki-ingest-paper --search "RAG memory"` |
| 🔍 `/wiki-query` | Query the wiki and get synthesized answers | `/wiki-query What is MemoRAG?` |
| 🏥 `/wiki-lint` | Check wiki health (orphans, broken links) | `/wiki-lint` |
| 🔀 `/wiki-disambiguate` | Merge duplicate entities and manage aliases | `/wiki-disambiguate` |

---

## 📋 Prerequisites

Before running `./setup`, ensure these are installed:

| Tool | Website | Install |
|:----:|:-------:|---------|
| 🤖 **Claude Code CLI** | [claude.ai/code](https://claude.ai/code) | `npm install -g @anthropic-ai/claude-code` |
| 💎 **Obsidian** | [obsidian.md](https://obsidian.md) | `brew install --cask obsidian` |
| 🐍 **Python 3.12+** | [python.org](https://python.org) | `brew install python` |

> 💡 **Tip:** The setup script will automatically install `uv` (Python package manager) and all dependencies.

---

## 📦 Supported Source Types

| Type | Example | Processing |
|:----:|---------|------------|
| 📄 **PDF files** | `wiki/raw/paper.pdf` | MinerU API → Markdown |
| 📝 **arXiv papers** | `2409.05591` | DeepXiv API → Markdown |
| 🌐 **Web URLs** | `https://example.com/article` | Scrapling → Markdown |
| 🎬 **Bilibili videos** | `https://bilibili.com/video/BV...` | Whisper → Transcript |
| 📝 **Markdown files** | `wiki/raw/article.md` | Direct read |

---

## 💡 Usage Examples

### 📥 Ingest Sources

```bash
# Single source
/wiki-ingest-llm wiki/raw/paper.pdf
/wiki-ingest-llm https://arxiv.org/abs/2409.05591
/wiki-ingest-llm https://bilibili.com/video/BV1vyDpBEESx

# Batch processing 🚀
/wiki-ingest-llm wiki/raw/*.pdf --parallel 5

# Use different LLM model
/wiki-ingest-llm wiki/raw/paper.pdf --model gpt-4o
```

### 📚 Search & Ingest Papers

```bash
# Keyword search
/wiki-ingest-paper --search "agent memory" --limit 20

# Filter by category
/wiki-ingest-paper --search "RAG" --categories cs.CL,cs.AI

# Direct import by arXiv ID
/wiki-ingest-paper --arxiv 2409.05591 2409.05592

# Trending papers 🔥
/wiki-ingest-paper --trending --days 7
```

### 🔍 Query the Wiki

```bash
/wiki-query What is RAG?
/wiki-query Which papers discuss GRPO?
/wiki-query How does MemoRAG differ from traditional RAG?
```

Returns synthesized answers with citations:

```
## 💬 Answer

MemoRAG is a memory-augmented RAG framework that introduces a global memory
module to cache retrieved knowledge across queries...

## 📚 Sources
- [[arxiv-2409.05591]] — Introduced MemoRAG architecture
- [[RAG]] — Definition and traditional approach
- [[Hongjin Qian]] — Lead author of MemoRAG paper
```

---

## 📁 Wiki Structure

```
wiki/
├── 📑 index.md              # Catalog (auto-updated)
├── 🗃️ cache.md              # Entity names cache
├── 📋 log.md                # Operation log
├── 📂 entities/             # Knowledge entities
│   ├── RAG.md
│   ├── MemoRAG.md
│   ├── Hongjin Qian.md
│   └── ...
└── 📂 raw/                  # Source documents
    ├── arxiv-2409.05591.md
    └── ...
```

---

## 🔧 Dependencies

| Dependency | Purpose |
|------------|---------|
| 📦 **uv** | Fast Python package manager |
| 🕷️ **Scrapling** | Web scraping with anti-bot stealth |
| 📄 **MinerU** | PDF parsing to Markdown |
| 🤖 **OpenAI** | LLM extraction (gpt-4o-mini default) |
| 📚 **DeepXiv SDK** | arXiv paper search |
| 🎧 **yt-dlp + Whisper** | Bilibili video transcription |

---

## 🤝 Contributing

PRs welcome! Areas for contribution:

- 🌐 Additional source types (YouTube, Twitter, podcasts)
- 🧠 Better entity disambiguation
- ⚡ Query optimization

---

## 📄 License

MIT
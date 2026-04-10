# 🧠 Everything is Knowledge

[English](README.md) | [中文](README_CN.md)

> ✨ **将碎片化知识转化为结构化、可查询的知识库** —— 由 Claude Code 和 LLM 提取驱动。

**Everything is Knowledge** 是一个知识管理系统，可以将文档、论文、网页、视频转化为结构化的 wiki 知识库，包含自动实体提取和交叉引用。使用自然语言查询，获取带引用的综合答案。

---

## 🎯 为什么需要这个项目？

| 😰 问题 | ✅ 解决方案 |
|---------|------------|
| 📄 **知识碎片化** — 论文、文章、视频散落在各处 | 🤖 **自动提取** — LLM 从来源中识别实体（人物、概念、方法） |
| 🤔 **难以回忆** — "哪篇论文讨论了 GRPO？我读过但忘了..." | 🔗 **交叉引用** — Obsidian 风格的 `[[实体]]` 链接连接所有内容 |
| 🏝️ **缺乏整合** — 信息孤立，无法形成关联 | 💬 **自然查询** — 提问，获取带引用的综合答案 |

---

## ⚡ 快速开始

```bash
# 1️⃣ 克隆仓库
git clone https://github.com/kyre-99/everything-is-knowledge.git
cd everything-is-knowledge

# 2️⃣ 运行 setup（安装依赖、配置 API keys）
./setup

# 3️⃣ 打开 Obsidian，选择 wiki/ 作为 vault

# 4️⃣ 启动 Claude Code
claude

# 5️⃣ 导入第一个来源
> /wiki-ingest-llm https://arxiv.org/abs/2409.05591

# 6️⃣ 查询 wiki
> /wiki-query What is MemoRAG?
```

---

## 🛠️ 功能特性

| Skill | 描述 | 示例 |
|:-----:|------|------|
| 🚀 `/wiki-init` | 初始化 wiki 结构并配置 API keys | `/wiki-init` |
| 📥 `/wiki-ingest-llm` | 使用 LLM 提取导入来源 | `/wiki-ingest-llm wiki/raw/paper.pdf` |
| 📚 `/wiki-ingest-paper` | 搜索并导入 arXiv 学术论文 | `/wiki-ingest-paper --search "RAG memory"` |
| 🔍 `/wiki-query` | 查询 wiki 并获取综合答案 | `/wiki-query What is MemoRAG?` |
| 🏥 `/wiki-lint` | 检查 wiki 健康（孤儿、断链） | `/wiki-lint` |
| 🔀 `/wiki-disambiguate` | 合并重复实体、管理别名 | `/wiki-disambiguate` |

---

## 📋 前置依赖

运行 `./setup` 前请确保已安装：

| 工具 | 官网 | 安装命令 |
|:----:|:----:|----------|
| 🤖 **Claude Code CLI** | [claude.ai/code](https://claude.ai/code) | `npm install -g @anthropic-ai/claude-code` |
| 💎 **Obsidian** | [obsidian.md](https://obsidian.md) | `brew install --cask obsidian` |
| 🐍 **Python 3.12+** | [python.org](https://python.org) | `brew install python` |

> 💡 **提示：** setup 脚本会自动安装 `uv`（Python 包管理器）和所有依赖。

---

## 📦 支持的来源类型

| 类型 | 示例 | 处理方式 |
|:----:|------|----------|
| 📄 **PDF 文件** | `wiki/raw/paper.pdf` | MinerU API → Markdown |
| 📝 **arXiv 论文** | `2409.05591` | DeepXiv API → Markdown |
| 🌐 **网页 URL** | `https://example.com/article` | Scrapling → Markdown |
| 🎬 **Bilibili 视频** | `https://bilibili.com/video/BV...` | Whisper → 转录文本 |
| 📝 **Markdown 文件** | `wiki/raw/article.md` | 直接读取 |

---

## 💡 使用示例

### 📥 导入来源

```bash
# 单个来源
/wiki-ingest-llm wiki/raw/paper.pdf
/wiki-ingest-llm https://arxiv.org/abs/2409.05591
/wiki-ingest-llm https://bilibili.com/video/BV1vyDpBEESx

# 批量处理 🚀
/wiki-ingest-llm wiki/raw/*.pdf --parallel 5

# 使用不同 LLM 模型
/wiki-ingest-llm wiki/raw/paper.pdf --model gpt-4o
```

### 📚 搜索并导入论文

```bash
# 关键词搜索
/wiki-ingest-paper --search "agent memory" --limit 20

# 按类别过滤
/wiki-ingest-paper --search "RAG" --categories cs.CL,cs.AI

# 直接导入 arXiv ID
/wiki-ingest-paper --arxiv 2409.05591 2409.05592

# 热门论文 🔥
/wiki-ingest-paper --trending --days 7
```

### 🔍 查询 Wiki

```bash
/wiki-query What is RAG?
/wiki-query Which papers discuss GRPO?
/wiki-query MemoRAG 与传统 RAG 有何不同？
```

返回带引用的综合答案：

```
## 💬 答案

MemoRAG 是一个记忆增强的 RAG 框架，引入全局记忆模块来缓存跨查询
检索的知识...

## 📚 来源
- [[arxiv-2409.05591]] — 提出 MemoRAG 架构
- [[RAG]] — 定义和传统方法
- [[Hongjin Qian]] — MemoRAG 论文作者
```

---

## 📁 Wiki 结构

```
wiki/
├── 📑 index.md              # 目录（自动更新）
├── 🗃️ cache.md              # 实体名缓存
├── 📋 log.md                # 操作日志
├── 📂 entities/             # 知识实体
│   ├── RAG.md
│   ├── MemoRAG.md
│   ├── Hongjin Qian.md
│   └── ...
└── 📂 raw/                  # 来源文档
    ├── arxiv-2409.05591.md
    └── ...
```

---

## 🔧 依赖列表

| 依赖 | 用途 |
|------|------|
| 📦 **uv** | 快速 Python 包管理器 |
| 🕷️ **Scrapling** | 带 anti-bot 隐蔽的网页抓取 |
| 📄 **MinerU** | PDF 转 Markdown |
| 🤖 **OpenAI** | LLM 提取（默认 gpt-4o-mini） |
| 📚 **DeepXiv SDK** | arXiv 论文搜索 |
| 🎧 **yt-dlp + Whisper** | Bilibili 视频转录 |

---

## 🤝 贡献

欢迎 PR！主要方向：

- 🌐 更多来源类型（YouTube、Twitter、播客）
- 🧠 更好的实体消歧
- ⚡ 查询优化

---

## 📄 许可证

MIT
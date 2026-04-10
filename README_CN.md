# Everything is Knowledge

[English](README.md) | [中文](README_CN.md)

> 将碎片化知识转化为结构化、可查询的知识库 —— 由 Claude Code 和 LLM 提取驱动。

**Everything is Knowledge** 是一个知识管理系统，可以将文档、论文、网页、视频转化为结构化的 wiki 知识库，包含实体和交叉引用。使用自然语言查询，从个人知识库中获取综合答案。

## 目录

- [为什么需要这个项目？](#为什么需要这个项目)
- [功能特性](#功能特性)
- [快速开始](#快速开始)
- [前置依赖](#前置依赖)
- [支持的来源类型](#支持的来源类型)
- [使用示例](#使用示例)
- [Wiki 结构](#wiki-结构)
- [实体类型](#实体类型)
- [配置说明](#配置说明)
- [API Key 来源](#api-key-来源)
- [两阶段 LLM 提取](#两阶段-llm-提取)
- [项目结构](#项目结构)
- [依赖列表](#依赖列表)

## 为什么需要这个项目？

- **知识碎片化** → 论文、文章、视频散落在各处
- **难以回忆** → "哪篇论文讨论了 GRPO？" —— 你读过，但忘了在哪
- **缺乏整合** → 信息孤立，无法形成关联

本项目通过以下方式解决：
- **自动提取** → LLM 从来源中识别实体（人物、概念、方法）
- **交叉引用** → Obsidian 风格的 `[[实体]]` 链接连接所有内容
- **自然查询** → 提问，获取带引用的综合答案

## 功能特性

| Skill | 描述 | 示例 |
|-------|------|------|
| `/wiki-init` | 初始化 wiki 结构并配置 API keys | `/wiki-init` |
| `/wiki-ingest-llm` | 使用 LLM 提取导入来源（PDF、URL、arXiv、Bilibili） | `/wiki-ingest-llm wiki/raw/paper.pdf` |
| `/wiki-ingest-paper` | 搜索并导入 arXiv/PMC 学术论文 | `/wiki-ingest-paper --search "RAG memory"` |
| `/wiki-query` | 查询 wiki 并获取综合答案 | `/wiki-query What is MemoRAG?` |
| `/wiki-lint` | 检查 wiki 健康（孤儿、断链） | `/wiki-lint` |
| `/wiki-disambiguate` | 合并重复实体、管理别名 | `/wiki-disambiguate` |

## 快速开始

```bash
# 1. 克隆仓库
git clone https://github.com/kyre-99/everything-is-knowledge.git
cd everything-is-knowledge

# 2. 运行 setup（安装依赖、配置 API keys）
./setup

# 3. 打开 Obsidian，选择 wiki/ 作为 vault

# 4. 启动 Claude Code
claude

# 5. 导入第一个来源
> /wiki-ingest-llm https://arxiv.org/abs/2409.05591

# 6. 查询 wiki
> /wiki-query What is MemoRAG?
```

## 前置依赖

运行 `./setup` 前请确保已安装：

| 工具 | 官网 | 安装命令 |
|------|------|----------|
| **Claude Code CLI** | [claude.ai/code](https://claude.ai/code) | `npm install -g @anthropic-ai/claude-code` |
| **Obsidian** | [obsidian.md](https://obsidian.md) | macOS: `brew install --cask obsidian` |
| **Python 3.12+** | [python.org](https://python.org) | 系统安装或 `brew install python` |

> **注意：** setup 脚本会自动安装 `uv`（Python 包管理器）和项目依赖。

## 支持的来源类型

| 类型 | 示例 | 工作原理 |
|------|------|----------|
| **PDF 文件** | `wiki/raw/paper.pdf` | MinerU API → Markdown |
| **arXiv 论文** | `2409.05591` | DeepXiv API → Markdown |
| **网页 URL** | `https://example.com/article` | Scrapling → Markdown |
| **Bilibili 视频** | `https://bilibili.com/video/BV...` | Whisper → 转录文本 |
| **Markdown 文件** | `wiki/raw/article.md` | 直接读取 |

## 使用示例

### 导入来源

```bash
# 单个来源
/wiki-ingest-llm wiki/raw/paper.pdf
/wiki-ingest-llm https://arxiv.org/abs/2409.05591
/wiki-ingest-llm https://bilibili.com/video/BV1vyDpBEESx

# 批量处理
/wiki-ingest-llm wiki/raw/*.pdf --parallel 5
/wiki-ingest-llm wiki/raw/paper1.pdf wiki/raw/paper2.pdf https://example.com

# 使用不同 LLM 模型
/wiki-ingest-llm wiki/raw/paper.pdf --model gpt-4o
```

### 搜索并导入论文

```bash
# 关键词搜索
/wiki-ingest-paper --search "agent memory" --limit 20

# 按类别过滤
/wiki-ingest-paper --search "RAG" --categories cs.CL,cs.AI

# 直接导入 arXiv ID
/wiki-ingest-paper --arxiv 2409.05591 2409.05592

# 热门论文
/wiki-ingest-paper --trending --days 7
```

### 查询 Wiki

```bash
/wiki-query What is RAG?
/wiki-query Which papers discuss GRPO?
/wiki-query MemoRAG 与传统 RAG 有何不同？
/wiki-query 哪些机构在做 agent memory 研究？
```

返回带引用的综合答案：
```
## Answer

MemoRAG 是一个记忆增强的 RAG 框架，引入全局记忆模块来缓存跨查询
检索的知识...

## Sources
- [[arxiv-2409.05591]] — 提出 MemoRAG 架构
- [[RAG]] — 定义和传统方法
- [[Hongjin Qian]] — MemoRAG 论文作者
```

### 检查 Wiki 健康

```bash
/wiki-lint
```

检测并报告：
- 孤儿实体（无入链）
- 断开的 `[[...]]` 交叉引用
- 缺失的来源文档
- 索引不一致

## Wiki 结构

```
wiki/
├── index.md              # 目录（自动更新）
├── cache.md              # 实体名缓存
├── log.md                # 操作日志
├── entities/             # 知识实体
│   ├── RAG.md
│   ├── MemoRAG.md
│   ├── Hongjin Qian.md
│   └── ...
└── raw/                  # 来源文档
    ├── arxiv-2409.05591.md
    ├── test-article.md
    └── ...
```

### 实体页面格式

```markdown
# EntityName
type: person | org | artifact | event | abstract

## Facts

- [[RAG]] 是一种为大型语言模型提供外部知识库上下文的技术... [[arxiv-2409.05591]]
- [[MemoRAG]] 在传统 [[RAG]] 基础上引入全局记忆模块... [[test-article]]
```

交叉引用使用 Obsidian `[[实体]]` 语法，方便导航。

## 实体类型

| 类型 | 描述 | 示例 |
|------|------|------|
| `person` | 研究者、作者 | Andrew Ng, Geoffrey Hinton |
| `org` | 组织机构 | Google DeepMind, 北京大学 |
| `artifact` | 工具、框架、数据集 | TensorFlow, PyTorch, MemoRAG |
| `event` | 会议、里程碑 | NeurIPS 2024, 图灵奖 |
| `abstract` | 概念、方法、理论 | RAG, 强化学习, GRPO |

## 配置说明

API keys 存储在 `~/.wiki-config.json`。

```bash
# 查看当前配置
uv run python .claude/shared/bin/wiki_config.py status

# 设置 OpenAI API key（LLM 提取必需）
uv run python .claude/shared/bin/wiki_config.py set openai_api_key YOUR_KEY

# 设置自定义 endpoint（可选，用于代理）
uv run python .claude/shared/bin/wiki_config.py set openai_base_url https://api.zhizengzheng.com/v1

# 设置 MinerU API key（可选，PDF 解析）
uv run python .claude/shared/bin/wiki_config.py set mineru_api_key YOUR_KEY

# 设置 DeepXiv token（可选，首次使用自动注册）
uv run python .claude/shared/bin/wiki_config.py set deepxiv_token YOUR_TOKEN
```

### 优先级顺序

环境变量 > 配置文件 > 默认值

| 变量 | 配置字段 |
|------|----------|
| `OPENAI_API_KEY` | `openai_api_key` |
| `OPENAI_BASE_URL` | `openai_base_url` |
| `MINERU_API_KEY` | `mineru_api_key` |
| `DEEPXIV_TOKEN` | `deepxiv_token` |

## API Key 来源

| 服务 | 用途 | 获取地址 |
|------|------|----------|
| **OpenAI** | LLM 提取（必需） | [platform.openai.com/api-keys](https://platform.openai.com/api-keys) |
| **MinerU** | PDF 转 Markdown（可选） | [mineru.net](https://mineru.net) |
| **DeepXiv** | arXiv 搜索（可选） | 自动注册，或 [data.rag.ac.cn](https://data.rag.ac.cn/register) |

> **提示：** DeepXiv 免费额度 = 10,000 次/天。首次使用会自动注册 token。

## 两阶段 LLM 提取

为了更好的提取质量：

```
Phase 1: Discovery（发现）
├── 输入：文档 + 已有实体缓存
├── 输出：实体名列表 + 类型
└── LLM 识别实体，不生成上下文

Phase 2: Context Generation（上下文生成，并行）
├── 输入：每个实体 + 文档 + 其他实体名
├── 输出：详细上下文（每个实体 100-200 字）
└── LLM 编写带来源引用的事实
```

这种分离提高了准确性，并支持并行处理。

## 项目结构

```
everything-is-knowledge/
├── .claude/
│   ├── CLAUDE.md                   # 项目指令
│   ├── skills/
│   │   ├── wiki-init/
│   │   ├── wiki-ingest-llm/
│   │   ├── wiki-ingest-paper/
│   │   ├── wiki-query/
│   │   ├── wiki-lint/
│   │   └── wiki-disambiguate/
│   └── shared/bin/
│       ├── wiki_config.py          # 配置 CLI
│       ├── pdf_reader.py           # MinerU PDF 解析
│       ├── web_fetcher.py          # Scrapling 网页抓取
│       ├── bilibili_fetcher.py     # Bilibili 转录获取
│       ├── deepxiv_fetcher.py      # DeepXiv 论文获取
│       └── llm_extractor.py        # OpenAI 提取
├── wiki/                           # 你的知识库
├── setup                           # 一键安装脚本
├── pyproject.toml                  # Python 依赖
└── README.md
```

## 依赖列表

- **uv** — 快速 Python 包管理器
- **Scrapling** — 带 anti-bot 隐蔽的网页抓取
- **MinerU** — PDF 转 Markdown
- **OpenAI** — LLM 提取（默认 gpt-4o-mini）
- **DeepXiv SDK** — arXiv 论文搜索
- **yt-dlp + Whisper** — Bilibili 视频转录

## 贡献

欢迎 PR！主要方向：
- 更多来源类型（YouTube、Twitter、播客）
- 更好的实体消歧
- 查询优化

## 许可证

MIT

---

**Made with Claude Code** — [claude.ai/code](https://claude.ai/code)
# Project Configuration


## Wiki Skills

Wiki skills are located in `.claude/skills/wiki/`. Each skill has a SKILL.md file that defines the workflow.

### Wiki skill routing

- "init wiki", "setup wiki", "initialize wiki" → invoke wiki-init
- "ingest this", "add to wiki", "process this PDF/URL" → invoke wiki-ingest
- "ingest with LLM", "batch ingest", "fast ingest" → invoke wiki-ingest-llm
- "search papers", "ingest paper", "arxiv paper" → invoke wiki-ingest-paper
- "query the wiki", "what does my wiki say", "search my knowledge" → invoke wiki-query
- "lint the wiki", "check wiki health", "wiki cleanup" → invoke wiki-lint


## Environment

Python dependencies managed by `uv`:
- `uv run python .claude/shared/bin/web_fetcher.py <url>`
- `uv run python .claude/shared/bin/pdf_reader.py <path>`
- `uv run python .claude/shared/bin/bilibili_fetcher.py <url>`

### Bilibili Video Transcription

Bilibili videos use Whisper API for transcription. Large audio files (>25MB) are automatically split using `imageio-ffmpeg` (bundled dependency, no system install needed).

Configuration:
- Run `/wiki-init` to configure the wiki
- Config file: `~/.wiki-config.json`
- CLI: `uv run python .claude/shared/bin/wiki_config.py status`

API keys can also be set via environment variables:
- `MINERU_API_KEY` - MinerU PDF parsing
- `OPENAI_API_KEY` - OpenAI Whisper transcription
- `OPENAI_BASE_URL` - Custom OpenAI endpoint
- `DEEPXIV_TOKEN` - DeepXiv paper search (auto-registered on first use)
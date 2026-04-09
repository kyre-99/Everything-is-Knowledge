# Project Configuration

## Skill routing

When the user's request matches an available skill, ALWAYS invoke it using the Skill
tool as your FIRST action. Do NOT answer directly, do NOT use other tools first.
The skill has specialized workflows that produce better results than ad-hoc answers.

Key routing rules:
- Product ideas, "is this worth building", brainstorming → invoke office-hours
- Bugs, errors, "why is this broken", 500 errors → invoke investigate
- Ship, deploy, push, create PR → invoke ship
- QA, test the site, find bugs → invoke qa
- Code review, check my diff → invoke review
- Update docs after shipping → invoke document-release
- Weekly retro → invoke retro
- Design system, brand → invoke design-consultation
- Visual audit, design polish → invoke design-review
- Architecture review → invoke plan-eng-review
- Save progress, checkpoint, resume → invoke checkpoint
- Code quality, health check → invoke health

## Wiki Skills

Wiki skills are located in `.claude/skills/wiki/`. Each skill has a SKILL.md file that defines the workflow.

### Wiki skill routing

- "init wiki", "setup wiki", "initialize wiki" → invoke wiki-init
- "ingest this", "add to wiki", "process this PDF/URL" → invoke wiki-ingest
- "query the wiki", "what does my wiki say", "search my knowledge" → invoke wiki-query
- "lint the wiki", "check wiki health", "wiki cleanup" → invoke wiki-lint

## Wiki Conventions

- Cross-references use Obsidian syntax: `[[Page Title]]`
- All wiki pages have YAML frontmatter with required fields
- `index.md` is the catalog — read it first for any query or ingest
- `log.md` is append-only — never delete entries
- Chinese filenames are supported (UTF-8)

## Environment

Python dependencies managed by `uv`:
- `uv run python .claude/skills/wiki-ingest/bin/web_fetcher.py <url>`
- `uv run python .claude/skills/wiki-ingest/bin/pdf_reader.py <path>`
- `uv run python .claude/skills/wiki-ingest/bin/bilibili_fetcher.py <url>`

Configuration:
- Run `/wiki-init` to configure the wiki
- Config file: `~/.wiki-config.json`
- CLI: `uv run python .claude/skills/wiki-ingest/bin/wiki_config.py status`

API keys can also be set via environment variables:
- `MINERU_API_KEY` - MinerU PDF parsing
- `OPENAI_API_KEY` - OpenAI Whisper transcription
- `OPENAI_BASE_URL` - Custom OpenAI endpoint
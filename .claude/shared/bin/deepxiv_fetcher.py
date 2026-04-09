#!/usr/bin/env python3
"""
DeepXiv paper fetcher.
Fetches papers from arXiv via DeepXiv API for wiki ingestion.
Returns markdown content ready for wiki processing.

Usage:
    uv run python bin/deepxiv_fetcher.py --search "agent memory" --limit 5
    uv run python bin/deepxiv_fetcher.py --arxiv 2409.05591
    uv run python bin/deepxiv_fetcher.py --arxiv 2409.05591 --brief
    uv run python bin/deepxiv_fetcher.py --arxiv 2409.05591 --section Introduction
    uv run python bin/deepxiv_fetcher.py --trending --days 7 --limit 10
    uv run python bin/deepxiv_fetcher.py --pmc PMC544940

Setup:
    Run /wiki-init to configure, or set DEEPXIV_TOKEN environment variable
    First use will auto-register a free token.
"""

import sys
import json
import argparse
from pathlib import Path
from typing import Optional

# Try to import deepxiv_sdk, fallback to local import
try:
    from deepxiv_sdk import Reader, APIError, AuthenticationError, RateLimitError
except ImportError:
    print("Error: deepxiv_sdk not installed. Install with: pip install deepxiv-sdk", file=sys.stderr)
    sys.exit(1)


def get_token() -> Optional[str]:
    """Get DeepXiv token from environment or config."""
    import os
    # deepxiv_sdk will auto-register if no token is provided
    # Check environment first
    token = os.environ.get("DEEPXIV_TOKEN")
    if token:
        return token

    # Check ~/.env file (where deepxiv CLI saves tokens)
    env_file = Path.home() / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if line.startswith("DEEPXIV_TOKEN="):
                return line.split("=", 1)[1].strip()

    # Return None - deepxiv_sdk Reader will auto-register
    return None


def search_papers(
    query: str,
    limit: int = 10,
    categories: Optional[str] = None,
    min_citations: Optional[int] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    token: Optional[str] = None,
) -> dict:
    """
    Search for papers on DeepXiv.

    Returns list of papers with arxiv_id, title, abstract, etc.
    """
    reader = Reader(token=token)

    cat_list = None
    if categories:
        cat_list = [c.strip() for c in categories.split(",")]

    try:
        results = reader.search(
            query=query,
            size=limit,
            categories=cat_list,
            min_citation=min_citations,
            date_from=date_from,
            date_to=date_to,
        )
        return {
            "success": True,
            "query": query,
            "total": results.get("total", 0),
            "results": results.get("results", []),
        }
    except AuthenticationError as e:
        return {"success": False, "error": f"认证失败: {str(e)}"}
    except RateLimitError as e:
        return {"success": False, "error": f"已达日限额: {str(e)}"}
    except APIError as e:
        return {"success": False, "error": str(e)}
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_paper(
    arxiv_id: str,
    mode: str = "full",
    section: Optional[str] = None,
    token: Optional[str] = None,
) -> dict:
    """
    Get paper content from DeepXiv.

    Modes:
    - brief: Quick summary (title, TLDR, keywords, citations, GitHub URL)
    - head: Metadata and structure (sections list, token counts)
    - section: Get specific section content
    - preview: First 10k characters
    - full: Complete markdown content
    - json: Complete structured JSON
    """
    reader = Reader(token=token)

    try:
        if mode == "brief":
            result = reader.brief(arxiv_id)
            return {
                "success": True,
                "arxiv_id": arxiv_id,
                "mode": "brief",
                "title": result.get("title", ""),
                "tldr": result.get("tldr", ""),
                "keywords": result.get("keywords", []),
                "citations": result.get("citations", 0),
                "github_url": result.get("github_url", ""),
                "src_url": result.get("src_url", ""),
                "publish_at": result.get("publish_at", ""),
            }

        elif mode == "head":
            result = reader.head(arxiv_id)
            return {
                "success": True,
                "arxiv_id": arxiv_id,
                "mode": "head",
                "title": result.get("title", ""),
                "abstract": result.get("abstract", ""),
                "authors": result.get("authors", []),
                "sections": result.get("sections", []),
                "categories": result.get("categories", []),
                "token_count": result.get("token_count", 0),
                "publish_at": result.get("publish_at", ""),
            }

        elif mode == "section":
            if not section:
                return {"success": False, "error": "Section name required for --section mode"}
            content = reader.section(arxiv_id, section)
            return {
                "success": True,
                "arxiv_id": arxiv_id,
                "mode": "section",
                "section": section,
                "content": content,
                "title": "",  # Will be filled by caller if needed
            }

        elif mode == "preview":
            result = reader.preview(arxiv_id)
            return {
                "success": True,
                "arxiv_id": arxiv_id,
                "mode": "preview",
                "content": result.get("content", ""),
                "is_truncated": result.get("is_truncated", False),
                "total_characters": result.get("total_characters", 0),
            }

        elif mode == "json":
            result = reader.json(arxiv_id)
            return {
                "success": True,
                "arxiv_id": arxiv_id,
                "mode": "json",
                "data": result,
            }

        else:  # full
            content = reader.raw(arxiv_id)
            if not content:
                # Try to get head for basic info
                head = reader.head(arxiv_id)
                if head:
                    # Construct basic markdown from head
                    content = f"# {head.get('title', arxiv_id)}\n\n"
                    authors = head.get("authors", [])
                    if authors:
                        author_names = [a.get("name", str(a)) if isinstance(a, dict) else str(a) for a in authors]
                        content += f"**Authors:** {', '.join(author_names)}\n\n"
                    content += f"**Categories:** {', '.join(head.get('categories', []))}\n\n"
                    content += f"## Abstract\n\n{head.get('abstract', 'No abstract')}\n\n"
                    sections = head.get("sections", [])
                    if sections:
                        content += "## Sections\n\n"
                        for s in sections:
                            name = s.get("name", str(s)) if isinstance(s, dict) else str(s)
                            content += f"- {name}\n"

            return {
                "success": True,
                "arxiv_id": arxiv_id,
                "mode": "full",
                "content": content,
                "title": "",  # Will be extracted from content or head
            }

    except AuthenticationError as e:
        return {"success": False, "error": f"认证失败: {str(e)}"}
    except RateLimitError as e:
        return {"success": False, "error": f"已达日限额: {str(e)}"}
    except APIError as e:
        return {"success": False, "error": str(e)}
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_trending(
    days: int = 7,
    limit: int = 30,
    token: Optional[str] = None,
) -> dict:
    """
    Get trending papers from DeepXiv.

    Returns list of hot papers with social metrics.
    """
    reader = Reader(token=token)

    try:
        result = reader.trending(days=days, limit=limit)
        return {
            "success": True,
            "days": days,
            "papers": result.get("papers", []),
            "total": result.get("total", 0),
            "generated_at": result.get("generated_at", ""),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_pmc(
    pmc_id: str,
    mode: str = "full",
    token: Optional[str] = None,
) -> dict:
    """
    Get PMC (PubMed Central) paper.

    Modes:
    - head: Metadata only
    - full: Complete structured JSON
    """
    reader = Reader(token=token)

    try:
        if mode == "head":
            result = reader.pmc_head(pmc_id)
            return {
                "success": True,
                "pmc_id": pmc_id,
                "mode": "head",
                "title": result.get("title", ""),
                "abstract": result.get("abstract", ""),
                "authors": result.get("authors", []),
                "doi": result.get("doi", ""),
                "publish_at": result.get("publish_at", ""),
            }
        else:  # full
            result = reader.pmc_full(pmc_id)
            # PMC JSON contains markdown content in 'content' field
            content = result.get("content", "")
            if not content:
                # Construct from structured data
                content = f"# {result.get('title', pmc_id)}\n\n"
                authors = result.get("authors", [])
                if authors:
                    content += f"**Authors:** {', '.join([a.get('name', str(a)) for a in authors])}\n\n"
                content += f"**DOI:** {result.get('doi', '')}\n\n"
                content += f"## Abstract\n\n{result.get('abstract', '')}\n\n"

            return {
                "success": True,
                "pmc_id": pmc_id,
                "mode": "full",
                "content": content,
                "title": result.get("title", ""),
                "data": result,
            }

    except Exception as e:
        return {"success": False, "error": str(e)}


def save_to_raw(content: str, title: str, source_id: str, raw_dir: str = "raw") -> str:
    """Save fetched content to raw directory."""
    raw_path = Path(raw_dir)
    raw_path.mkdir(exist_ok=True)

    # Generate safe filename
    safe_name = "".join(c if c.isalnum() or c in ('-', '_', ' ') else '' for c in title)
    safe_name = safe_name[:60].strip().replace(' ', '-')

    if not safe_name:
        safe_name = source_id.replace('/', '-').replace(':', '-')

    md_filename = f"{safe_name}.md"
    md_path = raw_path / md_filename
    md_path.write_text(content, encoding="utf-8")

    return str(md_path)


def main():
    parser = argparse.ArgumentParser(
        description="Fetch papers from DeepXiv (arXiv/PMC)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Search papers:
    uv run python bin/deepxiv_fetcher.py --search "agent memory" --limit 5
    uv run python bin/deepxiv_fetcher.py --search "transformer" --categories cs.AI,cs.CL

  Get paper by arXiv ID:
    uv run python bin/deepxiv_fetcher.py --arxiv 2409.05591
    uv run python bin/deepxiv_fetcher.py --arxiv 2409.05591 --brief
    uv run python bin/deepxiv_fetcher.py --arxiv 2409.05591 --section Introduction
    uv run python bin/deepxiv_fetcher.py --arxiv 2409.05591 --preview

  Get trending papers:
    uv run python bin/deepxiv_fetcher.py --trending --days 7 --limit 10

  Get PMC paper:
    uv run python bin/deepxiv_fetcher.py --pmc PMC544940

Output formats:
  --json         Output JSON only
  --save-raw     Save markdown to raw/ directory (default: True)
  --no-save      Don't save to raw/
        """
    )

    # Action arguments
    parser.add_argument("--search", "-s", help="Search query for papers")
    parser.add_argument("--arxiv", "-a", help="arXiv paper ID (e.g., 2409.05591)")
    parser.add_argument("--trending", "-t", action="store_true", help="Get trending papers")
    parser.add_argument("--pmc", "-p", help="PMC paper ID (e.g., PMC544940)")

    # Options
    parser.add_argument("--limit", "-l", type=int, default=10, help="Number of results (default: 10)")
    parser.add_argument("--categories", "-c", help="Filter by categories (comma-separated)")
    parser.add_argument("--min-citations", type=int, help="Minimum citation count")
    parser.add_argument("--date-from", help="Date from (YYYY-MM-DD)")
    parser.add_argument("--date-to", help="Date to (YYYY-MM-DD)")
    parser.add_argument("--days", type=int, default=7, help="Trending days (7, 14, 30)")
    parser.add_argument("--section", help="Section name to fetch")
    parser.add_argument("--brief", "-b", action="store_true", help="Get brief info only")
    parser.add_argument("--preview", action="store_true", help="Get preview (~10k chars)")
    parser.add_argument("--json", "-j", action="store_true", help="Output JSON only")
    parser.add_argument("--no-save", action="store_true", help="Don't save to raw/")
    parser.add_argument("--raw-dir", default="raw", help="Directory to save markdown")

    args = parser.parse_args()

    # Get token
    token = get_token()

    # Determine action
    if args.search:
        result = search_papers(
            query=args.search,
            limit=args.limit,
            categories=args.categories,
            min_citations=args.min_citations,
            date_from=args.date_from,
            date_to=args.date_to,
            token=token,
        )

        if result.get("success"):
            # For search results, optionally fetch brief info for each paper
            if not args.json:
                print(f"\nFound {result['total']} papers for '{args.search}':\n")
                for i, paper in enumerate(result.get("results", []), 1):
                    arxiv_id = paper.get("arxiv_id", "N/A")
                    title = paper.get("title", "No title")
                    citations = paper.get("citation", 0)
                    abstract = paper.get("abstract", "")[:150]
                    print(f"{i}. {title}")
                    print(f"   arXiv: {arxiv_id} | Citations: {citations}")
                    print(f"   {abstract}...")
                    print()

        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif args.arxiv:
        # Determine mode
        if args.brief:
            mode = "brief"
        elif args.preview:
            mode = "preview"
        elif args.section:
            mode = "section"
        else:
            mode = "full"

        result = get_paper(
            arxiv_id=args.arxiv,
            mode=mode,
            section=args.section,
            token=token,
        )

        if result.get("success") and result.get("content"):
            # Save to raw if requested
            if not args.no_save:
                title = result.get("title", args.arxiv)
                if not title:
                    # Extract title from content
                    lines = result["content"].split("\n")
                    for line in lines:
                        if line.startswith("# "):
                            title = line[2:].strip()
                            break

                saved_path = save_to_raw(
                    result["content"],
                    title,
                    f"arxiv-{args.arxiv}",
                    args.raw_dir,
                )
                result["saved_to"] = saved_path
                print(f"Saved to: {saved_path}", file=sys.stderr)

        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif args.trending:
        result = get_trending(
            days=args.days,
            limit=args.limit,
            token=token,
        )

        if result.get("success") and not args.json:
            print(f"\n📊 Trending Papers (Last {args.days} Days)\n")
            print(f"Generated: {result.get('generated_at', 'N/A')}")
            print(f"Total: {result.get('total', 0)}\n")

            for i, paper in enumerate(result.get("papers", []), 1):
                arxiv_id = paper.get("arxiv_id", "N/A")
                stats = paper.get("stats", {})
                views = stats.get("total_views", 0)
                print(f"{i}. arXiv:{arxiv_id} | Views: {views}")

        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif args.pmc:
        mode = "full"
        result = get_pmc(
            pmc_id=args.pmc,
            mode=mode,
            token=token,
        )

        if result.get("success") and result.get("content"):
            if not args.no_save:
                title = result.get("title", args.pmc)
                saved_path = save_to_raw(
                    result["content"],
                    title,
                    f"pmc-{args.pmc}",
                    args.raw_dir,
                )
                result["saved_to"] = saved_path
                print(f"Saved to: {saved_path}", file=sys.stderr)

        print(json.dumps(result, ensure_ascii=False, indent=2))

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
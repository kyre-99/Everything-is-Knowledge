#!/usr/bin/env python3
"""
Wiki Ingest Paper CLI - Search and ingest academic papers.
Full pipeline: search → select → fetch → extract → write wiki.

Usage:
    # Search and interactively select papers
    uv run python wiki_ingest_paper.py --search "agent memory"

    # Direct arXiv ID import
    uv run python wiki_ingest_paper.py --arxiv 2409.05591

    # Trending papers
    uv run python wiki_ingest_paper.py --trending --days 7 --limit 10

    # Batch import multiple papers
    uv run python wiki_ingest_paper.py --arxiv 2409.05591 2409.05592 2409.05593
"""

import sys
import json
import os
import argparse
import time
from pathlib import Path
from typing import Optional, List

# Import deepxiv_sdk for paper search
try:
    from deepxiv_sdk import Reader, APIError
except ImportError:
    print("Error: deepxiv_sdk not installed. Run: pip install deepxiv-sdk", file=sys.stderr)
    sys.exit(1)

# Import from wiki_ingest_llm
SCRIPT_DIR = Path(__file__).parent
WIKI_INGEST_LLM_DIR = SCRIPT_DIR.parent.parent / "wiki-ingest-llm" / "bin"
sys.path.insert(0, str(WIKI_INGEST_LLM_DIR))

from wiki_ingest_llm import (
    process_source,
    write_all_wiki_pages,
    append_log_md,
    parse_index_md,
    get_openai_config,
)
from openai import OpenAI


def get_token() -> Optional[str]:
    """Get DeepXiv token from environment or config."""
    token = os.environ.get("DEEPXIV_TOKEN")
    if token:
        return token

    env_file = Path.home() / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if line.startswith("DEEPXIV_TOKEN="):
                return line.split("=", 1)[1].strip()

    return None


def search_papers_interactive(
    query: str,
    limit: int = 10,
    categories: Optional[str] = None,
    min_citations: Optional[int] = None,
    token: Optional[str] = None,
) -> List[str]:
    """
    Search for papers and let user select which to ingest.

    Returns list of selected arXiv IDs.
    """
    reader = Reader(token=token)

    cat_list = None
    if categories:
        cat_list = [c.strip() for c in categories.split(",")]

    print(f"\n🔍 Searching for: '{query}'...\n", file=sys.stderr)

    try:
        results = reader.search(
            query=query,
            size=limit,
            categories=cat_list,
            min_citation=min_citations,
        )
    except APIError as e:
        print(f"❌ Search failed: {e}", file=sys.stderr)
        return []

    total = results.get("total", 0)
    papers = results.get("results", [])

    if not papers:
        print(f"No papers found for '{query}'", file=sys.stderr)
        return []

    print(f"Found {total} papers (showing {len(papers)}):\n")

    # Display results
    for i, paper in enumerate(papers, 1):
        arxiv_id = paper.get("arxiv_id", "N/A")
        title = paper.get("title", "No title")
        citations = paper.get("citation", 0)
        abstract = paper.get("abstract", "")[:150]

        print(f"{i}. {title}")
        print(f"   arXiv: {arxiv_id} | Citations: {citations}")
        print(f"   {abstract}...")
        print()

    # Interactive selection
    print("Enter paper numbers to ingest (e.g., '1,3,5' or '1-3' or 'all'): ", end="")
    try:
        selection = input().strip().lower()
    except EOFError:
        # Non-interactive mode, select all
        selection = "all"

    if selection == "all" or selection == "":
        return [p.get("arxiv_id") for p in papers if p.get("arxiv_id")]

    selected_ids = []

    # Parse selection
    if "-" in selection:
        # Range: 1-3
        parts = selection.split("-")
        if len(parts) == 2:
            start = int(parts[0].strip())
            end = int(parts[1].strip())
            for i in range(start - 1, min(end, len(papers))):
                arxiv_id = papers[i].get("arxiv_id")
                if arxiv_id:
                    selected_ids.append(arxiv_id)
    else:
        # List: 1,3,5
        for num in selection.split(","):
            try:
                idx = int(num.strip()) - 1
                if 0 <= idx < len(papers):
                    arxiv_id = papers[idx].get("arxiv_id")
                    if arxiv_id:
                        selected_ids.append(arxiv_id)
            except ValueError:
                continue

    return selected_ids


def ingest_papers(
    arxiv_ids: List[str],
    client: OpenAI,
    existing_entities: List[dict],
    existing_concepts: List[dict],
    wiki_dir: Path,
    model: str = "gpt-4o-mini",
) -> dict:
    """
    Ingest multiple papers: fetch, extract, write wiki.

    Returns summary of what was created/updated.
    """
    results = []
    errors = []

    print(f"\n📚 Ingesting {len(arxiv_ids)} papers...\n", file=sys.stderr)

    for i, arxiv_id in enumerate(arxiv_ids, 1):
        print(f"[{i}/{len(arxiv_ids)}] Processing arXiv:{arxiv_id}...", file=sys.stderr)

        try:
            result = process_source(
                arxiv_id,
                client,
                existing_entities,
                existing_concepts,
                model,
            )

            # Mark source type
            result["_source_type"] = "paper"
            result["_source_url"] = f"https://arxiv.org/abs/{arxiv_id}"

            if "error" in result and result.get("entities") is None:
                errors.append({"source": arxiv_id, "error": result.get("error")})
                print(f"  ❌ Error: {result.get('error')}", file=sys.stderr)
            else:
                results.append(result)
                title = result.get("source", {}).get("title", arxiv_id)
                entities_count = len(result.get("entities", []))
                concepts_count = len(result.get("concepts", []))
                print(f"  ✅ {title}: {entities_count} entities, {concepts_count} concepts", file=sys.stderr)

        except Exception as e:
            errors.append({"source": arxiv_id, "error": str(e)})
            print(f"  ❌ Error: {e}", file=sys.stderr)

    # Write wiki pages
    if results:
        print(f"\n📝 Writing wiki pages to {wiki_dir}...", file=sys.stderr)
        summary = write_all_wiki_pages(results, wiki_dir)
        append_log_md(results, errors, wiki_dir)

        print(f"Created: sources[{summary['sources_created']}], entities[{summary['entities_created']}], concepts[{summary['concepts_created']}]", file=sys.stderr)
    else:
        summary = {
            "sources_created": 0,
            "sources_updated": 0,
            "entities_created": 0,
            "entities_updated": 0,
            "concepts_created": 0,
            "concepts_updated": 0,
        }

    return {
        "results": results,
        "errors": errors,
        "summary": summary,
    }


def get_trending_papers(
    days: int = 7,
    limit: int = 20,
    token: Optional[str] = None,
) -> List[str]:
    """
    Get trending papers and let user select.

    Returns list of selected arXiv IDs.
    """
    reader = Reader(token=token)

    print(f"\n🔥 Fetching trending papers (last {days} days)...\n", file=sys.stderr)

    try:
        result = reader.trending(days=days, limit=limit)
    except APIError as e:
        print(f"❌ Failed to get trending: {e}", file=sys.stderr)
        return []

    papers = result.get("papers", [])

    if not papers:
        print("No trending papers found", file=sys.stderr)
        return []

    print(f"Trending papers (generated: {result.get('generated_at', 'N/A')}):\n")

    for i, paper in enumerate(papers[:limit], 1):
        arxiv_id = paper.get("arxiv_id", "N/A")
        rank = paper.get("rank", "?")
        stats = paper.get("stats", {})
        views = stats.get("total_views", 0)

        print(f"{i}. arXiv:{arxiv_id} | Rank #{rank} | Views: {views}")

    # Interactive selection
    print("\nEnter paper numbers to ingest (e.g., '1,3,5' or '1-5' or 'all'): ", end="")
    try:
        selection = input().strip().lower()
    except EOFError:
        selection = "all"

    if selection == "all" or selection == "":
        return [p.get("arxiv_id") for p in papers if p.get("arxiv_id")]

    selected_ids = []

    if "-" in selection:
        parts = selection.split("-")
        if len(parts) == 2:
            start = int(parts[0].strip())
            end = int(parts[1].strip())
            for i in range(start - 1, min(end, len(papers))):
                arxiv_id = papers[i].get("arxiv_id")
                if arxiv_id:
                    selected_ids.append(arxiv_id)
    else:
        for num in selection.split(","):
            try:
                idx = int(num.strip()) - 1
                if 0 <= idx < len(papers):
                    arxiv_id = papers[idx].get("arxiv_id")
                    if arxiv_id:
                        selected_ids.append(arxiv_id)
            except ValueError:
                continue

    return selected_ids


def main():
    parser = argparse.ArgumentParser(
        description="Search and ingest academic papers into wiki",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Search and interactively select:
    uv run python wiki_ingest_paper.py --search "agent memory"
    uv run python wiki_ingest_paper.py --search "RAG" --categories cs.CL,cs.AI --limit 20

  Direct import by arXiv ID:
    uv run python wiki_ingest_paper.py --arxiv 2409.05591
    uv run python wiki_ingest_paper.py --arxiv 2409.05591 2409.05592 2409.05593

  Trending papers:
    uv run python wiki_ingest_paper.py --trending --days 7 --limit 20
        """
    )

    # Action arguments
    parser.add_argument("--search", "-s", help="Search query for papers")
    parser.add_argument("--arxiv", "-a", nargs="+", help="arXiv paper ID(s) to ingest directly")
    parser.add_argument("--trending", "-t", action="store_true", help="Get trending papers")

    # Search options
    parser.add_argument("--limit", "-l", type=int, default=10, help="Number of search results (default: 10)")
    parser.add_argument("--categories", "-c", help="Filter by arXiv categories (comma-separated)")
    parser.add_argument("--min-citations", type=int, help="Minimum citation count")
    parser.add_argument("--days", type=int, default=7, help="Trending days (7, 14, 30)")

    # Ingest options
    parser.add_argument("--model", "-m", default="gpt-4o-mini", help="LLM model for extraction")
    parser.add_argument("--index", default="wiki/index.md", help="Path to wiki index.md")
    parser.add_argument("--no-write", action="store_true", help="Skip writing wiki pages, only output JSON")

    args = parser.parse_args()

    # Get DeepXiv token
    token = get_token()

    # Get OpenAI config
    api_key, base_url = get_openai_config()

    if not api_key:
        print("Error: OpenAI API key not configured", file=sys.stderr)
        print("Set via: export OPENAI_API_KEY=your-key", file=sys.stderr)
        sys.exit(1)

    client = OpenAI(api_key=api_key, base_url=base_url, timeout=60.0)

    # Parse existing wiki
    index_path = Path(args.index)
    wiki_dir = index_path.parent
    existing_entities, existing_concepts, _ = parse_index_md(index_path)
    print(f"Loaded {len(existing_entities)} entities, {len(existing_concepts)} concepts from index.md", file=sys.stderr)

    # Determine action
    arxiv_ids = []

    if args.search:
        arxiv_ids = search_papers_interactive(
            query=args.search,
            limit=args.limit,
            categories=args.categories,
            min_citations=args.min_citations,
            token=token,
        )

    elif args.arxiv:
        arxiv_ids = args.arxiv

    elif args.trending:
        arxiv_ids = get_trending_papers(
            days=args.days,
            limit=args.limit,
            token=token,
        )

    else:
        parser.print_help()
        sys.exit(1)

    if not arxiv_ids:
        print("\nNo papers selected.", file=sys.stderr)
        sys.exit(0)

    # Ingest papers
    result = ingest_papers(
        arxiv_ids=arxiv_ids,
        client=client,
        existing_entities=existing_entities,
        existing_concepts=existing_concepts,
        wiki_dir=wiki_dir,
        model=args.model,
    )

    # Output JSON
    output = {
        "arxiv_ids": arxiv_ids,
        "summary": result["summary"],
        "errors": result["errors"],
    }

    print("\n" + json.dumps(output, ensure_ascii=False, indent=2))

    # Exit code
    if result["results"]:
        print(f"\n✅ Successfully ingested {len(result['results'])} papers!", file=sys.stderr)
        sys.exit(0)
    else:
        print(f"\n❌ No papers were ingested.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
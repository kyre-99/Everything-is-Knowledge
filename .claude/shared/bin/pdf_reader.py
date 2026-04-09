#!/usr/bin/env python3
"""
PDF reader using MinerU API.
Parses PDFs and returns Markdown for Claude Code processing.

Usage:
    uv run python bin/pdf_reader.py "raw/paper.pdf"
    uv run python bin/pdf_reader.py "https://example.com/paper.pdf"

Setup:
    Run /wiki-init to configure, or set MINERU_API_KEY environment variable
"""

import sys
import json
import os
import time
import argparse
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import requests

# Import unified config
try:
    from wiki_config import get_config, get_mineru_api_key
except ImportError:
    # Fallback for direct script execution
    import importlib.util
    spec = importlib.util.spec_from_file_location("wiki_config", Path(__file__).parent / "wiki_config.py")
    wiki_config = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(wiki_config)
    get_config = wiki_config.get_config
    get_mineru_api_key = wiki_config.get_mineru_api_key


def get_base_url() -> str:
    """Get MinerU API base URL from config."""
    config = get_config()
    return config.get("mineru_base_url", "https://mineru.net/api/v1/agent")


# MinerU API endpoints (base URL from config)
MINERU_BASE_URL = get_base_url()


def is_url(path: str) -> bool:
    """Check if path is a URL."""
    try:
        result = urlparse(path)
        return result.scheme in ("http", "https")
    except Exception:
        return False


def parse_pdf(
    pdf_path: str,
    language: str = "ch",
    page_range: Optional[str] = None,
    enable_table: bool = True,
    is_ocr: bool = False,
    enable_formula: bool = True
) -> dict:
    """
    Parse PDF using MinerU API.

    Args:
        pdf_path: Path to PDF file or URL
        language: Document language ("ch" for Chinese, "en" for English)
        page_range: Page range (e.g., "1-10")
        enable_table: Enable table extraction
        is_ocr: Force OCR
        enable_formula: Enable formula extraction

    Returns:
        dict with title, content (markdown), images, tables, metadata
    """
    api_key = get_mineru_api_key()
    if not api_key:
        return {
            "title": "",
            "content": "",
            "images": [],
            "tables": [],
            "metadata": {},
            "success": False,
            "error": "MinerU API key not found. Set MINERU_API_KEY or save to ~/.mineru_api_key"
        }

    if is_url(pdf_path):
        return parse_pdf_url(pdf_path, api_key)
    else:
        return parse_pdf_file(
            pdf_path, api_key, language, page_range, enable_table, is_ocr, enable_formula
        )


def parse_pdf_file(
    pdf_path: str,
    api_key: str,
    language: str,
    page_range: Optional[str],
    enable_table: bool,
    is_ocr: bool,
    enable_formula: bool
) -> dict:
    """
    Upload and parse local PDF file using MinerU API.

    Flow:
    1. Get signed upload URL
    2. PUT file to OSS
    3. Poll for result
    """
    pdf_file = Path(pdf_path)
    if not pdf_file.exists():
        return {
            "title": "",
            "content": "",
            "images": [],
            "tables": [],
            "metadata": {},
            "success": False,
            "error": f"PDF file not found: {pdf_path}"
        }

    try:
        file_name = pdf_file.name

        # Step 1: Get signed upload URL
        data = {
            "file_name": file_name,
            "language": language,
            "enable_table": enable_table,
            "is_ocr": is_ocr,
            "enable_formula": enable_formula
        }
        if page_range:
            data["page_range"] = page_range

        headers = {"Content-Type": "application/json"}

        resp = requests.post(
            f"{MINERU_BASE_URL}/parse/file",
            headers=headers,
            json=data,
            timeout=30
        )

        result = resp.json()
        if result.get("code") != 0:
            return {
                "title": "",
                "content": "",
                "images": [],
                "tables": [],
                "metadata": {},
                "success": False,
                "error": f"MinerU API error: {result.get('msg', 'Unknown error')}"
            }

        task_id = result["data"]["task_id"]
        file_url = result["data"]["file_url"]

        # Step 2: Upload file to OSS (with retry)
        upload_success = False
        max_retries = 3
        for attempt in range(max_retries):
            try:
                with open(pdf_file, "rb") as f:
                    put_resp = requests.put(file_url, data=f, timeout=180)
                    if put_resp.status_code in (200, 201):
                        upload_success = True
                        break
                    else:
                        if attempt < max_retries - 1:
                            time.sleep(2)
                            continue
                        return {
                            "title": "",
                            "content": "",
                            "images": [],
                            "tables": [],
                            "metadata": {},
                            "success": False,
                            "error": f"File upload failed: HTTP {put_resp.status_code} - {put_resp.text[:200]}"
                        }
            except requests.exceptions.SSLError as e:
                if attempt < max_retries - 1:
                    time.sleep(3)
                    continue
                return {
                    "title": "",
                    "content": "",
                    "images": [],
                    "tables": [],
                    "metadata": {},
                    "success": False,
                    "error": f"SSL error uploading to OSS: {str(e)}"
                }

        if not upload_success:
            return {
                "title": "",
                "content": "",
                "images": [],
                "tables": [],
                "metadata": {},
                "success": False,
                "error": "File upload failed after retries"
            }

        # Step 3: Poll for result
        return poll_and_retrieve(task_id, api_key, pdf_file.stem)

    except requests.exceptions.Timeout:
        return {
            "title": "",
            "content": "",
            "images": [],
            "tables": [],
            "metadata": {},
            "success": False,
            "error": "MinerU API request timed out"
        }
    except Exception as e:
        return {
            "title": "",
            "content": "",
            "images": [],
            "tables": [],
            "metadata": {},
            "success": False,
            "error": str(e)
        }


def parse_pdf_url(url: str, api_key: str) -> dict:
    """
    Parse PDF from URL using MinerU API.
    Note: URL must be publicly accessible.
    """
    try:
        headers = {"Content-Type": "application/json"}
        data = {
            "url": url,
            "language": "ch"
        }

        resp = requests.post(
            f"{MINERU_BASE_URL}/parse/url",
            headers=headers,
            json=data,
            timeout=60
        )

        result = resp.json()
        if result.get("code") != 0:
            return {
                "title": "",
                "content": "",
                "images": [],
                "tables": [],
                "metadata": {},
                "success": False,
                "error": f"MinerU API error: {result.get('msg', 'Unknown error')}"
            }

        task_id = result["data"]["task_id"]
        return poll_and_retrieve(task_id, api_key, "document")

    except Exception as e:
        return {
            "title": "",
            "content": "",
            "images": [],
            "tables": [],
            "metadata": {},
            "success": False,
            "error": str(e)
        }


def poll_and_retrieve(task_id: str, api_key: str, default_title: str) -> dict:
    """
    Poll MinerU API for task completion and retrieve result.
    """
    state_labels = {
        "pending": "排队中",
        "running": "解析中",
        "waiting-file": "等待文件上传",
    }

    timeout = 300  # 5 minutes max
    interval = 3  # poll every 3 seconds
    start = time.time()

    while time.time() - start < timeout:
        resp = requests.get(
            f"{MINERU_BASE_URL}/parse/{task_id}",
            timeout=30
        )

        result = resp.json()
        state = result["data"]["state"]

        if state == "done":
            markdown_url = result["data"]["markdown_url"]
            md_resp = requests.get(markdown_url, timeout=60)
            content = md_resp.text

            return {
                "title": result["data"].get("title", default_title),
                "content": content,
                "images": result["data"].get("images", []),
                "tables": result["data"].get("tables", []),
                "metadata": {
                    "page_count": result["data"].get("page_count"),
                    "language": result["data"].get("language")
                },
                "success": True
            }

        if state == "failed":
            return {
                "title": "",
                "content": "",
                "images": [],
                "tables": [],
                "metadata": {},
                "success": False,
                "error": result["data"].get("err_msg", "解析失败")
            }

        # Still processing, wait and retry
        time.sleep(interval)

    return {
        "title": "",
        "content": "",
        "images": [],
        "tables": [],
        "metadata": {},
        "success": False,
        "error": f"轮询超时 ({timeout}s)，task_id: {task_id}"
    }


def main():
    parser = argparse.ArgumentParser(description="Parse PDF using MinerU API")
    parser.add_argument("pdf", help="Path to PDF file or URL")
    parser.add_argument("--lang", default="ch", help="Document language (ch/en)")
    parser.add_argument("--pages", help="Page range (e.g., '1-10')")
    parser.add_argument("--output", "-o", help="Output file (default: stdout)")
    parser.add_argument("--no-save", action="store_true", help="Don't save parsed markdown to raw folder")
    parser.add_argument("--raw-dir", default="raw", help="Directory to save parsed markdown (default: raw)")

    args = parser.parse_args()

    result = parse_pdf(
        args.pdf,
        language=args.lang,
        page_range=args.pages
    )

    # Auto-save parsed markdown to raw folder
    if result.get("success") and not args.no_save:
        raw_dir = Path(args.raw_dir)
        raw_dir.mkdir(exist_ok=True)

        # Generate filename from PDF name or URL
        if is_url(args.pdf):
            # Use title from result or URL-derived name
            title = result.get("title", "document")
            safe_name = "".join(c if c.isalnum() or c in ('-', '_', ' ') else '' for c in title)
            safe_name = safe_name[:60].strip().replace(' ', '-')
            md_filename = f"{safe_name or 'document'}.md"
        else:
            # Use original PDF filename with .md extension
            pdf_name = Path(args.pdf).stem
            md_filename = f"{pdf_name}.md"

        md_path = raw_dir / md_filename
        md_path.write_text(result["content"], encoding="utf-8")
        result["saved_to"] = str(md_path)

    output = json.dumps(result, ensure_ascii=False, indent=2)

    if args.output:
        Path(args.output).write_text(output, encoding="utf-8")
        print(f"Saved to {args.output}")
    else:
        print(output)


if __name__ == "__main__":
    main()
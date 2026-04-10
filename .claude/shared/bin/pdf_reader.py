#!/usr/bin/env python3
"""
PDF reader using MinerU API.
Parses PDFs and returns Markdown for Claude Code processing.

Supports both API modes:
- 精准解析 API (default): 200MB/600页限制，需要Token，支持vlm模型
- Agent 轻量 API: 10MB/20页限制，无需Token

Usage:
    uv run python bin/pdf_reader.py "raw/paper.pdf"
    uv run python bin/pdf_reader.py "https://example.com/paper.pdf"
    uv run python bin/pdf_reader.py "raw/paper.pdf" --agent  # 使用轻量API
    uv run python bin/pdf_reader.py "raw/paper.pdf" --model vlm  # 使用vlm模型

Setup:
    Run /wiki-init to configure, or set MINERU_API_KEY environment variable
"""

import sys
import json
import os
import time
import argparse
import zipfile
import tempfile
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


# API endpoints
# 精准解析 API (200MB/600页，需要Token)
PRECISE_BASE_URL = "https://mineru.net/api/v4/extract/task"
# Agent 轻量 API (10MB/20页，无需Token)
AGENT_BASE_URL = "https://mineru.net/api/v1/agent"


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
    enable_formula: bool = True,
    use_agent: bool = False,
    model_version: str = "vlm",
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
        use_agent: Use Agent lightweight API (10MB/20页限制)
        model_version: Model version for precise API ("pipeline" or "vlm")

    Returns:
        dict with title, content (markdown), images, tables, metadata
    """
    api_key = get_mineru_api_key()

    if use_agent:
        # Agent API 不需要Token，但有大小限制
        if is_url(pdf_path):
            return parse_pdf_agent_url(pdf_path, language, page_range, enable_table, is_ocr, enable_formula)
        else:
            return parse_pdf_agent_file(pdf_path, language, page_range, enable_table, is_ocr, enable_formula)
    else:
        # 精准解析 API 需要Token
        if not api_key:
            return {
                "title": "",
                "content": "",
                "images": [],
                "tables": [],
                "metadata": {},
                "success": False,
                "error": "MinerU API key not found. Set MINERU_API_KEY or run /wiki-init to configure."
            }

        if is_url(pdf_path):
            return parse_pdf_precise_url(pdf_path, api_key, language, page_range, enable_table, is_ocr, enable_formula, model_version)
        else:
            return parse_pdf_precise_file(pdf_path, api_key, language, page_range, enable_table, is_ocr, enable_formula, model_version)


def parse_pdf_precise_file(
    pdf_path: str,
    api_key: str,
    language: str,
    page_range: Optional[str],
    enable_table: bool,
    is_ocr: bool,
    enable_formula: bool,
    model_version: str,
) -> dict:
    """
    Upload and parse local PDF file using 精准解析 API.

    限制: 200MB/600页
    支持: vlm/pipeline 模型

    Flow:
    1. 申请上传URL (batch接口)
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

    # Check file size
    file_size_mb = pdf_file.stat().st_size / (1024 * 1024)
    if file_size_mb > 200:
        return {
            "title": "",
            "content": "",
            "images": [],
            "tables": [],
            "metadata": {},
            "success": False,
            "error": f"文件大小 {file_size_mb:.1f}MB 超过精准API限制 (200MB)"
        }

    try:
        file_name = pdf_file.name

        # Step 1: 申请批量上传URL
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }

        data = {
            "files": [{"name": file_name}],
            "model_version": model_version,
            "language": language,
            "enable_table": enable_table,
            "enable_formula": enable_formula,
        }
        if is_ocr:
            data["files"][0]["is_ocr"] = True
        if page_range:
            data["files"][0]["page_ranges"] = page_range

        resp = requests.post(
            "https://mineru.net/api/v4/file-urls/batch",
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

        batch_id = result["data"]["batch_id"]
        file_url = result["data"]["file_urls"][0]

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

        # Step 3: Poll for result (batch mode)
        return poll_batch_result(batch_id, api_key, pdf_file.stem)

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


def parse_pdf_precise_url(url: str, api_key: str, language: str, page_range: Optional[str], enable_table: bool, is_ocr: bool, enable_formula: bool, model_version: str) -> dict:
    """
    Parse PDF from URL using 精准解析 API.

    限制: 200MB/600页
    支持: vlm/pipeline 模型
    """
    try:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        data = {
            "url": url,
            "model_version": model_version,
            "language": language,
            "enable_table": enable_table,
            "enable_formula": enable_formula,
        }
        if is_ocr:
            data["is_ocr"] = True
        if page_range:
            data["page_ranges"] = page_range

        resp = requests.post(
            PRECISE_BASE_URL,
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
        return poll_precise_result(task_id, api_key, "document")

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


def poll_precise_result(task_id: str, api_key: str, default_title: str) -> dict:
    """
    Poll 精准解析 API for task completion and retrieve result.

    Returns full_zip_url containing markdown, json, and optional extra formats.
    """
    state_labels = {
        "pending": "排队中",
        "running": "解析中",
        "converting": "格式转换中",
    }

    timeout = 600  # 10 minutes max for large files
    interval = 5  # poll every 5 seconds
    start = time.time()

    while time.time() - start < timeout:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }

        resp = requests.get(
            f"{PRECISE_BASE_URL}/{task_id}",
            headers=headers,
            timeout=30
        )

        result = resp.json()
        state = result["data"]["state"]
        elapsed = int(time.time() - start)

        if state == "done":
            full_zip_url = result["data"]["full_zip_url"]

            # Download and extract zip
            zip_resp = requests.get(full_zip_url, timeout=120)

            with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp_zip:
                tmp_zip.write(zip_resp.content)
                tmp_zip_path = tmp_zip.name

            try:
                with zipfile.ZipFile(tmp_zip_path, 'r') as zf:
                    # Find markdown file (usually full.md)
                    md_files = [f for f in zf.namelist() if f.endswith('.md')]
                    content = ""
                    if md_files:
                        content = zf.read(md_files[0]).decode('utf-8')

                    # Extract images if any
                    images = [f for f in zf.namelist() if f.endswith(('.png', '.jpg', '.jpeg'))]

                    # Strip .pdf extension from title if present
                    title = result["data"].get("data_id", default_title)
                    if title.lower().endswith(".pdf"):
                        title = title[:-4]

                    return {
                        "title": title,
                        "content": content,
                        "images": images,
                        "tables": [],
                        "metadata": {
                            "page_count": result["data"].get("extract_progress", {}).get("total_pages"),
                            "zip_url": full_zip_url,
                        },
                        "success": True
                    }
            finally:
                os.unlink(tmp_zip_path)

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
        print(f"[{elapsed}s] {state_labels.get(state, state)}...", file=sys.stderr)
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


def poll_batch_result(batch_id: str, api_key: str, default_title: str) -> dict:
    """
    Poll 批量解析结果 API.

    Uses /api/v4/extract-results/batch/{batch_id}
    """
    state_labels = {
        "waiting-file": "等待文件上传",
        "pending": "排队中",
        "running": "解析中",
        "converting": "格式转换中",
    }

    timeout = 600  # 10 minutes max
    interval = 5
    start = time.time()

    while time.time() - start < timeout:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }

        resp = requests.get(
            f"https://mineru.net/api/v4/extract-results/batch/{batch_id}",
            headers=headers,
            timeout=30
        )

        result = resp.json()
        extract_results = result.get("data", {}).get("extract_result", [])

        if not extract_results:
            time.sleep(interval)
            continue

        # Get first file result
        file_result = extract_results[0]
        state = file_result.get("state", "")
        elapsed = int(time.time() - start)

        if state == "done":
            full_zip_url = file_result["full_zip_url"]

            # Download and extract zip
            zip_resp = requests.get(full_zip_url, timeout=120)

            with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp_zip:
                tmp_zip.write(zip_resp.content)
                tmp_zip_path = tmp_zip.name

            try:
                with zipfile.ZipFile(tmp_zip_path, 'r') as zf:
                    md_files = [f for f in zf.namelist() if f.endswith('.md')]
                    content = ""
                    if md_files:
                        content = zf.read(md_files[0]).decode('utf-8')

                    images = [f for f in zf.namelist() if f.endswith(('.png', '.jpg', '.jpeg'))]

                    # Strip .pdf extension from filename for title
                    file_name = file_result.get("file_name", default_title)
                    if file_name.lower().endswith(".pdf"):
                        file_name = file_name[:-4]

                    return {
                        "title": file_name,
                        "content": content,
                        "images": images,
                        "tables": [],
                        "metadata": {
                            "zip_url": full_zip_url,
                        },
                        "success": True
                    }
            finally:
                os.unlink(tmp_zip_path)

        if state == "failed":
            return {
                "title": "",
                "content": "",
                "images": [],
                "tables": [],
                "metadata": {},
                "success": False,
                "error": file_result.get("err_msg", "解析失败")
            }

        print(f"[{elapsed}s] {state_labels.get(state, state)}...", file=sys.stderr)
        time.sleep(interval)

    return {
        "title": "",
        "content": "",
        "images": [],
        "tables": [],
        "metadata": {},
        "success": False,
        "error": f"轮询超时 ({timeout}s)，batch_id: {batch_id}"
    }


# ============================================================================
# Agent 轻量解析 API (10MB/20页限制，无需Token)
# ============================================================================

def parse_pdf_agent_url(url: str, language: str, page_range: Optional[str], enable_table: bool, is_ocr: bool, enable_formula: bool) -> dict:
    """
    Parse PDF from URL using Agent 轻量解析 API.

    限制: 10MB/20页
    无需Token
    """
    try:
        headers = {"Content-Type": "application/json"}
        data = {
            "url": url,
            "language": language,
            "enable_table": enable_table,
            "enable_formula": enable_formula,
        }
        if is_ocr:
            data["is_ocr"] = True
        if page_range:
            data["page_range"] = page_range

        resp = requests.post(
            f"{AGENT_BASE_URL}/parse/url",
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
                "error": f"MinerU Agent API error: {result.get('msg', 'Unknown error')}"
            }

        task_id = result["data"]["task_id"]
        return poll_agent_result(task_id, "document")

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


def parse_pdf_agent_file(pdf_path: str, language: str, page_range: Optional[str], enable_table: bool, is_ocr: bool, enable_formula: bool) -> dict:
    """
    Upload and parse local PDF file using Agent 轻量解析 API.

    限制: 10MB/20页
    无需Token
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

    # Check file size for Agent API
    file_size_mb = pdf_file.stat().st_size / (1024 * 1024)
    if file_size_mb > 10:
        return {
            "title": "",
            "content": "",
            "images": [],
            "tables": [],
            "metadata": {},
            "success": False,
            "error": f"文件大小 {file_size_mb:.1f}MB 超过Agent API限制 (10MB)，请使用精准解析API (--no-agent)"
        }

    try:
        file_name = pdf_file.name

        # Step 1: Get signed upload URL (no auth needed)
        headers = {"Content-Type": "application/json"}
        data = {
            "file_name": file_name,
            "language": language,
            "enable_table": enable_table,
            "enable_formula": enable_formula,
        }
        if is_ocr:
            data["is_ocr"] = True
        if page_range:
            data["page_range"] = page_range

        resp = requests.post(
            f"{AGENT_BASE_URL}/parse/file",
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
                "error": f"MinerU Agent API error: {result.get('msg', 'Unknown error')}"
            }

        task_id = result["data"]["task_id"]
        file_url = result["data"]["file_url"]

        # Step 2: Upload file to OSS
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
                            "error": f"File upload failed: HTTP {put_resp.status_code}"
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
        return poll_agent_result(task_id, pdf_file.stem)

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


def poll_agent_result(task_id: str, default_title: str) -> dict:
    """
    Poll Agent 轻量解析 API for task completion.

    Returns markdown_url (single file, not zip).
    """
    state_labels = {
        "waiting-file": "等待文件上传",
        "uploading": "文件下载中",
        "pending": "排队中",
        "running": "解析中",
    }

    timeout = 300  # 5 minutes max
    interval = 3
    start = time.time()

    while time.time() - start < timeout:
        resp = requests.get(
            f"{AGENT_BASE_URL}/parse/{task_id}",
            timeout=30
        )

        result = resp.json()
        state = result["data"]["state"]
        elapsed = int(time.time() - start)

        if state == "done":
            markdown_url = result["data"]["markdown_url"]
            md_resp = requests.get(markdown_url, timeout=60)
            content = md_resp.text

            return {
                "title": default_title,
                "content": content,
                "images": [],
                "tables": [],
                "metadata": {
                    "markdown_url": markdown_url,
                },
                "success": True
            }

        if state == "failed":
            err_msg = result["data"].get("err_msg", "解析失败")
            err_code = result["data"].get("err_code", 0)

            # 提供更友好的错误提示
            if err_code == -30001:
                err_msg = f"文件大小超出Agent API限制 (10MB)，请使用精准解析API (--no-agent)"
            elif err_code == -30003:
                err_msg = f"文件页数超出Agent API限制 (20页)，请使用精准解析API (--no-agent)"

            return {
                "title": "",
                "content": "",
                "images": [],
                "tables": [],
                "metadata": {},
                "success": False,
                "error": err_msg
            }

        print(f"[{elapsed}s] {state_labels.get(state, state)}...", file=sys.stderr)
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
    parser = argparse.ArgumentParser(
        description="Parse PDF using MinerU API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
API模式说明:
  默认使用精准解析API (200MB/600页限制，需要Token，支持vlm模型)
  使用 --agent 切换到轻量API (10MB/20页限制，无需Token)

模型选择 (仅精准API):
  --model pipeline  默认模型
  --model vlm       推荐模型，精度更高

示例:
  # 精准解析 (默认，需Token)
  uv run python bin/pdf_reader.py "paper.pdf"
  uv run python bin/pdf_reader.py "paper.pdf" --model vlm

  # 轻量解析 (无需Token，但有大小限制)
  uv run python bin/pdf_reader.py "small.pdf" --agent
        """
    )
    parser.add_argument("pdf", help="Path to PDF file or URL")
    parser.add_argument("--lang", default="ch", help="Document language (ch/en)")
    parser.add_argument("--pages", help="Page range (e.g., '1-10')")
    parser.add_argument("--output", "-o", help="Output file (default: stdout)")
    parser.add_argument("--no-save", action="store_true", help="Don't save parsed markdown to raw folder")
    parser.add_argument("--raw-dir", default="wiki/raw", help="Directory to save parsed markdown")
    parser.add_argument("--agent", action="store_true", help="Use Agent lightweight API (10MB/20页限制，无需Token)")
    parser.add_argument("--model", default="vlm", choices=["pipeline", "vlm"], help="Model version for precise API (default: vlm)")
    parser.add_argument("--no-table", action="store_true", help="Disable table extraction")
    parser.add_argument("--no-formula", action="store_true", help="Disable formula extraction")
    parser.add_argument("--ocr", action="store_true", help="Force OCR")

    args = parser.parse_args()

    result = parse_pdf(
        args.pdf,
        language=args.lang,
        page_range=args.pages,
        enable_table=not args.no_table,
        is_ocr=args.ocr,
        enable_formula=not args.no_formula,
        use_agent=args.agent,
        model_version=args.model,
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
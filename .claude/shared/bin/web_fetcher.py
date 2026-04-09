#!/usr/bin/env python3
"""
Web fetcher using Scrapling.
Fetches URLs and converts to Markdown for Claude Code processing.

Usage:
    uv run python bin/web_fetcher.py "https://example.com"
    uv run python bin/web_fetcher.py "https://example.com" --cookies "name=value; name2=value2"
    uv run python bin/web_fetcher.py "https://example.com" --cookies-file cookies.json
    uv run python bin/web_fetcher.py "https://example.com" --browser-cookies chrome:xiaohongshu.com
"""

import sys
import json
import argparse
import sqlite3
import shutil
import tempfile
from pathlib import Path
from urllib.parse import urlparse
from typing import Optional
import os

from markdownify import markdownify as md


def parse_cookies_string(cookies_str: str) -> dict:
    """Parse cookies from string format: 'name=value; name2=value2'"""
    cookies = {}
    for item in cookies_str.split(";"):
        item = item.strip()
        if "=" in item:
            name, value = item.split("=", 1)
            cookies[name.strip()] = value.strip()
    return cookies


def load_cookies_file(filepath: str) -> dict:
    """Load cookies from JSON file."""
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"Cookie file not found: {filepath}")
    return json.loads(path.read_text())


def get_browser_cookies(browser: str, domain: str) -> dict:
    """
    Extract cookies from browser's cookie database.

    Supports: chrome, chromium, edge, firefox, safari

    Args:
        browser: Browser name
        domain: Domain to filter cookies (e.g., 'xiaohongshu.com')

    Returns:
        dict of cookie name -> value
    """
    cookies = {}

    if browser.lower() in ("chrome", "chromium", "edge"):
        # Chrome/Chromium/Edge use SQLite databases
        browser_paths = {
            "chrome": [
                "~/Library/Application Support/Google/Chrome/Default/Cookies",
                "~/Library/Application Support/Google/Chrome/Profile 1/Cookies",
                "~/.config/google-chrome/Default/Cookies",
                "~/.config/google-chrome/Profile 1/Cookies",
            ],
            "chromium": [
                "~/Library/Application Support/Chromium/Default/Cookies",
                "~/.config/chromium/Default/Cookies",
            ],
            "edge": [
                "~/Library/Application Support/Microsoft Edge/Default/Cookies",
                "~/.config/microsoft-edge/Default/Cookies",
            ],
        }

        paths = browser_paths.get(browser.lower(), browser_paths["chrome"])

        for cookie_path in paths:
            cookie_file = Path(cookie_path).expanduser()
            if cookie_file.exists():
                cookies = _extract_chrome_cookies(cookie_file, domain)
                if cookies:
                    return cookies

    elif browser.lower() == "firefox":
        # Firefox cookies.ini
        firefox_paths = [
            "~/Library/Application Support/Firefox/Profiles/",
            "~/.mozilla/firefox/",
        ]

        for base_path in firefox_paths:
            base = Path(base_path).expanduser()
            if base.exists():
                for profile in base.glob("*"):
                    cookies_file = profile / "cookies.sqlite"
                    if cookies_file.exists():
                        cookies = _extract_firefox_cookies(cookies_file, domain)
                        if cookies:
                            return cookies

    elif browser.lower() == "safari":
        # Safari uses Cookies.binarycookies (binary format, harder to parse)
        safari_path = Path("~/Library/Cookies/Cookies.binarycookies").expanduser()
        if safari_path.exists():
            # Safari binary cookies require special parsing
            # For now, return empty and suggest using --cookies parameter
            pass

    return cookies


def _extract_chrome_cookies(cookie_file: Path, domain: str) -> dict:
    """Extract cookies from Chrome's SQLite database."""
    cookies = {}

    # Chrome locks the database, need to copy it
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        tmp_path = Path(tmp.name)
        shutil.copy(cookie_file, tmp_path)

    try:
        conn = sqlite3.connect(str(tmp_path))
        cursor = conn.cursor()

        # Query cookies for the domain
        query = """
            SELECT name, value, host_key
            FROM cookies
            WHERE host_key LIKE ? OR host_key LIKE ?
        """
        cursor.execute(query, (f"%{domain}", f"%.{domain}"))

        for row in cursor.fetchall():
            name, value, host = row
            if name and value:
                cookies[name] = value

        conn.close()
    finally:
        tmp_path.unlink(missing_ok=True)

    return cookies


def _extract_firefox_cookies(cookie_file: Path, domain: str) -> dict:
    """Extract cookies from Firefox's SQLite database."""
    cookies = {}

    try:
        conn = sqlite3.connect(str(cookie_file))
        cursor = conn.cursor()

        query = """
            SELECT name, value, host
            FROM moz_cookies
            WHERE host LIKE ? OR host LIKE ?
        """
        cursor.execute(query, (f"%{domain}", f"%.{domain}"))

        for row in cursor.fetchall():
            name, value, host = row
            if name and value:
                cookies[name] = value

        conn.close()
    except Exception:
        pass

    return cookies


def fetch_url(
    url: str,
    stealth: bool = True,
    cookies: Optional[dict] = None,
    wait_time: int = 5,
    scroll: bool = True,
    user_agent: Optional[str] = None,
) -> dict:
    """
    Fetch URL and convert to Markdown using Scrapling.

    Args:
        url: Target URL to fetch
        stealth: Use stealth mode to bypass anti-bot (default: True)
        cookies: Cookie dict to use
        wait_time: Seconds to wait for page load (default: 5)
        scroll: Scroll page to load lazy content (default: True)
        user_agent: Custom user agent string

    Returns:
        dict with title, content (markdown), url, images, metadata
    """
    try:
        if stealth:
            from scrapling.fetchers import StealthyFetcher

            fetcher_args = {
                "url": url,
                "headless": True,
                "network_idle": True,
                "timeout": 30000,
                "wait": wait_time,
            }

            # Add cookies if provided
            if cookies:
                fetcher_args["cookies"] = cookies

            # Custom user agent
            if user_agent:
                fetcher_args["user_agent"] = user_agent

            # Additional anti-bot settings for difficult sites
            fetcher_args.update({
                "disable_resources": True,  # Disable images/CSS to speed up
                "stealth_mode_settings": {
                    "humanize": True,
                    "simulate_mouse_movements": True,
                    "random_mouse_movements": True,
                }
            })

            response = StealthyFetcher.fetch(**fetcher_args)

            # Scroll to load lazy content
            if scroll:
                try:
                    response.page.scroll_page(height=1000)
                    response.page.wait_for(timeout=2000)
                except Exception:
                    pass

        else:
            from scrapling.fetchers import Fetcher
            fetcher_args = {
                "url": url,
                "timeout": 30000,
            }
            if cookies:
                fetcher_args["cookies"] = cookies

            response = Fetcher.get(**fetcher_args)

        # Extract main content
        content = extract_main_content(response)

        # Extract metadata
        metadata = extract_metadata(response)

        return {
            "title": response.css("title::text").get() or "Untitled",
            "content": content,
            "url": response.url,
            "images": response.css("img::attr(src)").getall()[:20],
            "metadata": metadata,
            "success": True
        }

    except Exception as e:
        return {
            "title": "",
            "content": "",
            "url": url,
            "images": [],
            "metadata": {},
            "success": False,
            "error": str(e)
        }


def extract_main_content(response) -> str:
    """
    Extract main article content and convert to Markdown.
    Scrapling's adaptive selectors find content even if structure changes.
    """
    # Site-specific selectors for better extraction
    site_selectors = {
        "xiaohongshu.com": [
            "#noteContainer",
            ".note-content",
            ".note-text",
            "[data-note-id]",
        ],
        "weibo.com": [
            ".WB_text",
            ".WB_detail",
        ],
        "zhihu.com": [
            ".RichContent-inner",
            ".RichText",
            "[itemprop='text']",
        ],
        "medium.com": [
            "article",
            ".postArticle-content",
        ],
    }

    # Check for site-specific selectors
    hostname = urlparse(response.url).hostname or ""
    for site, selectors in site_selectors.items():
        if site in hostname:
            for selector in selectors:
                elements = response.css(selector)
                if elements:
                    html = elements[0].html_content
                    return md(str(html), heading_style="atx")

    # Generic selectors
    generic_selectors = [
        "article",
        "main article",
        ".post-content",
        ".article-content",
        ".entry-content",
        ".content",
        "main",
    ]

    for selector in generic_selectors:
        elements = response.css(selector)
        if elements:
            html = elements[0].html_content
            return md(str(html), heading_style="atx")

    # Fallback: get body text
    body = response.css("body")
    if body:
        html = body[0].html_content
        return md(str(html), heading_style="atx")

    return response.text


def extract_metadata(response) -> dict:
    """Extract metadata from meta tags."""
    metadata = {}

    # Author
    author = (
        response.css('meta[name="author"]::attr(content)').get() or
        response.css('meta[property="article:author"]::attr(content)').get()
    )
    if author:
        metadata["author"] = str(author)

    # Published date
    date = (
        response.css('meta[property="article:published_time"]::attr(content)').get() or
        response.css('meta[name="date"]::attr(content)').get() or
        response.css('time::attr(datetime)').get()
    )
    if date:
        metadata["date"] = str(date)

    # Description
    description = (
        response.css('meta[name="description"]::attr(content)').get() or
        response.css('meta[property="og:description"]::attr(content)').get()
    )
    if description:
        metadata["description"] = str(description)

    # Keywords
    keywords = response.css('meta[name="keywords"]::attr(content)').get()
    if keywords:
        metadata["keywords"] = [k.strip() for k in str(keywords).split(",")]

    # Platform-specific metadata
    hostname = urlparse(response.url).hostname or ""

    # XiaoHongShu specific
    if "xiaohongshu" in hostname:
        note_id = response.url.split("/")[-1] if "/" in response.url else ""
        if note_id:
            metadata["note_id"] = note_id

        likes = response.css('[data-like-count]::attr(data-like-count)').get()
        if likes:
            metadata["likes"] = likes

        author_name = response.css('.author-name::text').get()
        if author_name:
            metadata["author"] = str(author_name).strip()

    return metadata


def main():
    parser = argparse.ArgumentParser(
        description="Fetch URL and convert to Markdown",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Basic fetch:
    uv run python bin/web_fetcher.py "https://example.com"

  With cookies string:
    uv run python bin/web_fetcher.py "https://xiaohongshu.com/discovery/item/xxx" \
        --cookies "web_session=xxx; a1=xxx"

  Import from browser:
    uv run python bin/web_fetcher.py "https://xiaohongshu.com/discovery/item/xxx" \
        --browser-cookies chrome:xiaohongshu.com

  Load from JSON file:
    uv run python bin/web_fetcher.py "https://example.com" --cookies-file cookies.json

  Longer wait for slow sites:
    uv run python bin/web_fetcher.py "https://example.com" --wait 10

  Auto-save to raw folder:
    uv run python bin/web_fetcher.py "https://example.com" --raw-dir raw
        """
    )
    parser.add_argument("url", help="URL to fetch")
    parser.add_argument("--no-stealth", action="store_true", help="Disable stealth mode")
    parser.add_argument("--cookies", "-c", help="Cookies in 'name=value; name2=value2' format")
    parser.add_argument("--cookies-file", "-f", help="Path to JSON file with cookies")
    parser.add_argument(
        "--browser-cookies", "-b",
        help="Import cookies from browser. Format: browser:domain (e.g., chrome:xiaohongshu.com)"
    )
    parser.add_argument("--wait", "-w", type=int, default=5, help="Wait time in seconds (default: 5)")
    parser.add_argument("--no-scroll", action="store_true", help="Disable page scrolling")
    parser.add_argument("--user-agent", "-u", help="Custom user agent string")
    parser.add_argument("--output", "-o", help="Output file (default: stdout)")
    parser.add_argument("--no-save", action="store_true", help="Don't save fetched markdown to raw folder")
    parser.add_argument("--raw-dir", default="wiki/raw", help="Directory to save fetched markdown (default: wiki/raw)")

    args = parser.parse_args()

    # Build cookies dict
    cookies = {}

    if args.cookies:
        cookies.update(parse_cookies_string(args.cookies))

    if args.cookies_file:
        cookies.update(load_cookies_file(args.cookies_file))

    if args.browser_cookies:
        try:
            browser, domain = args.browser_cookies.split(":")
            browser_cookies = get_browser_cookies(browser, domain)
            cookies.update(browser_cookies)
            print(f"[INFO] Imported {len(browser_cookies)} cookies from {browser} for {domain}")
        except ValueError:
            print("[ERROR] Invalid --browser-cookies format. Use: browser:domain")
            sys.exit(1)

    result = fetch_url(
        args.url,
        stealth=not args.no_stealth,
        cookies=cookies if cookies else None,
        wait_time=args.wait,
        scroll=not args.no_scroll,
        user_agent=args.user_agent,
    )

    # Auto-save fetched markdown to raw folder
    if result.get("success") and not args.no_save:
        raw_dir = Path(args.raw_dir)
        raw_dir.mkdir(exist_ok=True)

        # Generate filename from title or URL
        title = result.get("title", "webpage")
        safe_name = "".join(c if c.isalnum() or c in ('-', '_', ' ') else '' for c in title)
        safe_name = safe_name[:60].strip().replace(' ', '-')

        if not safe_name:
            # Fallback to URL hostname
            from urllib.parse import urlparse
            hostname = urlparse(args.url).hostname or "webpage"
            safe_name = hostname.replace('.', '-')

        md_filename = f"{safe_name}.md"
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
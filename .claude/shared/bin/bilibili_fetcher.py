#!/usr/bin/env python3
"""
Bilibili video fetcher.
Extracts CC字幕 (subtitles) from Bilibili videos for wiki ingestion.

Usage:
    uv run python bin/bilibili_fetcher.py "https://www.bilibili.com/video/BV1xx..."
    uv run python bin/bilibili_fetcher.py "https://www.bilibili.com/video/av12345"

Setup:
    Run /wiki-init to configure, or set OPENAI_API_KEY for Whisper transcription
"""

import sys
import json
import re
import time
import os
import tempfile
import subprocess
from pathlib import Path
from typing import Optional, List

import httpx
import yt_dlp
from openai import OpenAI

# Import unified config
try:
    from wiki_config import get_config, get_openai_config
except ImportError:
    # Fallback for direct script execution
    import importlib.util
    spec = importlib.util.spec_from_file_location("wiki_config", Path(__file__).parent / "wiki_config.py")
    wiki_config = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(wiki_config)
    get_config = wiki_config.get_config
    get_openai_config = wiki_config.get_openai_config


def extract_bvid(url: str) -> Optional[str]:
    """Extract BV ID from various Bilibili URL formats.

    Supports:
    - BV format: BV1xx...
    - av format: av12345
    """
    # BV1xx... format
    match = re.search(r'BV[\w]+', url)
    if match:
        return match.group(0)

    # av123... format — we'll use the aid directly for API calls
    match = re.search(r'av(\d+)', url, re.IGNORECASE)
    if match:
        return f"av{match.group(1)}"

    return None


def download_audio(url: str, output_dir: str) -> Optional[str]:
    """Download audio from Bilibili video using yt-dlp.

    Returns path to audio file or None on failure.
    Note: Uses original audio format (no ffmpeg conversion needed).
    """
    # Bilibili requires specific headers for access
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Referer": "https://www.bilibili.com",
    }

    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': os.path.join(output_dir, '%(id)s.%(ext)s'),
        'quiet': True,
        'no_warnings': True,
        'http_headers': headers,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if info:
                # Return the downloaded file path (original format, e.g., .m4a, .webm)
                ext = info.get('ext', 'm4a')
                return os.path.join(output_dir, f"{info['id']}.{ext}")
    except Exception as e:
        print(f"Download error: {e}", file=sys.stderr)
        return None

    return None


def split_audio_file(audio_path: str, max_size_mb: int = 25) -> List[str]:
    """
    Split audio file into chunks under max_size_mb.
    Uses ffmpeg (from imageio-ffmpeg or system) to split by time.

    Returns list of chunk file paths.
    """
    file_size_mb = os.path.getsize(audio_path) / (1024 * 1024)

    if file_size_mb <= max_size_mb:
        return [audio_path]

    print(f"File size {file_size_mb:.2f}MB exceeds {max_size_mb}MB limit, splitting...", file=sys.stderr)

    # Try to get ffmpeg executable
    ffmpeg_exe = None

    # Option 1: Use imageio-ffmpeg (bundled, no system install needed)
    try:
        import imageio_ffmpeg
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        print(f"Using bundled ffmpeg from imageio-ffmpeg", file=sys.stderr)
    except ImportError:
        pass

    # Option 2: Use system ffmpeg
    if not ffmpeg_exe:
        try:
            subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
            ffmpeg_exe = "ffmpeg"
        except:
            pass

    if not ffmpeg_exe:
        return [{
            "error": f"音频文件 {file_size_mb:.1f}MB 超过 Whisper API 限制 ({max_size_mb}MB)，需要 ffmpeg 进行分割。",
            "hint": "安装方式: uv add imageio-ffmpeg (推荐，自带ffmpeg) 或 brew install ffmpeg"
        }]

    try:
        # Get audio duration using ffmpeg (more compatible than ffprobe)
        # ffprobe might not be available in imageio-ffmpeg
        result = subprocess.run(
            [ffmpeg_exe, "-i", audio_path, "-f", "null", "-"],
            capture_output=True, text=True
        )
        # Parse duration from stderr (ffmpeg outputs info to stderr)
        import re
        duration_match = re.search(r'Duration: (\d+):(\d+):(\d+\.?\d*)', result.stderr)
        if not duration_match:
            return [{"error": "无法获取音频时长"}]

        hours, mins, secs = duration_match.groups()
        duration = int(hours) * 3600 + int(mins) * 60 + float(secs)

        # Calculate number of chunks with safety margin (target 85% of max size)
        safe_max_mb = max_size_mb * 0.85
        num_chunks = max(2, int(file_size_mb / safe_max_mb) + 1)
        chunk_duration = duration / num_chunks

        print(f"Audio duration: {duration:.0f}s, splitting into {num_chunks} chunks (~{chunk_duration:.0f}s each)", file=sys.stderr)

        output_dir = tempfile.mkdtemp()
        chunk_files = []

        for i in range(num_chunks):
            start_time = i * chunk_duration
            chunk_path = os.path.join(output_dir, f"chunk_{i:03d}.m4a")

            # Use ffmpeg to extract chunk (re-encode for safety)
            result = subprocess.run(
                [ffmpeg_exe, "-y", "-i", audio_path,
                 "-ss", str(start_time), "-t", str(chunk_duration),
                 "-c:a", "aac", "-b:a", "96k",  # Re-encode with lower bitrate for safety
                 chunk_path],
                capture_output=True, text=True
            )

            if result.returncode != 0:
                print(f"Warning: ffmpeg chunk {i} failed: {result.stderr[:200]}", file=sys.stderr)
                continue

            # Verify chunk size
            if os.path.exists(chunk_path) and os.path.getsize(chunk_path) > 0:
                chunk_size_mb = os.path.getsize(chunk_path) / (1024 * 1024)
                chunk_files.append(chunk_path)
                print(f"  Chunk {i+1}/{num_chunks}: {chunk_size_mb:.1f}MB", file=sys.stderr)

        if chunk_files:
            return chunk_files
        else:
            return [{"error": "所有音频分割尝试失败"}]

    except Exception as e:
        print(f"ffmpeg split failed: {e}", file=sys.stderr)
        return [{"error": f"音频分割失败: {str(e)}"}]


def transcribe_audio(audio_path: str) -> Optional[str]:
    """Transcribe audio using OpenAI Whisper API.

    Handles files larger than 25MB by splitting into chunks.

    Returns transcript text or None on failure.
    """
    MAX_FILE_SIZE_MB = 25

    # Get config from unified config
    api_key, base_url = get_openai_config()

    if not api_key:
        print("Error: OpenAI API key not configured. Run /wiki-init to configure.", file=sys.stderr)
        return None

    client = OpenAI(api_key=api_key, base_url=base_url)

    # Check file size and split if needed
    file_size_mb = os.path.getsize(audio_path) / (1024 * 1024)

    if file_size_mb > MAX_FILE_SIZE_MB:
        split_result = split_audio_file(audio_path, MAX_FILE_SIZE_MB)

        # Check if split returned an error
        if split_result and isinstance(split_result[0], dict) and "error" in split_result[0]:
            print(f"Error: {split_result[0]['error']}", file=sys.stderr)
            return None

        chunk_files = split_result
    else:
        chunk_files = [audio_path]

    # Transcribe each chunk
    transcripts = []

    for i, chunk_path in enumerate(chunk_files):
        chunk_size_mb = os.path.getsize(chunk_path) / (1024 * 1024)

        if len(chunk_files) > 1:
            print(f"Transcribing chunk {i+1}/{len(chunk_files)} ({chunk_size_mb:.2f}MB)...", file=sys.stderr)

        try:
            with open(chunk_path, "rb") as audio_file:
                transcript = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                )
                transcripts.append(transcript.text)
        except Exception as e:
            print(f"Transcription error for chunk {i+1}: {e}", file=sys.stderr)
            if len(chunk_files) == 1:
                return None
            # Continue with other chunks if one fails
            continue
        finally:
            # Clean up chunk files if they were created
            if chunk_path != audio_path and os.path.exists(chunk_path):
                os.remove(chunk_path)

    # Clean up temp directory if created
    if len(chunk_files) > 1 and chunk_files[0] != audio_path:
        chunk_dir = os.path.dirname(chunk_files[0])
        if os.path.exists(chunk_dir):
            try:
                os.rmdir(chunk_dir)
            except:
                pass

    return " ".join(transcripts) if transcripts else None


def fetch_bilibili(url: str, max_retries: int = 3, timeout: int = 30) -> dict:
    """Fetch Bilibili video info and subtitle.

    Args:
        url: Bilibili video URL
        max_retries: Number of retries on network failure
        timeout: HTTP timeout in seconds

    Returns:
        dict with title, content (transcript), url, bvid, duration, author, metadata
        or dict with error key on failure
    """
    bvid_or_aid = extract_bvid(url)
    if not bvid_or_aid:
        return {"error": "Invalid Bilibili URL", "url": url}

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Referer": "https://www.bilibili.com",
    }

    for attempt in range(max_retries):
        try:
            with httpx.Client(timeout=timeout, headers=headers) as client:
                # Get video info
                if bvid_or_aid.startswith("BV"):
                    info_url = f"https://api.bilibili.com/x/web-interface/view?bvid={bvid_or_aid}"
                    bvid = bvid_or_aid
                else:
                    # av format
                    aid = bvid_or_aid.replace("av", "")
                    info_url = f"https://api.bilibili.com/x/web-interface/view?aid={aid}"

                info_resp = client.get(info_url)
                info_resp.raise_for_status()
                info_data = info_resp.json()

                if info_data.get("code", 0) != 0:
                    return {
                        "error": f"Bilibili API error: {info_data.get('message', 'Unknown error')}",
                        "url": url
                    }

                info = info_data.get("data", {})
                bvid = info.get("bvid", bvid_or_aid)

                # Check for multi-part video
                if info.get("videos", 1) > 1:
                    print(f"Warning: Multi-part video detected ({info['videos']} parts), extracting first part only", file=sys.stderr)

                # Get subtitle list
                # Need cid for subtitle API
                cid = info.get("cid", info.get("pages", [{}])[0].get("cid", 0))

                subtitle_url = f"https://api.bilibili.com/x/player/v2?bvid={bvid}&cid={cid}"
                subtitle_resp = client.get(subtitle_url)
                subtitle_resp.raise_for_status()
                subtitle_data = subtitle_resp.json()

                if subtitle_data.get("code", 0) != 0:
                    return {
                        "error": "Failed to get subtitle data",
                        "title": info.get("title", "Unknown"),
                        "url": f"https://www.bilibili.com/video/{bvid}",
                        "bvid": bvid
                    }

                subtitle_list = subtitle_data.get("data", {}).get("subtitle", {}).get("subtitles", [])

                # If no CC字幕, fall back to Whisper transcription
                if not subtitle_list:
                    print(f"No CC字幕 found, falling back to Whisper transcription...", file=sys.stderr)

                    # Create temp directory for audio download
                    with tempfile.TemporaryDirectory() as temp_dir:
                        audio_path = download_audio(url, temp_dir)

                        if not audio_path:
                            return {
                                "error": "Failed to download audio for transcription",
                                "title": info.get("title", "Unknown"),
                                "url": f"https://www.bilibili.com/video/{bvid}",
                                "bvid": bvid
                            }

                        transcript = transcribe_audio(audio_path)

                        if not transcript:
                            return {
                                "error": "No CC字幕 available and Whisper transcription failed (check OPENAI_API_KEY)",
                                "title": info.get("title", "Unknown"),
                                "url": f"https://www.bilibili.com/video/{bvid}",
                                "bvid": bvid
                            }

                        # Return transcript from Whisper
                        duration_seconds = info.get("duration", 0)

                        return {
                            "title": info.get("title", "Unknown"),
                            "content": transcript,
                            "url": f"https://www.bilibili.com/video/{bvid}",
                            "bvid": bvid,
                            "duration": duration_seconds,
                            "author": info.get("owner", {}).get("name", "Unknown"),
                            "metadata": {
                                "view_count": info.get("stat", {}).get("view", 0),
                                "like_count": info.get("stat", {}).get("like", 0),
                                "publish_date": info.get("pubdate", 0),
                                "subtitle_language": "whisper-auto",
                                "multi_part": info.get("videos", 1) > 1,
                                "transcription_method": "whisper",
                            }
                        }

                # Fetch subtitle content from URL
                subtitle_info = subtitle_list[0]
                subtitle_json_url = subtitle_info.get("subtitle_url", "")

                if not subtitle_json_url:
                    return {
                        "error": "No subtitle URL found",
                        "title": info.get("title", "Unknown"),
                        "url": f"https://www.bilibili.com/video/{bvid}",
                        "bvid": bvid
                    }

                # Ensure URL has protocol
                if not subtitle_json_url.startswith("http"):
                    subtitle_json_url = "https:" + subtitle_json_url

                # Fetch subtitle JSON
                json_resp = client.get(subtitle_json_url)
                json_resp.raise_for_status()
                subtitle_json = json_resp.json()

                # subtitle_json format: {"body": [{"from": 0.0, "to": 2.5, "content": "..."}]}
                body = subtitle_json.get("body", [])

                if not body:
                    return {
                        "error": "Empty subtitle body",
                        "title": info.get("title", "Unknown"),
                        "url": f"https://www.bilibili.com/video/{bvid}",
                        "bvid": bvid
                    }

                # Extract transcript text
                transcript = "\n".join([item.get("content", "") for item in body if item.get("content")])

                # Duration is in seconds from Bilibili API
                duration_seconds = info.get("duration", 0)

                return {
                    "title": info.get("title", "Unknown"),
                    "content": transcript,
                    "url": f"https://www.bilibili.com/video/{bvid}",
                    "bvid": bvid,
                    "duration": duration_seconds,
                    "author": info.get("owner", {}).get("name", "Unknown"),
                    "metadata": {
                        "view_count": info.get("stat", {}).get("view", 0),
                        "like_count": info.get("stat", {}).get("like", 0),
                        "publish_date": info.get("pubdate", 0),
                        "subtitle_language": subtitle_info.get("lan", "zh-CN"),
                        "multi_part": info.get("videos", 1) > 1,
                    }
                }

        except httpx.TimeoutException:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # Exponential backoff
                print(f"Timeout, retrying in {wait_time}s... (attempt {attempt + 1}/{max_retries})", file=sys.stderr)
                time.sleep(wait_time)
                continue
            return {"error": "Network timeout after retries", "url": url}

        except httpx.HTTPStatusError as e:
            return {"error": f"HTTP error: {e.response.status_code}", "url": url}

        except Exception as e:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
                print(f"Error: {e}, retrying in {wait_time}s... (attempt {attempt + 1}/{max_retries})", file=sys.stderr)
                time.sleep(wait_time)
                continue
            return {"error": str(e), "url": url}

    return {"error": "Max retries exceeded", "url": url}


def main():
    if len(sys.argv) < 2:
        print("Usage: uv run python bin/bilibili_fetcher.py <bilibili_url>", file=sys.stderr)
        print("Options: --no-save, --raw-dir <dir>", file=sys.stderr)
        sys.exit(1)

    # Simple argument parsing for optional flags
    url = None
    no_save = False
    raw_dir = "wiki/raw"

    for arg in sys.argv[1:]:
        if arg == "--no-save":
            no_save = True
        elif arg.startswith("--raw-dir="):
            raw_dir = arg.split("=", 1)[1]
        elif arg.startswith("--raw-dir"):
            # Handle --raw-dir <dir> format
            idx = sys.argv.index(arg)
            if idx + 1 < len(sys.argv) and not sys.argv[idx + 1].startswith("-"):
                raw_dir = sys.argv[idx + 1]
        elif not arg.startswith("-"):
            url = arg

    if not url:
        print("Error: No URL provided", file=sys.stderr)
        sys.exit(1)

    result = fetch_bilibili(url)

    # Auto-save transcript to raw folder
    if result.get("content") and "error" not in result and not no_save:
        from pathlib import Path as PathLib
        raw_path = PathLib(raw_dir)
        raw_path.mkdir(exist_ok=True)

        # Generate filename from title or bvid
        title = result.get("title", "video")
        safe_name = "".join(c if c.isalnum() or c in ('-', '_', ' ') else '' for c in title)
        safe_name = safe_name[:60].strip().replace(' ', '-')

        if not safe_name:
            safe_name = result.get("bvid", "bilibili-video")

        md_filename = f"{safe_name}.md"
        md_path = raw_path / md_filename
        md_path.write_text(result["content"], encoding="utf-8")
        result["saved_to"] = str(md_path)

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
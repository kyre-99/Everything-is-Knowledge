#!/usr/bin/env python3
"""
Unified configuration for Wiki skills.
All wiki scripts should import this module for consistent configuration.

Config file: ~/.wiki-config.json
Priority: Environment variables > Config file > Defaults

Usage:
    from wiki_config import get_config
    config = get_config()
    api_key = config.get("mineru_api_key")
"""

import os
import json
from pathlib import Path
from typing import Any, Optional


# Default values
DEFAULTS = {
    "pdf_parser": "mineru",  # "mineru" | "pymupdf" | "both"
    "mineru_base_url": "https://mineru.net/api/v1/agent",
    "openai_base_url": "https://api.zhizengzeng.com/v1",
    "openai_api_key": "",  # No default key for security
    "mineru_api_key": "",
    "deepxiv_token": "",  # Optional: DeepXiv token (auto-registers on first use)
}

CONFIG_FILE = Path.home() / ".wiki-config.json"


def load_config_file() -> dict:
    """Load configuration from ~/.wiki-config.json"""
    if not CONFIG_FILE.exists():
        return {}

    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"Warning: Failed to load config file: {e}", file=__import__('sys').stderr)
        return {}


def get_config() -> dict:
    """
    Get merged configuration.
    Priority: Environment variables > Config file > Defaults

    Returns:
        dict with all configuration values
    """
    config = DEFAULTS.copy()

    # Load from file
    file_config = load_config_file()
    config.update(file_config)

    # Environment variables override (highest priority)
    env_mappings = {
        "WIKI_PDF_PARSER": "pdf_parser",
        "MINERU_API_KEY": "mineru_api_key",
        "MINERU_BASE_URL": "mineru_base_url",
        "OPENAI_API_KEY": "openai_api_key",
        "OPENAI_BASE_URL": "openai_base_url",
        "DEEPXIV_TOKEN": "deepxiv_token",
    }

    for env_key, config_key in env_mappings.items():
        env_value = os.getenv(env_key)
        if env_value:
            config[config_key] = env_value

    return config


def get_mineru_api_key() -> str:
    """Get MinerU API key (convenience function)."""
    config = get_config()
    key = config.get("mineru_api_key", "")

    # Fallback to legacy file location
    if not key:
        legacy_file = Path.home() / ".mineru_api_key"
        if legacy_file.exists():
            key = legacy_file.read_text().strip()

    return key


def get_openai_config() -> tuple[str, str]:
    """
    Get OpenAI API configuration (convenience function).

    Returns:
        tuple of (api_key, base_url)
    """
    config = get_config()
    api_key = config.get("openai_api_key", "")
    base_url = config.get("openai_base_url", DEFAULTS["openai_base_url"])

    # Fallback to legacy file locations
    if not api_key:
        legacy_file = Path.home() / ".openai_api_key"
        if legacy_file.exists():
            api_key = legacy_file.read_text().strip()

    return api_key, base_url


def get_deepxiv_token() -> str:
    """
    Get DeepXiv token (convenience function).

    Returns:
        DeepXiv token string (empty if not configured)
    """
    config = get_config()
    token = config.get("deepxiv_token", "")

    # Fallback to ~/.env file (where deepxiv CLI stores it)
    if not token:
        env_file = Path.home() / ".env"
        if env_file.exists():
            for line in env_file.read_text().splitlines():
                if line.startswith("DEEPXIV_TOKEN="):
                    token = line.split("=", 1)[1].strip()
                    break

    return token


def save_config(config: dict) -> bool:
    """
    Save configuration to file.

    Args:
        config: Dictionary with configuration values

    Returns:
        True if saved successfully, False otherwise
    """
    try:
        # Merge with existing config
        existing = load_config_file()
        existing.update(config)

        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(existing, f, indent=2, ensure_ascii=False)

        return True
    except IOError as e:
        print(f"Error saving config: {e}", file=__import__('sys').stderr)
        return False


def print_config_status() -> None:
    """Print current configuration status (for debugging)."""
    config = get_config()

    print("=== Wiki Configuration ===")
    print(f"Config file: {CONFIG_FILE}")
    print(f"PDF Parser: {config['pdf_parser']}")
    print(f"MinerU API Key: {'✓ configured' if config.get('mineru_api_key') else '✗ not set'}")
    print(f"MinerU Base URL: {config.get('mineru_base_url', 'default')}")
    print(f"OpenAI API Key: {'✓ configured' if config.get('openai_api_key') else '✗ not set'}")
    print(f"OpenAI Base URL: {config.get('openai_base_url', 'default')}")
    print(f"DeepXiv Token: {'✓ configured' if config.get('deepxiv_token') else '✗ not set (auto-register on first use)'}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        cmd = sys.argv[1]

        if cmd == "status":
            print_config_status()
        elif cmd == "set":
            if len(sys.argv) < 4:
                print("Usage: wiki_config.py set <key> <value>")
                print("Keys: pdf_parser, mineru_api_key, mineru_base_url, openai_api_key, openai_base_url, deepxiv_token")
                sys.exit(1)

            key = sys.argv[2]
            value = sys.argv[3]

            if save_config({key: value}):
                print(f"✓ Set {key}")
            else:
                print(f"✗ Failed to set {key}")
                sys.exit(1)
        elif cmd == "get":
            if len(sys.argv) < 3:
                print("Usage: wiki_config.py get <key>")
                sys.exit(1)

            key = sys.argv[2]
            config = get_config()
            print(config.get(key, ""))
        else:
            print(f"Unknown command: {cmd}")
            print("Commands: status, set, get")
            sys.exit(1)
    else:
        print_config_status()
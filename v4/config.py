"""
Configuration module for v4 agent.

Centralizes all configuration: API client, model selection, paths.
Environment variables:
    OPENAI_API_KEY  - API key for OpenAI-compatible endpoint
    OPENAI_BASE_URL - Base URL (optional, for proxies/alternatives)
    MODEL_ID        - Model to use (default: claude-sonnet-4-5-20250929)
"""

import os
from pathlib import Path

from openai import OpenAI
from dotenv import load_dotenv

load_dotenv(override=True)


# =============================================================================
# Paths
# =============================================================================

WORKDIR = Path.cwd()
SKILLS_DIR = WORKDIR / "skills"


# =============================================================================
# API Client
# =============================================================================

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url=os.getenv("OPENAI_BASE_URL"),
)

MODEL = os.getenv("MODEL_ID", "claude-sonnet-4-5-20250929")

"""
Priority Profile Builder for RolloForge.

Reads Rollo's MEMORY.md and RolloWiki to extract a personalized priority profile.
Used by personalized_scoring.py to bias bookmark scores toward Rollo's actual priorities.

Profile structure:
{
    "built_at": "2026-05-01T15:30:00Z",
    "sources": ["MEMORY.md", "wiki/sources/..."],
    "projects": {
        "medical-imaging": {
            "label": "Medical Imaging / FYP",
            "weight": 10.0,
            "keywords": ["nnU-Net", "U-Net", "tumor segmentation", "medical imaging", "dice score", "HD95", "biomedical"],
            "description": "Final year project — AI-based tumor segmentation"
        },
        ...
    },
    "global_keywords": {
        "gpu": 8.0,
        "docker": 7.0,
        ...
    }
}
"""
from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

LOGGER = logging.getLogger(__name__)

WORKSPACE = Path("/home/ubuntu/.openclaw/workspace")
WIKI_DIR = Path("/home/ubuntu/.openclaw/wiki/main")
PROFILE_PATH = Path("/home/ubuntu/RolloForge/data/priority_profile.json")

# Manually maintained priority definitions — these are the ground truth.
# The auto-extractor supplements these but doesn't override them.
CORE_PRIORITIES = {
    "medical-imaging": {
        "label": "Medical Imaging / FYP",
        "weight": 10.0,
        "keywords": [
            "nnU-Net", "nnunet", "U-Net", "unet", "tumor segmentation",
            "medical imaging", "medical image", "dice score", "HD95",
            "biomedical", "radiology", "MRI", "CT scan", "whole-body",
            "lesion detection", "segmentation model", "monai",
            "total segmentator", "auto-segmentation"
        ],
        "description": "Final year project — AI-based tumor segmentation with nnU-Net and transformers"
    },
    "openclaw-agents": {
        "label": "OpenClaw / Agent Systems",
        "weight": 9.0,
        "keywords": [
            "openclaw", "multi-agent", "agent orchestration", "subagent",
            "coding agent", "acp", "hermes", "agent skill", "agent workflow",
            "skill file", "autonomous agent", "agent team", "agent swarm"
        ],
        "description": "Building and optimizing multi-agent systems with OpenClaw"
    },
    "rolloforge": {
        "label": "RolloForge",
        "weight": 8.5,
        "keywords": [
            "rolloforge", "bookmark", "deepseek analysis", "forger",
            "scoring", "bucketing", "bookmark processing", "dashboard"
        ],
        "description": "Personal bookmark → analysis → action system"
    },
    "gpu-infra": {
        "label": "GPU Servers / Infrastructure",
        "weight": 9.0,
        "keywords": [
            "gpu", "A100", "A6000", "nvidia", "cuda", "docker", "container",
            "server", "linux", "SSH", "tunnel", "systemd", "infrastructure",
            "deployment", "devops", "vps", "reverse tunnel"
        ],
        "description": "Managing GPU servers, Docker containers, and lab infrastructure"
    },
    "ai-models": {
        "label": "AI Models / LLMs",
        "weight": 8.0,
        "keywords": [
            "deepseek", "kimi", "claude", "gpt", "grok", "qwen", "gemini",
            "openai", "anthropic", "llm", "large language model", "model release",
            "coding model", "reasoning model", "vision model", "open source model",
            "benchmark", "livebench", "swe-bench"
        ],
        "description": "New model releases, benchmarks, and comparisons — directly usable"
    },
    "autoresearch": {
        "label": "Autoresearch / AutoML",
        "weight": 7.5,
        "keywords": [
            "autoresearch", "karpathy loop", "hyperparameter", "autoML",
            "automated research", "optimization loop", "grid search",
            "bayesian optimization", "experiment tracking"
        ],
        "description": "Automated research and hyperparameter optimization"
    },
    "trading": {
        "label": "Trading / Prediction Markets",
        "weight": 6.0,
        "keywords": [
            "trading", "crypto", "bitcoin", "polymarket", "forex", "quant",
            "prediction market", "technical analysis", "trading bot",
            "market making", "betting", "odds"
        ],
        "description": "Crypto/forex trading and prediction markets — side interest"
    },
    "coding-tools": {
        "label": "AI Coding Tools",
        "weight": 7.5,
        "keywords": [
            "cursor", "copilot", "codex", "claude code", "windsurf", "cody",
            "coding assistant", "code generation", "ide", "vscode extension",
            "ai coding", "vibe coding"
        ],
        "description": "AI-powered coding tools and workflows"
    },
    "product-building": {
        "label": "Product Building / Startups",
        "weight": 7.0,
        "keywords": [
            "product", "startup", "SaaS", "shipping", "MVP", "bootstrap",
            "indie hacker", "solopreneur", "build in public", "launch",
            "monetization", "revenue", "customer"
        ],
        "description": "Building and shipping products fast with AI"
    },
}

# Keywords that boost ANY bookmark score regardless of project match
GLOBAL_BOOST_KEYWORDS = {
    "open source": 1.5,
    "github": 1.5,
    "api": 1.0,
    "implementation": 1.0,
    "step-by-step": 1.0,
    "tutorial": 0.5,
    "code": 0.5,
    "docker": 1.0,
    "openclaw": 2.0,
    "deepseek": 2.0,
    "kimi": 2.0,
    "karpathy": 1.5,
}

# Keywords that penalize (distractions)
DISTRACTION_KEYWORDS = {
    "nft": -2.0,
    "memecoin": -2.0,
    "meme coin": -2.0,
    "web3 gaming": -2.0,
    "social media marketing": -1.0,
    "influencer": -1.0,
    "tiktok": -1.5,
    "onlyfans": -3.0,
}


def extract_from_memory_md() -> dict[str, Any]:
    """Extract project priorities from MEMORY.md 'Current Active Work' section."""
    memory_path = WORKSPACE / "MEMORY.md"
    if not memory_path.exists():
        LOGGER.warning("MEMORY.md not found at %s", memory_path)
        return {"projects": {}, "global": {}}

    content = memory_path.read_text(encoding="utf-8")

    # Find "Current Active Work" section
    active_match = re.search(
        r'## Current Active Work\n\n(.*?)(?=\n## |\n---|\Z)',
        content, re.DOTALL
    )
    if not active_match:
        LOGGER.warning("'Current Active Work' section not found in MEMORY.md")
        return {"projects": {}, "global": {}}

    section = active_match.group(1)

    # Extract project blocks (### headers)
    projects = {}
    project_blocks = re.split(r'\n### ', section)
    for block in project_blocks[1:]:  # Skip content before first ###
        lines = block.strip().split('\n')
        if not lines:
            continue
        name = lines[0].strip()
        # Generate a slug
        slug = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')

        # Extract keywords from the block
        block_text = ' '.join(lines[1:])
        keywords = set()

        # Common tech terms
        tech_terms = re.findall(
            r'\b(?:[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*|'
            r'[a-z]+(?:-[a-z]+)+|'
            r'[A-Z]{2,}\d*(?:-\d+)?|'
            r'(?:nn)?U-Net|'
            r'GPT-\d|'
            r'RolloForge|OpenClaw)\b',
            block_text
        )
        keywords.update(t.lower() for t in tech_terms if len(t) > 2)

        # Extract quoted and parenthesized terms
        for match in re.finditer(r'["\']([^"\']{3,40})["\']', block_text):
            keywords.add(match.group(1).lower())
        for match in re.finditer(r'\(([^)]{3,40})\)', block_text):
            keywords.add(match.group(1).lower())

        if keywords:
            # Assign weight based on position (first projects = higher priority)
            projects[slug] = {
                "label": name,
                "weight": 8.0,
                "keywords": sorted(keywords)[:20],
                "description": block_text[:200].strip()
            }

    # Extract global signals from full MEMORY.md
    global_signals = {}

    # Check "What I'm Avoiding" / priority sections for explicit signals
    priority_section = re.search(
        r'## Optimization Priority\n\n(.*?)(?=\n## |\n---|\Z)',
        content, re.DOTALL
    )
    if priority_section:
        pri_text = priority_section.group(1).lower()
        if "time" in pri_text:
            global_signals["speed_efficiency"] = 8.0
        if "sanity" in pri_text:
            global_signals["reliability"] = 7.0
        if "money" in pri_text:
            global_signals["cost_efficiency"] = 6.0

    return {"projects": projects, "global": global_signals}


def build_profile(force: bool = False) -> dict[str, Any]:
    """
    Build the full priority profile.
    
    Merges CORE_PRIORITIES (manual ground truth) with auto-extracted data.
    CORE_PRIORITIES always wins on conflicts.
    """
    now = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')

    # Start with core priorities as base
    projects = {k: dict(v) for k, v in CORE_PRIORITIES.items()}

    # Try auto-extraction from MEMORY.md for additional signals
    try:
        extracted = extract_from_memory_md()
        extra_projects = extracted.get("projects", {})
        extra_global = extracted.get("global", {})
    except Exception as e:
        LOGGER.warning("Failed to extract from MEMORY.md: %s", e)
        extra_projects = {}
        extra_global = {}

    # Build profile
    profile = {
        "built_at": now,
        "version": 1,
        "sources": ["CORE_PRIORITIES (manual)", "MEMORY.md"],
        "projects": projects,
        "global_boost_keywords": GLOBAL_BOOST_KEYWORDS,
        "distraction_keywords": DISTRACTION_KEYWORDS,
        "extra_signals": extra_global,
        "stats": {
            "total_projects": len(projects),
            "total_keywords": sum(len(p["keywords"]) for p in projects.values()),
            "max_weight": max((p["weight"] for p in projects.values()), default=10.0),
            "min_weight": min((p["weight"] for p in projects.values()), default=1.0),
        }
    }

    return profile


def load_profile() -> dict[str, Any]:
    """Load cached profile, building it if missing or stale."""
    if PROFILE_PATH.exists():
        try:
            with open(PROFILE_PATH, encoding="utf-8") as f:
                cached = json.load(f)
            # Check if profile is from today
            built_at = cached.get("built_at", "")
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            if today in built_at:
                return cached
            LOGGER.info("Profile is from %s, rebuilding...", built_at[:10])
        except (json.JSONDecodeError, KeyError) as e:
            LOGGER.warning("Cached profile corrupt: %s, rebuilding...", e)

    return build_and_save_profile()


def build_and_save_profile() -> dict[str, Any]:
    """Build profile and save to disk."""
    profile = build_profile(force=True)
    PROFILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(PROFILE_PATH, "w", encoding="utf-8") as f:
        json.dump(profile, f, indent=2, ensure_ascii=False)
    LOGGER.info(
        "Built priority profile: %d projects, %d keywords",
        profile["stats"]["total_projects"],
        profile["stats"]["total_keywords"],
    )
    return profile


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    profile = build_and_save_profile()
    print(json.dumps(profile, indent=2, ensure_ascii=False))

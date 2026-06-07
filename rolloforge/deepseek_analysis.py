"""DeepSeek LLM integration for RolloForge bookmark analysis.

Replaces heuristic scoring with real LLM analysis.
"""
import json
import logging
import os
from functools import lru_cache
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from openai import (
    APIConnectionError,
    APIError,
    APITimeoutError,
    AuthenticationError,
    OpenAI,
    RateLimitError,
)
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

# Load environment variables from .env file
load_dotenv()

# Also check ~/.hermes/.env for KIMI_API_KEY
hermes_env = Path.home() / '.hermes' / '.env'
if hermes_env.exists():
    with open(hermes_env) as f:
        for line in f:
            if '=' in line and not line.startswith('#'):
                key, val = line.strip().split('=', 1)
                if key not in os.environ:
                    os.environ[key] = val

import subprocess
import re

LOGGER = logging.getLogger(__name__)

# Model configuration - using DeepSeek V4 Pro
ANALYSIS_BASE_URL = "https://api.deepseek.com"
ANALYSIS_MODEL = "deepseek-v4-pro"
ANALYSIS_TIMEOUT = 60  # seconds
OPENCLAW_WORKSPACE = Path("/home/ubuntu/.openclaw/workspace")
PROFILE_FILES = [
    OPENCLAW_WORKSPACE / "USER.md",
    OPENCLAW_WORKSPACE / "SOUL.md",
    OPENCLAW_WORKSPACE / "CONTEXT.md",
    OPENCLAW_WORKSPACE / "MEMORY.md",
]

WIKI_DIR = Path("/home/ubuntu/.openclaw/wiki/main")


class DeepSeekError(Exception):
    """Base exception for DeepSeek errors."""
    pass


class DeepSeekConfigError(DeepSeekError):
    """Raised when configuration is invalid."""
    pass


class DeepSeekAPIError(DeepSeekError):
    """Raised when API call fails."""
    pass


@lru_cache(maxsize=1)
def _load_user_context() -> str:
    """Load durable user context files to personalize bookmark analysis."""
    sections = []
    max_chars_per_file = 6000

    for path in PROFILE_FILES:
        try:
            content = path.read_text(encoding="utf-8")
        except FileNotFoundError:
            LOGGER.warning("Profile file missing for DeepSeek context: %s", path)
            continue
        except Exception as exc:
            LOGGER.warning("Failed to read profile file %s: %s", path, exc)
            continue

        trimmed = content[:max_chars_per_file]
        if len(content) > max_chars_per_file:
            trimmed += "\n...[truncated]"
        sections.append(f"## {path.name}\n{trimmed}")

    if not sections:
        return "No user profile files were available."

    return "\n\n".join(sections)


def _load_wiki_context(bookmark_text: str, title: str = "", url: str = "") -> str:
    """Search RolloWiki for relevant context about bookmark topics."""
    try:
        # Extract key terms from bookmark for searching
        search_terms = set()
        
        # Add title words (filtered)
        if title:
            search_terms.update(w.lower() for w in re.findall(r'\b[A-Za-z]{4,}\b', title))
        
        # Add URL domain
        if url:
            domain = re.search(r'https?://(?:www\.)?([^/]+)', url)
            if domain:
                search_terms.add(domain.group(1).split('.')[0].lower())
        
        # Add key terms from text (first 500 chars only)
        if bookmark_text:
            text_terms = re.findall(r'\b[A-Za-z]{5,}\b', bookmark_text[:500])
            # Count frequency and take top terms
            from collections import Counter
            term_counts = Counter(t.lower() for t in text_terms)
            search_terms.update(t for t, c in term_counts.most_common(8))
        
        if not search_terms:
            return ""
        
        # Search wiki using grep (fast, no dependencies)
        wiki_sources = WIKI_DIR / "sources"
        if not wiki_sources.exists():
            return ""
        
        found_sections = []
        max_sections = 3
        max_chars_per_section = 2000
        
        # Search each source file for matching terms
        for source_file in sorted(wiki_sources.glob("*.md"), reverse=True)[:5]:
            try:
                content = source_file.read_text(encoding="utf-8")
                # Find paragraphs containing search terms
                paragraphs = content.split("\n\n")
                matching = []
                for para in paragraphs:
                    para_lower = para.lower()
                    if any(term in para_lower for term in search_terms):
                        matching.append(para)
                
                if matching:
                    section_text = "\n\n".join(matching[:3])  # Top 3 matching paragraphs
                    if len(section_text) > max_chars_per_section:
                        section_text = section_text[:max_chars_per_section] + "\n...[truncated]"
                    found_sections.append(f"### {source_file.name}\n{section_text}")
                    
                if len(found_sections) >= max_sections:
                    break
                    
            except Exception:
                continue
        
        if found_sections:
            return "\n\n".join(found_sections)
        return ""
        
    except Exception as e:
        LOGGER.warning(f"Wiki context loading failed: {e}")
        return ""


def get_analysis_client() -> Optional[OpenAI]:
    """Initialize analysis client (DeepSeek V4 Pro)."""
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        LOGGER.error("DEEPSEEK_API_KEY not set")
        return None
    return OpenAI(api_key=api_key, base_url=ANALYSIS_BASE_URL, timeout=ANALYSIS_TIMEOUT)
    return OpenAI(
        api_key=api_key,
        base_url=ANALYSIS_BASE_URL,
        timeout=ANALYSIS_TIMEOUT,
        max_retries=0,  # We handle retries with tenacity
    )


@retry(
    retry=retry_if_exception_type((APIConnectionError, APITimeoutError, RateLimitError)),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    reraise=True
)
def _call_analysis_api(client: OpenAI, prompt: str) -> str:
    """Make API call to Kimi via OpenRouter with retry logic."""
    response = client.chat.completions.create(
        model=ANALYSIS_MODEL,
        messages=[
            {"role": "system", "content": "You are an expert bookmark analyzer. You understand OpenClaw, AI agents, trading, and prediction markets. You provide honest, actionable analysis."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7,
        max_tokens=1200,
        response_format={"type": "json_object"}
    )
    return response.choices[0].message.content


def _parse_json_response(content: str) -> Optional[dict]:
    """Best-effort parser for model JSON output."""
    if not content:
        return None

    cleaned = content.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:].lstrip()

    candidates = [cleaned]
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidates.append(cleaned[start:end + 1])

    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            continue
    return None


def _repair_json_response(client: OpenAI, raw_content: str) -> Optional[dict]:
    """Ask Kimi to repair malformed JSON without changing meaning."""
    if not raw_content or not raw_content.strip():
        return None

    response = client.chat.completions.create(
        model=ANALYSIS_MODEL,
        messages=[
            {
                "role": "system",
                "content": "Repair malformed JSON. Return only one valid JSON object. Preserve meaning; do not add commentary.",
            },
            {
                "role": "user",
                "content": f"Fix this malformed JSON and return only valid JSON:\n\n{raw_content}",
            },
        ],
        temperature=0.1,
        max_tokens=1200,
    )
    repaired = response.choices[0].message.content
    return _parse_json_response(repaired)


def analyze_with_deepseek(text: str, title: str = "", url: str = "") -> Optional[dict]:
    """
    Analyze bookmark content using DeepSeek LLM.
    
    Returns analysis dict or None if failed.
    """
    client = get_analysis_client()
    if not client:
        LOGGER.error("Failed to initialize analysis client")
        return None
    
    # Truncate text if too long (Kimi has context limits)
    max_chars = 8000
    if len(text) > max_chars:
        text = text[:max_chars] + "... [truncated]"
    
    user_context = _load_user_context()
    wiki_context = _load_wiki_context(text, title, url)
    
    # Build wiki section if available
    wiki_section = ""
    if wiki_context:
        wiki_section = f"""

ROLLOWIKI CONTEXT (relevant pages from your knowledge base):
{wiki_context}
"""
    
    prompt = f"""You are the bookmark analyst for Rollo. Do not do generic internet summarization.

Your job is to read the bookmark fully, read the user context below, and judge whether this is useful for Rollo specifically.

USER CONTEXT FILES:
{user_context}{wiki_section}

BOOKMARK TO ANALYZE:
URL: {url}
Title: {title}
Content: {text}

Analyze the bookmark against Rollo's real context:
- his current projects, systems, and workflows
- what he is actively building or fixing now
- whether this reduces friction, creates leverage, saves time, improves infra, improves agent workflows, or is directly useful for current exploration
- whether it is actually actionable this week, worth building later, or just reference material

Respond in valid JSON. Instead of arbitrary 0-10 scores, answer these 3 focused questions:

{{
  "title": "Polished title, concise, no trailing dots",
  "summary": "3-4 sentences. Explain what it is, the core takeaway, and why it matters for Rollo specifically.",
  "recommendation_reason": "One blunt sentence explaining why this is or is not relevant to Rollo right now.",
  "key_insights": ["3-5 concrete takeaways grounded in the content"],
  "tags": ["2-6 specific tags, never generic"],
  "actionable_this_week": false,
  "reduces_friction": false,
  "reference_material": false,
  "recommendation_bucket": "test_this_week|build_later|archive|ignore"
}}

Question definitions:
- **actionable_this_week**: Can Rollo act on this TODAY or within 7 days? Does it have immediate steps he can take? (Not "someday" — THIS WEEK)
- **reduces_friction**: Does this make something he's currently building faster, cheaper, easier, or better? Does it remove a blocker?
- **reference_material**: Is this something he'll want to FIND again later, even if he doesn't act on it now? (Docs, benchmarks, comparisons, guides)

Bucketing rules:
- **test_this_week**: actionable_this_week = true (regardless of other answers)
- **build_later**: actionable_this_week = false AND reduces_friction = true
- **archive**: actionable_this_week = false AND reduces_friction = false AND reference_material = true
- **ignore**: All three are false

OVERRIDE RULES — When you see any of these, bump UP the bucket:
1. **AI coding tools / infrastructure / model releases** (Cursor, Kimi, Claude, GPT, Grok, Qwen, DeepSeek) → test_this_week
2. **GPU / compute / supercomputer / infrastructure scaling** → build_later minimum
3. **Trading / quant / prediction markets / automation** → build_later (never archive)
4. **Multi-agent / OpenClaw / Hermes / AI agents / assistants** → test_this_week
5. **Startups building AI tools, API integrations, workflow automation** → build_later minimum

DEFAULT RULE: When uncertain between two buckets, ALWAYS choose the MORE URGENT one. Rollo prefers action over reference.

Scoring notes:
- Be strict. Most bookmarks should not be top priority.
- Judge against Rollo, not against a generic tech audience.
- Do not downgrade something just because it is short if it has strong practical leverage.
- Do NOT give relevance < 5 to model releases, AI tools, infrastructure, coding tools, or anything related to agents/automation. These are core to Rollo's work.
- Do not use fake personalization language like 'this user should care because'. Just write like an intelligent operator.
- Never use the tag 'general'.
- Prefer specific tags like openclaw, agents, coding, automation, llm, medical-imaging, infra, docker, gpu, bookmarking, product, trading, research, claude, kimi, deepseek.
- Base the recommendation on the full bookmark content plus the user context files and wiki context above, not on crude keyword matching.

FINAL CHECK before responding: If you bucketed as archive/ignore for any content about AI models, coding tools, infrastructure, trading, or agents — you are probably wrong. Reconsider and bucket UP."""

    try:
        content = _call_analysis_api(client, prompt)
        analysis = _parse_json_response(content)
        if analysis is None:
            LOGGER.warning("Kimi returned malformed JSON, attempting repair pass")
            analysis = _repair_json_response(client, content)
        if analysis is None:
            raise json.JSONDecodeError("Unable to repair Kimi JSON", content or "", 0)
        
        # Transform to match expected format
        # Handle both old 'bucket' and new 'recommendation_bucket'
        if "bucket" in analysis and "recommendation_bucket" not in analysis:
            analysis["recommendation_bucket"] = analysis["bucket"]
        
        # NEW: Compute legacy scores from binary questions for backward compatibility
        actionable = analysis.get("actionable_this_week", False)
        reduces_friction = analysis.get("reduces_friction", False)
        reference = analysis.get("reference_material", False)
        
        # Compute derived scores (0-10 scale) from binary answers
        # These approximate the old 8-dimension scoring for dashboard compatibility
        relevance = 8.0 if actionable else (6.0 if reduces_friction else (4.0 if reference else 2.0))
        practical_value = 8.0 if reduces_friction else (5.0 if reference else 2.0)
        actionability = 9.0 if actionable else (4.0 if reduces_friction else 1.0)
        stage_fit = 7.0 if (actionable or reduces_friction) else 4.0
        novelty = analysis.get("novelty", 5.0)  # Keep if provided, else default
        excitement = analysis.get("excitement", 5.0)
        difficulty = 3.0 if actionable else (5.0 if reduces_friction else 7.0)
        time_cost = 2.0 if actionable else (5.0 if reduces_friction else 7.0)
        
        # Compute bucket if not provided (fallback logic)
        if "recommendation_bucket" not in analysis:
            if actionable:
                analysis["recommendation_bucket"] = "test_this_week"
            elif reduces_friction:
                analysis["recommendation_bucket"] = "build_later"
            elif reference:
                analysis["recommendation_bucket"] = "archive"
            else:
                analysis["recommendation_bucket"] = "ignore"
        
        # Compute priority and worth scores
        worth_score = 8.0 if actionable else (6.5 if reduces_friction else (4.0 if reference else 1.5))
        effort_score = 2.0 if actionable else (5.0 if reduces_friction else 7.0)
        priority_score = max(0.0, min(10.0, worth_score - (0.3 * effort_score)))
        
        # Build scoring_inputs for backward compatibility
        if "scoring_inputs" not in analysis:
            analysis["scoring_inputs"] = {
                "relevance": relevance,
                "practical_value": practical_value,
                "actionability": actionability,
                "stage_fit": stage_fit,
                "novelty": novelty,
                "excitement": excitement,
                "difficulty": difficulty,
                "time_cost": time_cost
            }
        
        # Ensure legacy fields exist
        analysis["worth_score"] = analysis.get("worth_score", worth_score)
        analysis["effort_score"] = analysis.get("effort_score", effort_score)
        analysis["priority_score"] = analysis.get("priority_score", priority_score)
        
        # Add metadata
        analysis["analysis_source"] = "kimi"
        analysis["model"] = ANALYSIS_MODEL
        
        LOGGER.info(f"Kimi analysis complete: {analysis.get('title', 'N/A')[:50]}...")
        return analysis
        
    except AuthenticationError as e:
        LOGGER.error(f"Kimi authentication failed: {e}")
        return None
    except RateLimitError as e:
        LOGGER.error(f"Kimi rate limit exceeded: {e}")
        raise  # Let retry handle this
    except APITimeoutError as e:
        LOGGER.error(f"Kimi API timeout: {e}")
        raise  # Let retry handle this
    except APIConnectionError as e:
        LOGGER.error(f"Kimi connection error: {e}")
        raise  # Let retry handle this
    except APIError as e:
        LOGGER.error(f"Kimi API error: {e}")
        return None
    except json.JSONDecodeError as e:
        LOGGER.error(f"Failed to parse Kimi response as JSON: {e}")
        return None
    except Exception as e:
        LOGGER.error(f"Kimi analysis failed with unexpected error: {e}")
        return None


def deepseek_analyze_bookmark(text: str, title: str = "", url: str = "") -> dict:
    """
    Analyze bookmark with DeepSeek, fallback to heuristic if fails.
    
    Returns analysis dict.
    """
    # Try DeepSeek first
    try:
        result = analyze_with_deepseek(text, title, url)
        if result:
            return result
    except Exception as e:
        LOGGER.warning(f"DeepSeek analysis failed after retries: {e}")
    
    # Fallback to heuristic
    LOGGER.warning("DeepSeek failed, using fallback analysis")
    text_str = text if isinstance(text, str) else text.get("text", "") if isinstance(text, dict) else str(text)
    return {
        "title": title or "Untitled",
        "summary": "[DeepSeek failed - basic analysis] " + text_str[:100],
        "recommendation_reason": "DeepSeek API failed, fallback analysis",
        "tags": ["deepseek-failed", "review-manually"],
        "recommendation_bucket": "archive",
        "actionable_this_week": False,
        "reduces_friction": False,
        "reference_material": True,
        "priority_score": 3.0,
        "worth_score": 5.0,
        "effort_score": 4.0,
        "relevance": 3.0,
        "practical_value": 3.0,
        "actionability": 3.0,
        "stage_fit": 3.0,
        "novelty": 3.0,
        "excitement": 3.0,
        "difficulty": 5.0,
        "time_cost": 5.0,
        "scoring_inputs": {
            "relevance": 3.0,
            "practical_value": 3.0,
            "actionability": 3.0,
            "stage_fit": 3.0,
            "novelty": 3.0,
            "excitement": 3.0,
            "difficulty": 5.0,
            "time_cost": 5.0
        },
        "analysis_source": "deepseek_fallback"
    }


if __name__ == "__main__":
    # Test
    test_text = """Karpathy open-sourced autoresearch. 42,000 GitHub stars in a week. 
    The pattern works on anything you can score with a number. Ad copy, cold emails, 
    video scripts, job posts, skill files. 12 cycles per hour, 100 overnight."""
    
    try:
        result = analyze_with_deepseek(test_text, "Test Title", "https://x.com/test")
        print(json.dumps(result, indent=2))
    except KeyboardInterrupt:
        LOGGER.info("Interrupted by user")
    except Exception as e:
        LOGGER.error(f"Test failed: {e}")
        print(f"Error: {e}")
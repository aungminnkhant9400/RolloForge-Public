from __future__ import annotations

from rolloforge.models import ScoringInputs
from rolloforge.utils import clamp_score


# Tier 1: Proven builders - automatic high credibility
TIER_1_SOURCES = {
    "karpathy", "gregisenberg", "saboo_shubham_", "shubhamsaboo",
    "andrejkarpathy", "deedydas", "aakashgupta", "roundtablespace"
}

# Tier 2: Established practitioners
TIER_2_SOURCES = {
    "0xsero", "nickspisak_", "investingluc", "0xmario",
    "thedankoe", "zeneca", "startupideaspod", "anthropic", "openai"
}

# OpenClaw-related keywords for relevance boost
OPENCLAW_KEYWORDS = ["openclaw", "claude code", "agent team", "multi-agent", "agent orchestration"]

# Autoresearch keywords
AUTORESEARCH_KEYWORDS = ["autoresearch", "karpathy loop", "automated research", "optimization loop"]


def get_source_credibility(author: str | None) -> float:
    """Calculate credibility bonus based on author."""
    if not author:
        return 0.0
    author_lower = author.lower()
    if any(tier1 in author_lower for tier1 in TIER_1_SOURCES):
        return 1.5
    if any(tier2 in author_lower for tier2 in TIER_2_SOURCES):
        return 0.5
    return 0.0


def calculate_relevance(text: str, author: str | None, tags: list[str]) -> float:
    """
    Relevance scoring (0-10):
    - 10: Direct OpenClaw implementation
    - 9: Autoresearch/optimization  
    - 8: Multi-agent orchestration
    - 7: AI agent tooling
    - 6: Crypto trading automation
    - 4-5: General AI/tech
    - 1-3: Off-topic
    """
    text_lower = text.lower()
    combined = f"{text_lower} {' '.join(tags).lower()}"
    
    base_score = 4.0  # Default: general AI/tech
    
    # Check for OpenClaw implementation
    if any(kw in combined for kw in OPENCLAW_KEYWORDS):
        if "implementation" in combined or "setup" in combined or "parallel" in combined:
            base_score = 10.0
        else:
            base_score = 7.5
    
    # Check for autoresearch
    elif any(kw in combined for kw in AUTORESEARCH_KEYWORDS):
        base_score = 9.0
    
    # Check for multi-agent
    elif "multi-agent" in combined or "agent team" in combined:
        base_score = 8.0
    
    # Check for crypto trading
    elif "trading" in combined and ("crypto" in combined or "polymarket" in combined):
        base_score = 6.0
    
    # Source credibility bonus
    credibility = get_source_credibility(author)
    
    return clamp_score(base_score + credibility)


def calculate_practical_value(text: str, url: str) -> float:
    """
    Practical value (0-10):
    - 10: Code repos, ready implementations
    - 8-9: Step-by-step tutorials
    - 6-7: Conceptual frameworks
    - 4-5: High-level strategy
    - 1-3: Theory/opinions
    """
    text_lower = text.lower()
    url_lower = url.lower()
    
    # Code repository
    if "github.com" in url_lower:
        if "repo" in text_lower or "implementation" in text_lower or "code" in text_lower:
            return 10.0
        return 8.5
    
    # Step-by-step tutorials
    if "how to" in text_lower or "step-by-step" in text_lower or "guide" in text_lower:
        if "example" in text_lower or "template" in text_lower:
            return 9.0
        return 8.0
    
    # Conceptual frameworks
    if "framework" in text_lower or "methodology" in text_lower:
        return 6.5
    
    # High-level strategy
    if "strategy" in text_lower or "thoughts" in text_lower:
        return 5.0
    
    return 4.0


def calculate_actionability(text: str, is_openclaw_related: bool) -> float:
    """
    Actionability (0-10):
    - 10: Specific commands/steps
    - 8-9: Clear workflow
    - 6-7: Approach described
    - 4-5: Vague suggestions
    - 1-3: No next step
    
    +2 bonus if OpenClaw-related (user acts when popular)
    """
    text_lower = text.lower()
    
    # Specific commands
    if any(cmd in text_lower for cmd in ["run this", "install", "docker", "git clone", "pip install"]):
        base = 10.0
    elif "steps" in text_lower or "workflow" in text_lower:
        base = 8.0
    elif "try" in text_lower or "use" in text_lower:
        base = 6.0
    else:
        base = 4.0
    
    # OpenClaw bonus (user will try when popular)
    if is_openclaw_related:
        base += 2.0
    
    return clamp_score(base)


def calculate_stage_fit(text: str, tags: list[str]) -> float:
    """
    Stage fit (0-10) - User is in "Build OpenClaw system" stage:
    - 10: OpenClaw-specific implementations
    - 8-9: Agent orchestration, automation
    - 6-7: GPU optimization, autoresearch
    - 4-5: Trading tools
    - 2-3: Medical imaging (project done)
    """
    combined = f"{text.lower()} {' '.join(tags).lower()}"
    
    if "openclaw" in combined:
        if "implementation" in combined or "setup" in combined:
            return 10.0
        return 9.0
    
    if "agent" in combined and ("orchestration" in combined or "team" in combined):
        return 8.5
    
    if "autoresearch" in combined or "gpu" in combined:
        return 6.5
    
    if "trading" in combined:
        return 5.0
    
    return 4.0


def calculate_novelty(text: str, author: str | None) -> float:
    """
    Novelty (0-10):
    - Karpathy autoresearch = automatic 9+
    - First time seeing = 8-10
    - New angle = 6-8
    - Familiar reminder = 4-6
    - Widely known = 1-3
    """
    text_lower = text.lower()
    
    # Karpathy autoresearch = new paradigm
    if "karpathy" in text_lower and "autoresearch" in text_lower:
        return 9.5
    
    # Breakthrough/new concepts
    if any(kw in text_lower for kw in ["breakthrough", "novel", "new paradigm", "first time"]):
        return 8.5
    
    # Research papers
    if "paper" in text_lower or "research" in text_lower:
        return 7.0
    
    return 5.0


def calculate_effort(text: str, needs_gpu: bool) -> float:
    """
    Effort score (0-10, higher = harder):
    - 2-3: 30 min try
    - 5-6: Weekend project
    - 8-9: Multi-day
    - 10: Research paper
    
    GPU requirement = -2 (user has A100/A6000)
    """
    text_lower = text.lower()
    
    if "research" in text_lower and "paper" in text_lower:
        base = 9.0
    elif "framework" in text_lower or "architecture" in text_lower:
        base = 7.0
    elif "setup" in text_lower or "install" in text_lower:
        base = 5.0
    elif "guide" in text_lower or "tutorial" in text_lower:
        base = 4.0
    else:
        base = 5.0
    
    # GPU reduces effort (user has resources)
    if needs_gpu:
        base -= 2.0
    
    return max(2.0, base)


def compute_worth_score(inputs: ScoringInputs) -> float:
    """Calculate worth score from inputs."""
    score = (
        0.30 * inputs.relevance +        # Priority for user's interests
        0.25 * inputs.practical_value +  # Can actually use it
        0.20 * inputs.actionability +    # Can act on it
        0.15 * inputs.stage_fit +        # Fits current build phase
        0.10 * inputs.novelty            # New information
    )
    return clamp_score(score)


def compute_effort_score(inputs: ScoringInputs) -> float:
    """Calculate effort score from difficulty and time cost."""
    score = 0.6 * inputs.difficulty + 0.4 * inputs.time_cost
    return clamp_score(score)


def compute_priority_score(worth_score: float, effort_score: float) -> float:
    """Priority = worth - 0.5 * effort (adjusted for user's lazy+pickup-when-popular style)"""
    return round(worth_score - 0.5 * effort_score, 2)


def recommendation_bucket(
    inputs: ScoringInputs, 
    worth_score: float, 
    priority_score: float,
    is_openclaw_related: bool = False
) -> str:
    """
    Bucket assignment based on user's criteria:
    - test_this_week: High priority OpenClaw/autoresearch content
    - build_later: Secondary interests, good but not urgent
    - archive: Interesting but not timely
    - ignore: Low value
    """
    # test_this_week: Must be OpenClaw/autoresearch related with high scores
    if is_openclaw_related and priority_score >= 8 and inputs.actionability >= 7 and worth_score >= 7.5:
        return "test_this_week"
    
    # Also test_this_week for high-priority autoresearch with GPU use
    if inputs.relevance >= 8 and priority_score >= 8:
        return "test_this_week"
    
    # build_later: Good content but lower priority or not immediately actionable
    if priority_score >= 3 and worth_score >= 5:
        return "build_later"
    
    # archive: Worth keeping for reference
    if worth_score >= 3 or priority_score >= 1:
        return "archive"
    
    return "ignore"


def auto_score_bookmark(text: str, author: str | None, tags: list[str], url: str) -> ScoringInputs:
    """
    Automatically calculate all scoring inputs based on content analysis.
    """
    combined = f"{text.lower()} {' '.join(tags).lower()}"
    is_openclaw_related = "openclaw" in combined or "claude code" in combined
    needs_gpu = "gpu" in combined or "a100" in combined or "a6000" in combined
    
    return ScoringInputs(
        relevance=calculate_relevance(text, author, tags),
        practical_value=calculate_practical_value(text, url),
        actionability=calculate_actionability(text, is_openclaw_related),
        stage_fit=calculate_stage_fit(text, tags),
        novelty=calculate_novelty(text, author),
        excitement=5.0,  # Neutral unless explicitly exciting content
        difficulty=calculate_effort(text, needs_gpu),
        time_cost=calculate_effort(text, needs_gpu),  # Same as difficulty for simplicity
    )


def score_analysis(inputs: ScoringInputs, is_openclaw_related: bool = False) -> tuple[float, float, float, str]:
    """
    Full scoring pipeline.
    Returns: (worth_score, effort_score, priority_score, bucket)
    """
    worth_score = compute_worth_score(inputs)
    effort_score = compute_effort_score(inputs)
    priority_score = compute_priority_score(worth_score, effort_score)
    bucket = recommendation_bucket(inputs, worth_score, priority_score, is_openclaw_related)
    return worth_score, effort_score, priority_score, bucket

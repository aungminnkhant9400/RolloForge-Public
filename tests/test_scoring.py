"""Unit tests for scoring algorithms."""
import pytest

from rolloforge.models import ScoringInputs
from rolloforge.scoring import (
    TIER_1_SOURCES,
    TIER_2_SOURCES,
    auto_score_bookmark,
    calculate_actionability,
    calculate_effort,
    calculate_novelty,
    calculate_practical_value,
    calculate_relevance,
    calculate_stage_fit,
    compute_effort_score,
    compute_priority_score,
    compute_worth_score,
    get_source_credibility,
    recommendation_bucket,
    score_analysis,
)


class TestSourceCredibility:
    """Tests for source credibility calculations."""

    def test_tier_1_source(self):
        """Tier 1 sources get 1.5 credibility."""
        assert get_source_credibility("karpathy") == 1.5
        assert get_source_credibility("gregisenberg") == 1.5
        assert get_source_credibility("@saboo_shubham_") == 1.5

    def test_tier_2_source(self):
        """Tier 2 sources get 0.5 credibility."""
        assert get_source_credibility("0xsero") == 0.5
        assert get_source_credibility("nickspisak_") == 0.5
        assert get_source_credibility("anthropic") == 0.5

    def test_unknown_source(self):
        """Unknown sources get 0 credibility."""
        assert get_source_credibility("random_user") == 0.0
        assert get_source_credibility("unknown") == 0.0

    def test_none_author(self):
        """None author returns 0 credibility."""
        assert get_source_credibility(None) == 0.0

    def test_case_insensitive(self):
        """Source matching is case insensitive."""
        assert get_source_credibility("KARPATHY") == 1.5
        assert get_source_credibility("Anthropic") == 0.5

    def test_partial_match_in_tier1(self):
        """Partial matches in author string work for tier 1."""
        assert get_source_credibility("karpathy_ai") == 1.5


class TestRelevanceCalculation:
    """Tests for relevance scoring."""

    def test_openclaw_implementation_max_score(self):
        """OpenClaw implementation gets max relevance."""
        text = "OpenClaw implementation with parallel setup"
        score = calculate_relevance(text, None, [])
        assert score == 10.0

    def test_openclaw_related_high_score(self):
        """OpenClaw related gets high score."""
        text = "Working with claude code and openclaw"
        score = calculate_relevance(text, None, [])
        assert score == 7.5

    def test_autoresearch_score(self):
        """Autoresearch keywords get 9.0."""
        text = "Karpathy autoresearch optimization loop"
        score = calculate_relevance(text, None, [])
        assert score == 9.0

    def test_multi_agent_score(self):
        """Multi-agent gets high score due to openclaw keyword match."""
        text = "Building multi-agent systems"
        score = calculate_relevance(text, None, [])
        # "multi-agent" is in OPENCLAW_KEYWORDS, so it gets 7.5 not 8.0
        assert score == 7.5

    def test_crypto_trading_score(self):
        """Crypto trading gets 6.0."""
        text = "Crypto trading on polymarket"
        score = calculate_relevance(text, None, [])
        assert score == 6.0

    def test_default_score(self):
        """Default/general AI gets 4.0."""
        text = "Some general AI discussion"
        score = calculate_relevance(text, None, [])
        assert score == 4.0

    def test_tier1_bonus(self):
        """Tier 1 author adds bonus to relevance."""
        text = "AI discussion"
        score = calculate_relevance(text, "karpathy", [])
        assert score == 5.5  # 4.0 + 1.5

    def test_tier2_bonus(self):
        """Tier 2 author adds smaller bonus."""
        text = "AI discussion"
        score = calculate_relevance(text, "0xsero", [])
        assert score == 4.5  # 4.0 + 0.5


class TestPracticalValueCalculation:
    """Tests for practical value scoring."""

    def test_github_repo_max_score(self):
        """GitHub repo with code mention gets 10."""
        text = "Check out this implementation code repo"
        url = "https://github.com/user/repo"
        assert calculate_practical_value(text, url) == 10.0

    def test_github_without_code(self):
        """GitHub without code mention gets 8.5."""
        text = "Interesting project"
        url = "https://github.com/user/repo"
        assert calculate_practical_value(text, url) == 8.5

    def test_tutorial_with_template(self):
        """Tutorial with template gets 9.0."""
        text = "How to build with this example template"
        url = "https://example.com/guide"
        assert calculate_practical_value(text, url) == 9.0

    def test_guide_without_template(self):
        """Guide without template gets 8.0."""
        text = "Step-by-step guide to building"
        url = "https://example.com/guide"
        assert calculate_practical_value(text, url) == 8.0

    def test_framework_score(self):
        """Framework content gets 6.5."""
        text = "New methodology and framework"
        url = "https://example.com/post"
        assert calculate_practical_value(text, url) == 6.5

    def test_strategy_score(self):
        """Strategy content gets 5.0."""
        text = "My thoughts on strategy"
        url = "https://example.com/post"
        assert calculate_practical_value(text, url) == 5.0

    def test_default_score(self):
        """Default content gets 4.0."""
        text = "Random discussion"
        url = "https://example.com/post"
        assert calculate_practical_value(text, url) == 4.0


class TestActionabilityCalculation:
    """Tests for actionability scoring."""

    def test_specific_commands(self):
        """Commands like install, docker get 10."""
        text = "Run this: docker run and git clone"
        assert calculate_actionability(text, False) == 10.0

    def test_workflow_steps(self):
        """Workflow/steps gets 8."""
        text = "Follow this workflow with these steps"
        assert calculate_actionability(text, False) == 8.0

    def test_try_use_suggestions(self):
        """Try/use suggestions get 6."""
        text = "You should try this and use that"
        assert calculate_actionability(text, False) == 6.0

    def test_vague_content(self):
        """Vague content gets 4."""
        text = "Interesting ideas to consider"
        assert calculate_actionability(text, False) == 4.0

    def test_openclaw_bonus(self):
        """OpenClaw related gets +2 bonus."""
        text = "Interesting ideas"  # Would be 4 without bonus
        assert calculate_actionability(text, True) == 6.0

    def test_openclaw_with_commands(self):
        """OpenClaw with commands capped at 10."""
        text = "Run this docker command"
        assert calculate_actionability(text, True) == 10.0  # Capped


class TestStageFitCalculation:
    """Tests for stage fit scoring."""

    def test_openclaw_implementation(self):
        """OpenClaw implementation gets 10."""
        text = "OpenClaw implementation with setup"
        assert calculate_stage_fit(text, []) == 10.0

    def test_openclaw_general(self):
        """OpenClaw general gets 9.0."""
        text = "Working with OpenClaw"
        assert calculate_stage_fit(text, []) == 9.0

    def test_agent_orchestration(self):
        """Agent orchestration gets 8.5."""
        text = "Agent orchestration and team building"
        assert calculate_stage_fit(text, []) == 8.5

    def test_autoresearch_gpu(self):
        """Autoresearch/GPU gets 6.5."""
        text = "GPU autoresearch optimization"
        assert calculate_stage_fit(text, []) == 6.5

    def test_trading(self):
        """Trading gets 5.0."""
        text = "Trading strategies"
        assert calculate_stage_fit(text, []) == 5.0

    def test_default(self):
        """Default gets 4.0."""
        text = "Random content"
        assert calculate_stage_fit(text, []) == 4.0


class TestNoveltyCalculation:
    """Tests for novelty scoring."""

    def test_karpathy_autoresearch(self):
        """Karpathy autoresearch gets 9.5."""
        text = "Karpathy discusses autoresearch paradigm"
        assert calculate_novelty(text, "karpathy") == 9.5

    def test_breakthrough_concepts(self):
        """Breakthrough concepts get 8.5."""
        text = "This breakthrough represents a new paradigm"
        assert calculate_novelty(text, None) == 8.5

    def test_research_papers(self):
        """Research papers get 7.0."""
        text = "New research paper on AI"
        assert calculate_novelty(text, None) == 7.0

    def test_default(self):
        """Default content gets 5.0."""
        text = "Regular discussion"
        assert calculate_novelty(text, None) == 5.0


class TestEffortCalculation:
    """Tests for effort calculation."""

    def test_research_paper(self):
        """Research paper gets 9.0."""
        text = "This research paper presents"
        assert calculate_effort(text, False) == 9.0

    def test_framework(self):
        """Framework gets 7.0."""
        text = "New architecture framework"
        assert calculate_effort(text, False) == 7.0

    def test_setup_install(self):
        """Setup/install gets 5.0."""
        text = "Setup and install instructions"
        assert calculate_effort(text, False) == 5.0

    def test_guide_tutorial(self):
        """Guide/tutorial gets 4.0."""
        text = "Tutorial guide for beginners"
        assert calculate_effort(text, False) == 4.0

    def test_default_effort(self):
        """Default effort is 5.0."""
        text = "Random content"
        assert calculate_effort(text, False) == 5.0

    def test_gpu_reduces_effort(self):
        """GPU requirement reduces effort by 2."""
        text = "Research paper on GPU optimization"
        assert calculate_effort(text, True) == 7.0  # 9 - 2

    def test_effort_minimum(self):
        """Effort cannot go below 2.0."""
        text = "Tutorial guide"  # Would be 4 - 2 = 2
        assert calculate_effort(text, True) == 2.0


class TestWorthScoreCalculation:
    """Tests for worth score calculation."""

    def test_compute_worth_score(self):
        """Test weighted worth calculation."""
        inputs = ScoringInputs(
            relevance=10.0,
            practical_value=8.0,
            actionability=7.0,
            stage_fit=9.0,
            novelty=6.0,
            excitement=5.0,
            difficulty=4.0,
            time_cost=3.0,
        )
        # 0.30*10 + 0.25*8 + 0.20*7 + 0.15*9 + 0.10*6 = 3 + 2 + 1.4 + 1.35 + 0.6 = 8.35
        score = compute_worth_score(inputs)
        assert score == pytest.approx(8.35, 0.01)

    def test_worth_score_capped(self):
        """Worth score is capped at 10."""
        inputs = ScoringInputs(
            relevance=20.0,
            practical_value=20.0,
            actionability=20.0,
            stage_fit=20.0,
            novelty=20.0,
            excitement=20.0,
            difficulty=5.0,
            time_cost=5.0,
        )
        assert compute_worth_score(inputs) == 10.0


class TestEffortScoreCalculation:
    """Tests for effort score calculation."""

    def test_compute_effort_score(self):
        """Test effort calculation (0.6*difficulty + 0.4*time_cost)."""
        inputs = ScoringInputs(
            relevance=5.0,
            practical_value=5.0,
            actionability=5.0,
            stage_fit=5.0,
            novelty=5.0,
            excitement=5.0,
            difficulty=10.0,
            time_cost=5.0,
        )
        # 0.6*10 + 0.4*5 = 6 + 2 = 8
        assert compute_effort_score(inputs) == 8.0


class TestPriorityScoreCalculation:
    """Tests for priority score calculation."""

    def test_compute_priority(self):
        """Test priority = worth - 0.5*effort."""
        worth = 8.0
        effort = 4.0
        # 8 - 0.5*4 = 8 - 2 = 6
        assert compute_priority_score(worth, effort) == 6.0

    def test_high_effort_reduces_priority(self):
        """High effort reduces priority."""
        worth = 8.0
        effort = 10.0
        # 8 - 0.5*10 = 8 - 5 = 3
        assert compute_priority_score(worth, effort) == 3.0


class TestRecommendationBucket:
    """Tests for bucket assignment."""

    def test_test_this_week_openclaw_high(self):
        """OpenClaw with high scores goes to test_this_week."""
        inputs = ScoringInputs(
            relevance=8.0, practical_value=8.0, actionability=8.0,
            stage_fit=8.0, novelty=8.0, excitement=8.0,
            difficulty=3.0, time_cost=3.0,
        )
        bucket = recommendation_bucket(inputs, 8.0, 6.5, is_openclaw_related=True)
        assert bucket == "test_this_week"

    def test_test_this_week_high_relevance(self):
        """High relevance (>=8) with priority >=6 goes to test_this_week."""
        inputs = ScoringInputs(
            relevance=9.0, practical_value=5.0, actionability=5.0,
            stage_fit=5.0, novelty=5.0, excitement=5.0,
            difficulty=4.0, time_cost=4.0,
        )
        bucket = recommendation_bucket(inputs, 7.0, 6.0, is_openclaw_related=False)
        assert bucket == "test_this_week"

    def test_build_later(self):
        """Good but not urgent goes to build_later."""
        inputs = ScoringInputs(
            relevance=6.0, practical_value=6.0, actionability=6.0,
            stage_fit=6.0, novelty=6.0, excitement=6.0,
            difficulty=5.0, time_cost=5.0,
        )
        bucket = recommendation_bucket(inputs, 6.0, 4.0, is_openclaw_related=False)
        assert bucket == "build_later"

    def test_archive(self):
        """Worth keeping but low priority goes to archive."""
        inputs = ScoringInputs(
            relevance=4.0, practical_value=4.0, actionability=4.0,
            stage_fit=4.0, novelty=4.0, excitement=4.0,
            difficulty=5.0, time_cost=5.0,
        )
        bucket = recommendation_bucket(inputs, 4.0, 1.0, is_openclaw_related=False)
        assert bucket == "archive"

    def test_ignore(self):
        """Low value goes to ignore."""
        inputs = ScoringInputs(
            relevance=1.0, practical_value=1.0, actionability=1.0,
            stage_fit=1.0, novelty=1.0, excitement=1.0,
            difficulty=9.0, time_cost=9.0,
        )
        bucket = recommendation_bucket(inputs, 2.0, -2.0, is_openclaw_related=False)
        assert bucket == "ignore"

    def test_openclaw_not_actionable(self):
        """OpenClaw but low actionability goes to build_later."""
        inputs = ScoringInputs(
            relevance=6.0, practical_value=8.0, actionability=5.0,  # Low actionability
            stage_fit=8.0, novelty=8.0, excitement=8.0,
            difficulty=3.0, time_cost=3.0,
        )
        # Calculate worth and priority for this input
        # worth = 0.3*6 + 0.25*8 + 0.20*5 + 0.15*8 + 0.10*8 = 1.8 + 2 + 1 + 1.2 + 0.8 = 6.8
        # effort = 0.6*3 + 0.4*3 = 3.0
        # priority = 6.8 - 0.5*3 = 5.3
        bucket = recommendation_bucket(inputs, 6.8, 5.3, is_openclaw_related=True)
        assert bucket == "build_later"  # actionability < 7


class TestAutoScoreBookmark:
    """Tests for auto-scoring bookmarks."""

    def test_auto_score_openclaw(self):
        """Auto-score for OpenClaw content."""
        text = "OpenClaw implementation guide with docker setup"
        inputs = auto_score_bookmark(text, "test_author", ["openclaw", "docker"], "https://example.com")

        assert inputs.relevance == 10.0
        assert inputs.actionability == 10.0
        assert inputs.stage_fit == 10.0

    def test_auto_score_autoresearch(self):
        """Auto-score for autoresearch content."""
        # Note: "autoresearch" in text gives novelty boost
        text = "autoresearch optimization loop"
        inputs = auto_score_bookmark(text, "some_author", ["autoresearch"], "https://example.com")

        assert inputs.relevance == 9.0  # Autoresearch keyword
        # "autoresearch" is also in novelty keywords (breakthrough concepts)
        assert inputs.novelty >= 5.0

    def test_auto_score_with_gpu(self):
        """Auto-score reduces effort for GPU content."""
        text = "Research on A100 GPU optimization"
        inputs = auto_score_bookmark(text, "author", ["gpu"], "https://example.com")

        # GPU reduces effort
        assert inputs.difficulty < 9.0  # Would be 9 for research paper


class TestScoreAnalysis:
    """Tests for full scoring pipeline."""

    def test_full_pipeline(self):
        """Test complete scoring pipeline."""
        inputs = ScoringInputs(
            relevance=8.0, practical_value=7.0, actionability=6.0,
            stage_fit=7.0, novelty=5.0, excitement=6.0,
            difficulty=4.0, time_cost=3.0,
        )
        worth, effort, priority, bucket = score_analysis(inputs, is_openclaw_related=True)

        assert 0 <= worth <= 10
        assert 0 <= effort <= 10
        assert isinstance(priority, float)
        assert bucket in ["test_this_week", "build_later", "archive", "ignore"]

    def test_pipeline_returns_tuple(self):
        """Pipeline returns correct tuple structure."""
        inputs = ScoringInputs(
            relevance=5.0, practical_value=5.0, actionability=5.0,
            stage_fit=5.0, novelty=5.0, excitement=5.0,
            difficulty=5.0, time_cost=5.0,
        )
        result = score_analysis(inputs)

        assert len(result) == 4
        assert all(isinstance(x, (int, float)) for x in result[:3])
        assert isinstance(result[3], str)

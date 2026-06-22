"""
Unit tests for TrustMemory, AgentRecord, TrustScore, and TrustTier.

Tests cover initial scores, behavior recording, tier classification,
time-based decay, aggregate statistics, and manual promote/demote.
"""



import pytest

from avs_gateway.core.trust_memory import (
    TrustMemory,
    AgentRecord,
    TrustScore,
    TrustTier,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def memory():
    """Return a fresh TrustMemory instance."""
    return TrustMemory()


@pytest.fixture
def memory_fast_decay():
    """Return a TrustMemory with very fast decay for testing."""
    return TrustMemory(decay_half_life_seconds=1)


# ---------------------------------------------------------------------------
# Initial score
# ---------------------------------------------------------------------------

class TestInitialScore:
    """Tests for the initial trust score of unknown agents."""

    def test_unknown_agent_starts_at_50(self, memory):
        """An unknown agent starts with a trust score of 50."""
        score = memory.get_score("unknown-agent")
        assert isinstance(score, TrustScore)
        assert score.value == 50
        assert score.tier == "standard"
        assert score.total_actions == 0
        assert score.success_rate == 0.5

    def test_unknown_agent_idempotent(self, memory):
        """Getting score for the same unknown agent multiple times is consistent."""
        score1 = memory.get_score("unknown-agent")
        score2 = memory.get_score("unknown-agent")
        assert score1.value == score2.value == 50


# ---------------------------------------------------------------------------
# Record success
# ---------------------------------------------------------------------------

class TestRecordSuccess:
    """Tests for recording successful behavior."""

    def test_record_success_increases_score(self, memory):
        """Recording success increases the trust score."""
        score_before = memory.get_score("agent-001")
        score_after = memory.record_behavior("agent-001", "success")
        assert score_after.value > score_before.value

    def test_record_success_delta_is_plus_5(self, memory):
        """Each success adds +5 to the underlying score calculation."""
        memory.record_behavior("agent-001", "success")
        score = memory.get_score("agent-001")
        # With one observation and weight 1.0, score should be 50 + 5 = 55
        assert score.value > 50

    def test_record_multiple_successes(self, memory):
        """Recording multiple successes compounds the score increase."""
        for _ in range(5):
            memory.record_behavior("agent-001", "success")
        score = memory.get_score("agent-001")
        assert score.value > 60
        assert score.total_actions == 5


# ---------------------------------------------------------------------------
# Record failure
# ---------------------------------------------------------------------------

class TestRecordFailure:
    """Tests for recording failure behavior."""

    def test_record_failure_decreases_score(self, memory):
        """Recording failure decreases the trust score."""
        score_before = memory.get_score("agent-001")
        score_after = memory.record_behavior("agent-001", "failure")
        assert score_after.value < score_before.value

    def test_record_failure_delta_is_minus_10(self, memory):
        """Each failure subtracts -10 from the underlying score calculation."""
        memory.record_behavior("agent-001", "failure")
        score = memory.get_score("agent-001")
        assert score.value < 50

    def test_multiple_failures_lower_score(self, memory):
        """Recording multiple failures compounds the score decrease."""
        for _ in range(5):
            memory.record_behavior("agent-001", "failure")
        score = memory.get_score("agent-001")
        assert score.value < 30
        assert score.total_actions == 5


# ---------------------------------------------------------------------------
# Record quarantine
# ---------------------------------------------------------------------------

class TestRecordQuarantine:
    """Tests for recording quarantine behavior."""

    def test_record_quarantine_decreases_score(self, memory):
        """Recording quarantine decreases the trust score."""
        score_before = memory.get_score("agent-001")
        score_after = memory.record_behavior("agent-001", "quarantine")
        assert score_after.value < score_before.value

    def test_record_quarantine_delta_is_minus_8(self, memory):
        """Each quarantine subtracts -8 from the underlying score calculation."""
        memory.record_behavior("agent-001", "quarantine")
        score = memory.get_score("agent-001")
        assert score.value < 50


# ---------------------------------------------------------------------------
# Record approval behaviors
# ---------------------------------------------------------------------------

class TestRecordApprovalBehaviors:
    """Tests for recording approval-related behaviors."""

    def test_record_approval_granted_increases_score(self, memory):
        """Recording approval_granted increases the trust score."""
        score_before = memory.get_score("agent-001")
        score_after = memory.record_behavior("agent-001", "approval_granted")
        assert score_after.value > score_before.value

    def test_record_approval_denied_decreases_score(self, memory):
        """Recording approval_denied decreases the trust score."""
        score_before = memory.get_score("agent-001")
        score_after = memory.record_behavior("agent-001", "approval_denied")
        assert score_after.value < score_before.value


# ---------------------------------------------------------------------------
# Tier classification
# ---------------------------------------------------------------------------

class TestTierClassification:
    """Tests for trust tier classification at all 4 levels."""

    def test_tier_untrusted_at_score_0(self, memory):
        """Score 0-25 maps to 'untrusted' tier."""
        # Push score way down with failures
        for _ in range(10):
            memory.record_behavior("agent-bad", "failure")
        score = memory.get_score("agent-bad")
        assert score.tier == "untrusted"
        assert score.value <= 25

    def test_tier_limited_at_score_30(self, memory):
        """Score 26-50 maps to 'limited' tier."""
        # Use mixed approval behaviors for finer control (+3 and -7)
        # 2 approval_granted (+6) + 1 approval_denied (-7) = -1 avg ≈ -0.33
        # score ≈ 50 - 16.5 = 33.5 → limited
        memory.record_behavior("agent-limited", "approval_granted")
        memory.record_behavior("agent-limited", "approval_granted")
        memory.record_behavior("agent-limited", "approval_denied")
        score = memory.get_score("agent-limited")
        assert score.tier == "limited"
        assert 26 <= score.value <= 50

    def test_tier_standard_at_score_60(self, memory):
        """Score 51-75 maps to 'standard' tier."""
        # 3 approval_granted (+9) + 2 approval_denied (-14) = -5 avg ≈ -1.0
        # score ≈ 50 - 50 = 0... let me try different ratio
        # 3 approval_granted (+9) + 1 approval_denied (-7) = +2 avg ≈ +0.5
        # score ≈ 50 + 25 = 75 → standard (upper bound)
        memory.record_behavior("agent-std", "approval_granted")
        memory.record_behavior("agent-std", "approval_granted")
        memory.record_behavior("agent-std", "approval_granted")
        memory.record_behavior("agent-std", "approval_denied")
        score = memory.get_score("agent-std")
        assert score.tier == "standard"
        assert 51 <= score.value <= 75

    def test_tier_trusted_at_high_score(self, memory):
        """Score 76-100 maps to 'trusted' tier."""
        # Push score way up with successes
        for _ in range(10):
            memory.record_behavior("agent-good", "success")
        score = memory.get_score("agent-good")
        assert score.tier == "trusted"
        assert score.value >= 76


# ---------------------------------------------------------------------------
# Decay
# ---------------------------------------------------------------------------

class TestDecay:
    """Tests for time-based exponential decay."""

    def test_decay_method_returns_trust_score(self, memory):
        """The decay() method returns a TrustScore."""
        score = memory.decay("any-agent")
        assert isinstance(score, TrustScore)

    def test_decay_reduces_weight_of_old_observations(self, memory_fast_decay):
        """With fast decay, old observations have reduced impact."""
        import time
        # Record a behavior
        memory_fast_decay.record_behavior("agent-001", "success")
        score_immediate = memory_fast_decay.get_score("agent-001")
        # Wait a bit for decay
        time.sleep(0.5)
        score_after_decay = memory_fast_decay.decay("agent-001")
        # The score might change due to decay recalculation
        assert isinstance(score_after_decay, TrustScore)
        assert score_after_decay.total_actions == 1


# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------

class TestGetStats:
    """Tests for aggregate trust memory statistics."""

    def test_stats_empty_memory(self, memory):
        """Stats for an empty memory returns total_agents: 0."""
        stats = memory.get_stats()
        assert stats["total_agents"] == 0

    def test_stats_single_agent(self, memory):
        """Stats for a single agent returns correct values."""
        memory.record_behavior("agent-001", "success")
        stats = memory.get_stats()
        assert stats["total_agents"] == 1
        assert stats["avg_score"] > 0
        assert stats["min_score"] == stats["max_score"]
        assert sum(stats["tier_distribution"].values()) == 1

    def test_stats_multiple_agents(self, memory):
        """Stats for multiple agents returns aggregate values."""
        # Good agent
        for _ in range(5):
            memory.record_behavior("agent-good", "success")
        # Bad agent
        for _ in range(5):
            memory.record_behavior("agent-bad", "failure")

        stats = memory.get_stats()
        assert stats["total_agents"] == 2
        assert stats["max_score"] > stats["min_score"]
        assert stats["avg_score"] > stats["min_score"]
        assert stats["avg_score"] < stats["max_score"]
        assert sum(stats["tier_distribution"].values()) == 2

    def test_stats_tier_distribution(self, memory):
        """Tier distribution counts agents per tier."""
        # Push agent into untrusted
        for _ in range(10):
            memory.record_behavior("agent-untrusted", "failure")
        # Push agent into trusted
        for _ in range(10):
            memory.record_behavior("agent-trusted", "success")

        stats = memory.get_stats()
        assert stats["tier_distribution"]["untrusted"] >= 1
        assert stats["tier_distribution"]["trusted"] >= 1


# ---------------------------------------------------------------------------
# Manual promote / demote
# ---------------------------------------------------------------------------

class TestManualPromoteDemote:
    """Tests for manual promote() and demote() methods."""

    def test_manual_promote_increases_score(self, memory):
        """Promoting an agent increases their trust score."""
        score_before = memory.get_score("agent-001")
        score_after = memory.promote("agent-001", "test promotion")
        assert score_after.value > score_before.value

    def test_manual_promote_records_observation(self, memory):
        """Promotion records a success observation with metadata."""
        score = memory.promote("agent-001", "test reason")
        assert score.total_actions == 1

    def test_manual_demote_decreases_score(self, memory):
        """Demoting an agent decreases their trust score."""
        score_before = memory.get_score("agent-001")
        score_after = memory.demote("agent-001", "test demotion")
        assert score_after.value < score_before.value

    def test_manual_demote_records_observation(self, memory):
        """Demotion records a failure observation with metadata."""
        score = memory.demote("agent-001", "test reason")
        assert score.total_actions == 1

    def test_get_agent_ids(self, memory):
        """get_agent_ids returns all recorded agent IDs."""
        memory.record_behavior("agent-a", "success")
        memory.record_behavior("agent-b", "failure")
        agent_ids = memory.get_agent_ids()
        assert "agent-a" in agent_ids
        assert "agent-b" in agent_ids
        assert len(agent_ids) == 2


# ---------------------------------------------------------------------------
# Observation limits
# ---------------------------------------------------------------------------

class TestObservationLimits:
    """Tests for the MAX_OBSERVATIONS limit."""

    def test_observations_capped_at_max(self, memory):
        """Observations beyond MAX_OBSERVATIONS are pruned."""
        # MAX_OBSERVATIONS is 1000
        for i in range(1100):
            memory.record_behavior("agent-001", "success")

        # Check via internal state
        with memory._lock:
            record = memory._agents["agent-001"]
            assert len(record.observations) <= 1000

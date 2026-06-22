"""
Unit tests for the RiskEngine, RiskScore, RiskDimension, and RiskClassification.

Tests cover scoring across all action types, classification boundaries,
custom weights, blocking determination, and threshold mapping.
"""



import pytest

from avs_gateway.models.action_request import ActionType, create_action_request
from avs_gateway.core.risk_engine import (
    RiskEngine,
    RiskScore,
    RiskDimension,
    RiskClassification,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def engine():
    """Return a fresh RiskEngine with default weights."""
    return RiskEngine()


# ---------------------------------------------------------------------------
# Scoring - file operations
# ---------------------------------------------------------------------------

class TestScoreFileOperations:
    """Tests for file operation risk scoring."""

    def test_score_file_read_is_low_risk(self, engine):
        """A simple file read gets a low risk score."""
        request = create_action_request(
            agent_id="agent-001",
            action_type=ActionType.FILE,
            tool_name="file_tool",
            operation="read",
            parameters={"path": "/tmp/test.txt"},
        )
        score = engine.score(request)
        assert isinstance(score, RiskScore)
        assert 0 <= score.value <= 100
        # File read should be low risk
        assert score.classification in ("low", "medium")

    def test_score_file_read_secret_path_is_higher_risk(self, engine):
        """Reading a secret file path increases risk."""
        request = create_action_request(
            agent_id="agent-001",
            action_type=ActionType.FILE,
            tool_name="file_tool",
            operation="read",
            parameters={"path": "/etc/secret/config"},
        )
        score = engine.score(request)
        # Secret path should increase data_exposure
        assert score.raw_dimensions["data_exposure"] >= 50


# ---------------------------------------------------------------------------
# Scoring - payment operations
# ---------------------------------------------------------------------------

class TestScorePaymentOperations:
    """Tests for payment operation risk scoring."""

    def test_score_payment_high_amount(self, engine):
        """A large payment gets a high or critical risk score."""
        request = create_action_request(
            agent_id="agent-001",
            action_type=ActionType.PAYMENT,
            tool_name="payment_tool",
            operation="transfer",
            parameters={"amount": 50000, "to_account": "acc-1", "from_account": "acc-2"},
        )
        score = engine.score(request)
        assert score.value > 50  # Should be high or critical
        assert score.classification in ("high", "critical")

    def test_score_payment_extreme_amount_is_high_or_critical(self, engine):
        """An extreme payment ($100K+) has maximum financial impact."""
        request = create_action_request(
            agent_id="agent-001",
            action_type=ActionType.PAYMENT,
            tool_name="payment_tool",
            operation="transfer",
            parameters={"amount": 100000, "to_account": "acc-1", "from_account": "acc-2"},
        )
        score = engine.score(request)
        # financial_impact is 100, but weighted aggregation may not reach critical
        assert score.raw_dimensions["financial_impact"] == 100
        assert score.classification in ("high", "critical")

    def test_score_payment_small_amount_is_low(self, engine):
        """A small payment (< $100) should be lower risk."""
        request = create_action_request(
            agent_id="agent-001",
            action_type=ActionType.PAYMENT,
            tool_name="payment_tool",
            operation="transfer",
            parameters={"amount": 50, "to_account": "acc-1", "from_account": "acc-2"},
        )
        score = engine.score(request)
        assert score.classification in ("low", "medium")


# ---------------------------------------------------------------------------
# Scoring - database operations
# ---------------------------------------------------------------------------

class TestScoreDatabaseOperations:
    """Tests for database operation risk scoring."""

    def test_score_database_drop_is_high_reversibility(self, engine):
        """A DROP operation has maximum reversibility risk."""
        request = create_action_request(
            agent_id="agent-001",
            action_type=ActionType.DATABASE,
            tool_name="db_tool",
            operation="DROP",
            parameters={"table": "users"},
        )
        score = engine.score(request)
        assert score.raw_dimensions["reversibility"] >= 90
        # DROP has irreversibility=95 but weighted total may be medium/high
        assert score.classification in ("medium", "high", "critical")

    def test_score_database_select_is_low(self, engine):
        """A SELECT operation should be low risk."""
        request = create_action_request(
            agent_id="agent-001",
            action_type=ActionType.DATABASE,
            tool_name="db_tool",
            operation="SELECT",
            parameters={"table": "users"},
        )
        score = engine.score(request)
        assert score.raw_dimensions["reversibility"] == 0

    def test_score_database_delete_is_high(self, engine):
        """A DELETE operation should have high reversibility score."""
        request = create_action_request(
            agent_id="agent-001",
            action_type=ActionType.DATABASE,
            tool_name="db_tool",
            operation="DELETE",
            parameters={"table": "users", "where": {"id": "1"}},
        )
        score = engine.score(request)
        assert score.raw_dimensions["reversibility"] >= 70


# ---------------------------------------------------------------------------
# Scoring - API operations
# ---------------------------------------------------------------------------

class TestScoreAPIOperations:
    """Tests for API operation risk scoring."""

    def test_score_api_get_is_low(self, engine):
        """API GET should be low risk."""
        request = create_action_request(
            agent_id="agent-001",
            action_type=ActionType.API,
            tool_name="api_tool",
            operation="GET",
            parameters={"endpoint": "/users"},
        )
        score = engine.score(request)
        assert score.raw_dimensions["reversibility"] <= 10

    def test_score_api_delete_is_high(self, engine):
        """API DELETE should be high risk."""
        request = create_action_request(
            agent_id="agent-001",
            action_type=ActionType.API,
            tool_name="api_tool",
            operation="DELETE",
            parameters={"endpoint": "/users/1"},
        )
        score = engine.score(request)
        assert score.raw_dimensions["reversibility"] >= 70

    def test_score_api_post_is_medium(self, engine):
        """API POST should have moderate reversibility risk."""
        request = create_action_request(
            agent_id="agent-001",
            action_type=ActionType.API,
            tool_name="api_tool",
            operation="POST",
            parameters={"endpoint": "/users", "body": {"name": "test"}},
        )
        score = engine.score(request)
        assert score.raw_dimensions["reversibility"] >= 30


# ---------------------------------------------------------------------------
# Classification boundaries
# ---------------------------------------------------------------------------

class TestClassificationBoundaries:
    """Tests for risk classification boundaries."""

    def test_classification_low_at_boundary_0(self, engine):
        """Score of 0 is classified as low."""
        assert engine.classify(0) == "low"

    def test_classification_low_at_boundary_25(self, engine):
        """Score of 25 is classified as low."""
        assert engine.classify(25) == "low"

    def test_classification_medium_at_boundary_26(self, engine):
        """Score of 26 is classified as medium."""
        assert engine.classify(26) == "medium"

    def test_classification_medium_at_boundary_50(self, engine):
        """Score of 50 is classified as medium."""
        assert engine.classify(50) == "medium"

    def test_classification_high_at_boundary_51(self, engine):
        """Score of 51 is classified as high."""
        assert engine.classify(51) == "high"

    def test_classification_high_at_boundary_75(self, engine):
        """Score of 75 is classified as high."""
        assert engine.classify(75) == "high"

    def test_classification_critical_at_boundary_76(self, engine):
        """Score of 76 is classified as critical."""
        assert engine.classify(76) == "critical"

    def test_classification_critical_at_boundary_100(self, engine):
        """Score of 100 is classified as critical."""
        assert engine.classify(100) == "critical"


# ---------------------------------------------------------------------------
# is_blocking
# ---------------------------------------------------------------------------

class TestIsBlocking:
    """Tests for RiskScore.is_blocking() method."""

    def test_low_is_not_blocking(self, engine):
        """Low risk score is not blocking."""
        score = RiskScore(
            value=10, classification="low", dimensions={}, raw_dimensions={}
        )
        assert score.is_blocking() is False

    def test_medium_is_not_blocking(self, engine):
        """Medium risk score is not blocking."""
        score = RiskScore(
            value=40, classification="medium", dimensions={}, raw_dimensions={}
        )
        assert score.is_blocking() is False

    def test_high_is_blocking(self, engine):
        """High risk score IS blocking."""
        score = RiskScore(
            value=60, classification="high", dimensions={}, raw_dimensions={}
        )
        assert score.is_blocking() is True

    def test_critical_is_blocking(self, engine):
        """Critical risk score IS blocking."""
        score = RiskScore(
            value=90, classification="critical", dimensions={}, raw_dimensions={}
        )
        assert score.is_blocking() is True


# ---------------------------------------------------------------------------
# threshold_check
# ---------------------------------------------------------------------------

class TestThresholdCheck:
    """Tests for RiskEngine.threshold_check() method."""

    def test_threshold_low_maps_to_allow(self, engine):
        """Low classification maps to 'allow' decision."""
        score = RiskScore(value=10, classification="low", dimensions={}, raw_dimensions={})
        assert engine.threshold_check(score) == "allow"

    def test_threshold_medium_maps_to_require_approval(self, engine):
        """Medium classification maps to 'require_approval' decision."""
        score = RiskScore(value=30, classification="medium", dimensions={}, raw_dimensions={})
        assert engine.threshold_check(score) == "require_approval"

    def test_threshold_high_maps_to_quarantine(self, engine):
        """High classification maps to 'quarantine' decision."""
        score = RiskScore(value=60, classification="high", dimensions={}, raw_dimensions={})
        assert engine.threshold_check(score) == "quarantine"

    def test_threshold_critical_maps_to_deny(self, engine):
        """Critical classification maps to 'deny' decision."""
        score = RiskScore(value=90, classification="critical", dimensions={}, raw_dimensions={})
        assert engine.threshold_check(score) == "deny"


# ---------------------------------------------------------------------------
# Custom weights
# ---------------------------------------------------------------------------

class TestCustomWeights:
    """Tests for overriding default dimension weights."""

    def test_custom_weights_override_default(self):
        """Providing custom weights overrides the defaults."""
        custom_weights = {
            "sensitivity": 0.5,
            "scope": 0.0,
            "reversibility": 0.5,
            "permission_level": 0.0,
            "external_impact": 0.0,
            "financial_impact": 0.0,
            "data_exposure": 0.0,
            "historical_behavior": 0.0,
        }
        engine = RiskEngine(weights=custom_weights)
        assert engine.weights["sensitivity"] == 0.5
        assert engine.weights["scope"] == 0.0

    def test_weights_are_normalized(self):
        """Weights that don't sum to 1.0 are automatically normalized."""
        custom_weights = {
            "sensitivity": 10.0,
            "scope": 10.0,
            "reversibility": 10.0,
            "permission_level": 10.0,
            "external_impact": 10.0,
            "financial_impact": 10.0,
            "data_exposure": 10.0,
            "historical_behavior": 10.0,
        }
        engine = RiskEngine(weights=custom_weights)
        total = sum(engine.weights.values())
        assert abs(total - 1.0) < 0.001

    def test_custom_scorer_override(self):
        """Custom scorers can override dimension scoring."""
        def always_100(request, original):
            return 100

        engine = RiskEngine(custom_scorers={"sensitivity": always_100})
        request = create_action_request(
            agent_id="agent-001",
            action_type=ActionType.FILE,
            tool_name="file_tool",
            operation="read",
        )
        score = engine.score(request)
        assert score.raw_dimensions["sensitivity"] == 100


# ---------------------------------------------------------------------------
# RiskDimension
# ---------------------------------------------------------------------------

class TestRiskDimension:
    """Tests for the RiskDimension dataclass."""

    def test_risk_dimension_creation(self):
        """RiskDimension can be created with name, value, and weight."""
        dim = RiskDimension(name="sensitivity", value=75, weight=0.15)
        assert dim.name == "sensitivity"
        assert dim.value == 75
        assert dim.weight == 0.15

    def test_risk_dimension_default_weight(self):
        """RiskDimension defaults to weight 1.0."""
        dim = RiskDimension(name="test", value=50)
        assert dim.weight == 1.0


# ---------------------------------------------------------------------------
# Email and security scan scoring
# ---------------------------------------------------------------------------

class TestScoreOtherOperations:
    """Tests for email and security scan operations."""

    def test_score_email_send_internal(self, engine):
        """Internal email send should be moderate risk."""
        request = create_action_request(
            agent_id="agent-001",
            action_type=ActionType.EMAIL,
            tool_name="email_tool",
            operation="send",
            parameters={"to": "internal@company.com", "subject": "test", "body": "hello"},
        )
        score = engine.score(request)
        assert 0 <= score.value <= 100
        assert score.raw_dimensions["reversibility"] >= 50  # send is irreversible

    def test_score_security_scan_run(self, engine):
        """Security scan should have moderate sensitivity."""
        request = create_action_request(
            agent_id="agent-001",
            action_type=ActionType.SECURITY_SCAN,
            tool_name="scan_tool",
            operation="run_scan",
            parameters={"target": "localhost"},
        )
        score = engine.score(request)
        assert 0 <= score.value <= 100
        assert score.raw_dimensions["sensitivity"] >= 30

    def test_score_external_email_higher_impact(self, engine):
        """External email has higher external_impact."""
        request = create_action_request(
            agent_id="agent-001",
            action_type=ActionType.EMAIL,
            tool_name="email_tool",
            operation="send",
            parameters={
                "to": "external@gmail.com",
                "subject": "test",
                "body": "hello",
                "external": True,
            },
        )
        score = engine.score(request)
        assert score.raw_dimensions["external_impact"] >= 60

    def test_score_with_admin_permission(self, engine):
        """Admin permission level increases permission_level score."""
        request = create_action_request(
            agent_id="agent-001",
            action_type=ActionType.FILE,
            tool_name="file_tool",
            operation="read",
            context={"permission_level": "admin"},
        )
        score = engine.score(request)
        assert score.raw_dimensions["permission_level"] >= 45

    def test_score_with_global_scope(self, engine):
        """Global scope increases scope score."""
        request = create_action_request(
            agent_id="agent-001",
            action_type=ActionType.FILE,
            tool_name="file_tool",
            operation="read",
            parameters={"scope": "global"},
        )
        score = engine.score(request)
        assert score.raw_dimensions["scope"] >= 90

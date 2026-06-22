"""
Unit tests for the PolicyEngine, PolicyRule, PolicyResult, and DecisionType.

Tests cover loading policies from YAML/JSON, adding/removing rules,
evaluating conditions with various operators, logical operators,
dot-notation field access, priority ordering, and default behavior.
"""

import json
import os
import tempfile
from pathlib import Path

import pytest

# Repo-relative path to default policies (works on Windows and Linux)
_POLICIES_YAML = str(Path(__file__).resolve().parents[2] / "config" / "default_policies.yaml")

from avs_gateway.models.action_request import ActionRequest, ActionType, create_action_request
from avs_gateway.core.policy_engine import (
    PolicyEngine,
    PolicyRule,
    PolicyResult,
    DecisionType,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def engine():
    """Return a fresh PolicyEngine instance."""
    return PolicyEngine()


@pytest.fixture
def file_read_request():
    """Return an ActionRequest for a file read operation."""
    return create_action_request(
        agent_id="agent-001",
        action_type=ActionType.FILE,
        tool_name="file_tool",
        operation="read",
        parameters={"path": "/tmp/test.txt"},
    )


@pytest.fixture
def file_delete_request():
    """Return an ActionRequest for a file delete operation."""
    return create_action_request(
        agent_id="agent-001",
        action_type=ActionType.FILE,
        tool_name="file_tool",
        operation="delete",
        parameters={"path": "/tmp/test.txt"},
    )


# ---------------------------------------------------------------------------
# Policy loading
# ---------------------------------------------------------------------------

class TestLoadPolicies:
    """Tests for loading policies from files."""

    def test_load_policies_yaml(self, engine):
        """Loading from default YAML policy file returns correct count."""
        policies_path = _POLICIES_YAML
        count = engine.load_policies(policies_path)
        assert count == 23
        assert len(engine.list_rules()) == 23

    def test_load_policies_json(self, engine, tmp_path):
        """Loading from a JSON policy file works correctly."""
        policy_data = {
            "rules": [
                {
                    "name": "test_allow",
                    "description": "Test allow rule",
                    "priority": 1,
                    "condition": {"action_type": "file", "operation": "read"},
                    "decision": "allow",
                    "reason": "Test",
                }
            ]
        }
        json_path = tmp_path / "test_policies.json"
        json_path.write_text(json.dumps(policy_data))

        count = engine.load_policies(str(json_path))
        assert count == 1
        rules = engine.list_rules()
        assert len(rules) == 1
        assert rules[0].name == "test_allow"
        assert rules[0].decision == DecisionType.ALLOW

    def test_load_policies_file_not_found(self, engine):
        """Loading from a non-existent file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            engine.load_policies("/nonexistent/path/policies.yaml")

    def test_load_policies_invalid_format(self, engine, tmp_path):
        """Loading a file without a 'rules' key raises ValueError."""
        bad_path = tmp_path / "bad.yaml"
        bad_path.write_text("not_a_rules_key: []")
        with pytest.raises(ValueError):
            engine.load_policies(str(bad_path))

    def test_load_policies_missing_required_fields(self, engine, tmp_path):
        """Loading a rule with missing required fields raises ValueError."""
        bad_data = {"rules": [{"name": "incomplete"}]}
        bad_path = tmp_path / "bad.json"
        bad_path.write_text(json.dumps(bad_data))
        with pytest.raises(ValueError):
            engine.load_policies(str(bad_path))


# ---------------------------------------------------------------------------
# Add / remove rules
# ---------------------------------------------------------------------------

class TestAddRemoveRules:
    """Tests for adding and removing policy rules."""

    def test_add_rule(self, engine):
        """Adding a rule increases the rule count."""
        rule = PolicyRule(
            name="custom_rule",
            description="A custom rule",
            priority=10,
            condition={"action_type": "file", "operation": "read"},
            decision=DecisionType.ALLOW,
            reason="Custom allow",
        )
        engine.add_rule(rule)
        assert len(engine.list_rules()) == 1
        assert engine.get_rule("custom_rule") == rule

    def test_remove_rule_existing(self, engine):
        """Removing an existing rule returns True."""
        rule = PolicyRule(
            name="removable",
            description="Will be removed",
            priority=10,
            condition={"action_type": "file"},
            decision=DecisionType.ALLOW,
            reason="Test",
        )
        engine.add_rule(rule)
        assert engine.remove_rule("removable") is True
        assert len(engine.list_rules()) == 0

    def test_remove_rule_nonexistent(self, engine):
        """Removing a non-existent rule returns False."""
        assert engine.remove_rule("does_not_exist") is False

    def test_rules_sorted_by_priority(self, engine):
        """Rules are stored in ascending priority order."""
        for i, name in enumerate(["rule_c", "rule_a", "rule_b"]):
            rule = PolicyRule(
                name=name,
                description=f"Rule {name}",
                priority=[30, 10, 20][i],
                condition={"action_type": "file"},
                decision=DecisionType.ALLOW,
                reason="Test",
            )
            engine.add_rule(rule)
        rule_names = [r.name for r in engine.list_rules()]
        assert rule_names == ["rule_a", "rule_b", "rule_c"]


# ---------------------------------------------------------------------------
# Evaluation - basic
# ---------------------------------------------------------------------------

class TestEvaluateBasic:
    """Tests for basic policy evaluation."""

    def test_evaluate_allow_file_read(self, engine, file_read_request):
        """A file read request matches the allow rule and returns ALLOW."""
        engine.load_policies(
            _POLICIES_YAML
        )
        result = engine.evaluate(file_read_request)
        assert result.matched is True
        assert result.decision == DecisionType.ALLOW
        assert result.matched_rule == "file_read"

    def test_evaluate_deny_file_delete(self, engine, file_delete_request):
        """A file delete request matches the deny rule and returns DENY."""
        engine.load_policies(
            _POLICIES_YAML
        )
        result = engine.evaluate(file_delete_request)
        assert result.matched is True
        assert result.decision == DecisionType.DENY
        assert result.matched_rule == "file_delete"


# ---------------------------------------------------------------------------
# Evaluation - operators
# ---------------------------------------------------------------------------

class TestEvaluateOperators:
    """Tests for condition operators (gt, gte, lt, lte, eq, ne, in, nin, regex, exists, contains)."""

    def test_evaluate_amount_threshold_lte(self, engine):
        """Payment with amount <= 100 matches the small payment allow rule."""
        engine.load_policies(
            _POLICIES_YAML
        )
        request = create_action_request(
            agent_id="agent-001",
            action_type=ActionType.PAYMENT,
            tool_name="payment_tool",
            operation="transfer",
            parameters={"amount": 50},
        )
        result = engine.evaluate(request)
        assert result.matched is True
        assert result.decision == DecisionType.ALLOW
        assert result.matched_rule == "payment_small"

    def test_evaluate_amount_threshold_gt_and_lte(self, engine):
        """Payment with amount 500 matches the medium payment approval rule."""
        engine.load_policies(
            _POLICIES_YAML
        )
        request = create_action_request(
            agent_id="agent-001",
            action_type=ActionType.PAYMENT,
            tool_name="payment_tool",
            operation="transfer",
            parameters={"amount": 500},
        )
        result = engine.evaluate(request)
        assert result.matched is True
        assert result.decision == DecisionType.REQUIRE_APPROVAL
        assert result.matched_rule == "payment_medium"

    def test_evaluate_regex_match(self, engine):
        """Tool name matching a regex pattern triggers the rule."""
        rule = PolicyRule(
            name="regex_test",
            description="Regex match test",
            priority=1,
            condition={"tool_name": {"regex": ".*special.*"}},
            decision=DecisionType.DENY,
            reason="Regex matched",
        )
        engine.add_rule(rule)
        request = create_action_request(
            agent_id="agent-001",
            action_type=ActionType.FILE,
            tool_name="my_special_tool",
            operation="read",
        )
        result = engine.evaluate(request)
        assert result.matched is True
        assert result.matched_rule == "regex_test"

    def test_evaluate_operator_in(self, engine):
        """The 'in' operator matches when value is in the list."""
        rule = PolicyRule(
            name="in_test",
            description="In operator test",
            priority=1,
            condition={"operation": {"in": ["read", "GET", "SELECT"]}},
            decision=DecisionType.ALLOW,
            reason="In list",
        )
        engine.add_rule(rule)
        request = create_action_request(
            agent_id="agent-001",
            action_type=ActionType.FILE,
            tool_name="file_tool",
            operation="read",
        )
        result = engine.evaluate(request)
        assert result.matched is True
        assert result.matched_rule == "in_test"

    def test_evaluate_operator_nin(self, engine):
        """The 'nin' operator matches when value is NOT in the list."""
        rule = PolicyRule(
            name="nin_test",
            description="Nin operator test",
            priority=1,
            condition={"operation": {"nin": ["delete", "DROP", "DENY"]}},
            decision=DecisionType.ALLOW,
            reason="Not in list",
        )
        engine.add_rule(rule)
        request = create_action_request(
            agent_id="agent-001",
            action_type=ActionType.FILE,
            tool_name="file_tool",
            operation="read",
        )
        result = engine.evaluate(request)
        assert result.matched is True
        assert result.matched_rule == "nin_test"

    def test_evaluate_operator_eq(self, engine):
        """The 'eq' operator matches exact equality."""
        rule = PolicyRule(
            name="eq_test",
            description="Eq operator test",
            priority=1,
            condition={"agent_id": {"eq": "trusted-agent"}},
            decision=DecisionType.ALLOW,
            reason="Trusted agent",
        )
        engine.add_rule(rule)
        request = create_action_request(
            agent_id="trusted-agent",
            action_type=ActionType.FILE,
            tool_name="file_tool",
            operation="read",
        )
        result = engine.evaluate(request)
        assert result.matched is True

    def test_evaluate_operator_ne(self, engine):
        """The 'ne' operator matches when values are different."""
        rule = PolicyRule(
            name="ne_test",
            description="Ne operator test",
            priority=1,
            condition={"agent_id": {"ne": "blocked-agent"}},
            decision=DecisionType.ALLOW,
            reason="Not blocked",
        )
        engine.add_rule(rule)
        request = create_action_request(
            agent_id="normal-agent",
            action_type=ActionType.FILE,
            tool_name="file_tool",
            operation="read",
        )
        result = engine.evaluate(request)
        assert result.matched is True

    def test_evaluate_operator_exists_true(self, engine):
        """The 'exists' operator matches when field is present."""
        rule = PolicyRule(
            name="exists_test",
            description="Exists operator test",
            priority=1,
            condition={"parameters.path": {"exists": True}},
            decision=DecisionType.ALLOW,
            reason="Path exists",
        )
        engine.add_rule(rule)
        request = create_action_request(
            agent_id="agent-001",
            action_type=ActionType.FILE,
            tool_name="file_tool",
            operation="read",
            parameters={"path": "/tmp/test.txt"},
        )
        result = engine.evaluate(request)
        assert result.matched is True

    def test_evaluate_operator_exists_false(self, engine):
        """The 'exists' operator with False matches when field is absent."""
        rule = PolicyRule(
            name="not_exists_test",
            description="Exists False operator test",
            priority=1,
            condition={"parameters.missing_field": {"exists": False}},
            decision=DecisionType.ALLOW,
            reason="Field missing",
        )
        engine.add_rule(rule)
        request = create_action_request(
            agent_id="agent-001",
            action_type=ActionType.FILE,
            tool_name="file_tool",
            operation="read",
            parameters={},
        )
        result = engine.evaluate(request)
        assert result.matched is True

    def test_evaluate_operator_contains(self, engine):
        """The 'contains' operator matches substring in value."""
        rule = PolicyRule(
            name="contains_test",
            description="Contains operator test",
            priority=1,
            condition={"tool_name": {"contains": "secret"}},
            decision=DecisionType.DENY,
            reason="Contains secret",
        )
        engine.add_rule(rule)
        request = create_action_request(
            agent_id="agent-001",
            action_type=ActionType.FILE,
            tool_name="secret_file_tool",
            operation="read",
        )
        result = engine.evaluate(request)
        assert result.matched is True

    def test_evaluate_operator_gt_gte_lt_lte(self, engine):
        """Numeric comparison operators work correctly."""
        rule = PolicyRule(
            name="range_test",
            description="Range operators test",
            priority=1,
            condition={
                "parameters.amount": {"gt": 10, "gte": 20, "lt": 100, "lte": 50}
            },
            decision=DecisionType.ALLOW,
            reason="In range",
        )
        engine.add_rule(rule)
        # amount=25 satisfies: >10, >=20, <100, <=50
        request = create_action_request(
            agent_id="agent-001",
            action_type=ActionType.PAYMENT,
            tool_name="payment_tool",
            operation="transfer",
            parameters={"amount": 25},
        )
        result = engine.evaluate(request)
        assert result.matched is True


# ---------------------------------------------------------------------------
# Evaluation - logical operators
# ---------------------------------------------------------------------------

class TestEvaluateLogicalOperators:
    """Tests for logical operators ($or, $and, $not)."""

    def test_evaluate_logical_or_first_matches(self, engine):
        """$or returns True if at least one sub-condition matches."""
        rule = PolicyRule(
            name="or_test",
            description="Or operator test",
            priority=1,
            condition={
                "$or": [
                    {"action_type": "file"},
                    {"action_type": "api"},
                ]
            },
            decision=DecisionType.ALLOW,
            reason="Or matched",
        )
        engine.add_rule(rule)
        request = create_action_request(
            agent_id="agent-001",
            action_type=ActionType.FILE,
            tool_name="file_tool",
            operation="read",
        )
        result = engine.evaluate(request)
        assert result.matched is True

    def test_evaluate_logical_or_second_matches(self, engine):
        """$or returns True if the second sub-condition matches."""
        rule = PolicyRule(
            name="or_test",
            description="Or operator test",
            priority=1,
            condition={
                "$or": [
                    {"action_type": "file"},
                    {"action_type": "api"},
                ]
            },
            decision=DecisionType.ALLOW,
            reason="Or matched",
        )
        engine.add_rule(rule)
        request = create_action_request(
            agent_id="agent-001",
            action_type=ActionType.API,
            tool_name="api_tool",
            operation="GET",
        )
        result = engine.evaluate(request)
        assert result.matched is True

    def test_evaluate_logical_and_both_match(self, engine):
        """$and returns True only if ALL sub-conditions match."""
        rule = PolicyRule(
            name="and_test",
            description="And operator test",
            priority=1,
            condition={
                "$and": [
                    {"action_type": "file"},
                    {"operation": "read"},
                ]
            },
            decision=DecisionType.ALLOW,
            reason="And matched",
        )
        engine.add_rule(rule)
        request = create_action_request(
            agent_id="agent-001",
            action_type=ActionType.FILE,
            tool_name="file_tool",
            operation="read",
        )
        result = engine.evaluate(request)
        assert result.matched is True

    def test_evaluate_logical_and_one_fails(self, engine):
        """$and returns False if any sub-condition fails."""
        rule = PolicyRule(
            name="and_test",
            description="And operator test",
            priority=1,
            condition={
                "$and": [
                    {"action_type": "file"},
                    {"operation": "read"},
                ]
            },
            decision=DecisionType.ALLOW,
            reason="And matched",
        )
        engine.add_rule(rule)
        request = create_action_request(
            agent_id="agent-001",
            action_type=ActionType.FILE,
            tool_name="file_tool",
            operation="delete",
        )
        result = engine.evaluate(request)
        assert result.matched is False

    def test_evaluate_logical_not(self, engine):
        """$not inverts the condition result."""
        rule = PolicyRule(
            name="not_test",
            description="Not operator test",
            priority=1,
            condition={"$not": {"action_type": "payment"}},
            decision=DecisionType.ALLOW,
            reason="Not payment",
        )
        engine.add_rule(rule)
        request = create_action_request(
            agent_id="agent-001",
            action_type=ActionType.FILE,
            tool_name="file_tool",
            operation="read",
        )
        result = engine.evaluate(request)
        assert result.matched is True


# ---------------------------------------------------------------------------
# Evaluation - nested fields and defaults
# ---------------------------------------------------------------------------

class TestEvaluateNestedAndDefaults:
    """Tests for dot-notation field access and default behavior."""

    def test_evaluate_nested_field_dot_notation(self, engine):
        """Dot notation (parameters.amount) accesses nested dict fields."""
        engine.load_policies(
            _POLICIES_YAML
        )
        request = create_action_request(
            agent_id="agent-001",
            action_type=ActionType.PAYMENT,
            tool_name="payment_tool",
            operation="transfer",
            parameters={"amount": 5000},
        )
        result = engine.evaluate(request)
        assert result.matched is True
        assert result.decision == DecisionType.QUARANTINE
        assert result.matched_rule == "payment_large"

    def test_evaluate_no_match_returns_default(self, engine):
        """When no rule matches, the default decision is REQUIRE_APPROVAL."""
        # Engine with no rules loaded
        request = create_action_request(
            agent_id="agent-001",
            action_type=ActionType.SECURITY_SCAN,
            tool_name="scan_tool",
            operation="run_scan",
        )
        result = engine.evaluate(request)
        assert result.matched is False
        assert result.decision == DecisionType.REQUIRE_APPROVAL
        assert "default" in result.reason.lower()

    def test_evaluate_disabled_rule_is_skipped(self, engine):
        """Disabled rules are not evaluated."""
        rule_allow = PolicyRule(
            name="allow_all",
            description="Allow everything",
            priority=1,
            condition={"action_type": "file"},
            decision=DecisionType.ALLOW,
            reason="Allow all files",
            enabled=True,
        )
        rule_deny = PolicyRule(
            name="deny_all",
            description="Deny everything",
            priority=1,
            condition={"action_type": "file"},
            decision=DecisionType.DENY,
            reason="Deny all files",
            enabled=False,
        )
        engine.add_rule(rule_allow)
        engine.add_rule(rule_deny)
        request = create_action_request(
            agent_id="agent-001",
            action_type=ActionType.FILE,
            tool_name="file_tool",
            operation="read",
        )
        result = engine.evaluate(request)
        # The allow rule should match first since deny is disabled
        assert result.decision == DecisionType.ALLOW
        assert result.matched_rule == "allow_all"


# ---------------------------------------------------------------------------
# Policy priority
# ---------------------------------------------------------------------------

class TestPolicyPriority:
    """Tests for priority-based rule ordering."""

    def test_policy_priority_lower_first(self, engine):
        """Lower priority numbers are evaluated first."""
        rule1 = PolicyRule(
            name="low_priority",
            description="Priority 100",
            priority=100,
            condition={"action_type": "file"},
            decision=DecisionType.DENY,
            reason="Low priority deny",
        )
        rule2 = PolicyRule(
            name="high_priority",
            description="Priority 1",
            priority=1,
            condition={"action_type": "file"},
            decision=DecisionType.ALLOW,
            reason="High priority allow",
        )
        engine.add_rule(rule1)
        engine.add_rule(rule2)
        request = create_action_request(
            agent_id="agent-001",
            action_type=ActionType.FILE,
            tool_name="file_tool",
            operation="read",
        )
        result = engine.evaluate(request)
        # Priority 1 should match first
        assert result.matched_rule == "high_priority"
        assert result.decision == DecisionType.ALLOW

    def test_first_matching_rule_wins(self, engine):
        """The first matching rule in priority order wins."""
        rule1 = PolicyRule(
            name="first",
            description="First match",
            priority=1,
            condition={"operation": "read"},
            decision=DecisionType.ALLOW,
            reason="First",
        )
        rule2 = PolicyRule(
            name="second",
            description="Second match",
            priority=2,
            condition={"action_type": "file"},
            decision=DecisionType.DENY,
            reason="Second",
        )
        engine.add_rule(rule1)
        engine.add_rule(rule2)
        request = create_action_request(
            agent_id="agent-001",
            action_type=ActionType.FILE,
            tool_name="file_tool",
            operation="read",
        )
        result = engine.evaluate(request)
        assert result.matched_rule == "first"

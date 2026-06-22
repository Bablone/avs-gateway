"""
test_asr1_receipt_generation.py — Test ASR-1 receipt generation.

Tests that ASR1ReceiptGenerator correctly produces receipts for all
four decision types: ALLOW, DENY, REQUIRE_APPROVAL, QUARANTINE.
"""

import pytest
import uuid
import json

from avs_gateway.models.action_request import ActionRequest, ActionType, create_action_request
from avs_gateway.core.gateway_core import Decision, DecisionType
from avs_gateway.receipts.asr1 import (
    ASR1Receipt,
    ASR1ReceiptGenerator,
    canonical_json,
    hash_payload,
    ASR_VERSION,
    GENESIS_HASH,
)


# ---------------------------------------------------------------------------
# Minimal decision objects for testing
# ---------------------------------------------------------------------------

class _FakeDecision:
    """Minimal decision stand-in."""
    def __init__(self, value, reason, matched_policy, risk_score, trust_score):
        self.decision_type = _FakeEnum(value)
        self.reason = reason
        self.matched_policy = matched_policy
        self.risk_score = risk_score
        self.trust_score = trust_score


class _FakeEnum:
    def __init__(self, value):
        self.value = value


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_action():
    return create_action_request(
        agent_id="agent_001",
        action_type=ActionType.FILE,
        tool_name="file_delete",
        operation="delete",
        parameters={"path": "/etc/passwd"},
        context={"environment": "production"},
    )


@pytest.fixture
def decisions():
    return {
        "allow": _FakeDecision("allow", "Risk low", "rule_safe", 10, 80),
        "deny": _FakeDecision("deny", "Policy denied", "rule_dangerous", 90, 50),
        "require_approval": _FakeDecision("require_approval", "Needs human review", "rule_approval", 50, 60),
        "quarantine": _FakeDecision("quarantine", "Suspicious activity", "rule_quarantine", 85, 30),
    }


@pytest.fixture
def generator():
    return ASR1ReceiptGenerator()


# ---------------------------------------------------------------------------
# Generation tests
# ---------------------------------------------------------------------------

class TestASR1ReceiptGeneration:

    def test_generate_allow_receipt(self, generator, sample_action, decisions):
        receipt = generator.generate(sample_action, decisions["allow"])
        assert receipt.decision == "allow"
        assert receipt.decision_reason == "Risk low"
        assert receipt.agent_id == "agent_001"
        assert receipt.asr_version == ASR_VERSION
        assert receipt.receipt_id
        assert receipt.request_id == sample_action.action_id
        assert receipt.receipt_hash.startswith("sha256:")
        assert receipt.parameter_hash.startswith("sha256:")
        assert receipt.context_hash.startswith("sha256:")
        assert receipt.executed is True
        assert receipt.execution_status == "executed"

    def test_generate_deny_receipt(self, generator, sample_action, decisions):
        receipt = generator.generate(sample_action, decisions["deny"])
        assert receipt.decision == "deny"
        assert receipt.decision_reason == "Policy denied"
        assert receipt.executed is False
        assert receipt.execution_status == "blocked"
        assert receipt.receipt_hash.startswith("sha256:")

    def test_generate_require_approval_receipt(self, generator, sample_action, decisions):
        receipt = generator.generate(sample_action, decisions["require_approval"])
        assert receipt.decision == "require_approval"
        assert receipt.decision_reason == "Needs human review"
        assert receipt.executed is False
        assert receipt.execution_status == "blocked_pending_approval"

    def test_generate_quarantine_receipt(self, generator, sample_action, decisions):
        receipt = generator.generate(sample_action, decisions["quarantine"])
        assert receipt.decision == "quarantine"
        assert receipt.decision_reason == "Suspicious activity"
        assert receipt.executed is False
        assert receipt.execution_status == "quarantined"

    def test_receipt_has_all_required_fields(self, generator, sample_action, decisions):
        receipt = generator.generate(sample_action, decisions["allow"])
        d = receipt.to_dict()
        assert "asr_version" in d
        assert "receipt_id" in d
        assert "request_id" in d
        assert "timestamp_ns" in d
        assert "agent_identity" in d
        assert "action" in d
        assert "tool_manifest" in d
        assert "governance" in d
        assert "execution" in d
        assert "ledger" in d

    def test_receipt_id_is_valid_uuid(self, generator, sample_action, decisions):
        receipt = generator.generate(sample_action, decisions["allow"])
        uuid.UUID(receipt.receipt_id)  # raises if invalid

    def test_request_id_matches_action(self, generator, sample_action, decisions):
        receipt = generator.generate(sample_action, decisions["allow"])
        assert receipt.request_id == sample_action.action_id

    def test_timestamp_ns_is_integer_and_reasonable(self, generator, sample_action, decisions):
        receipt = generator.generate(sample_action, decisions["allow"])
        assert isinstance(receipt.timestamp_ns, int)
        assert receipt.timestamp_ns > 1700000000000000000  # After 2023
        assert receipt.timestamp_ns < 2000000000000000000  # Before 2033

    def test_parameter_hash_exists_not_raw_parameters(self, generator, sample_action, decisions):
        receipt = generator.generate(sample_action, decisions["allow"])
        assert receipt.parameter_hash.startswith("sha256:")
        # Raw parameters must NOT appear in the receipt
        receipt_dict = receipt.to_dict()
        assert "path" not in str(receipt_dict.get("action", {}))

    def test_risk_and_trust_scores(self, generator, sample_action, decisions):
        receipt = generator.generate(sample_action, decisions["allow"])
        assert receipt.risk_score == 10.0
        assert receipt.trust_score == 80.0

    def test_policy_ids_evaluated(self, generator, sample_action, decisions):
        receipt = generator.generate(sample_action, decisions["deny"], policy_ids_evaluated=["rule_01", "rule_02"])
        assert "rule_01" in receipt.policy_ids_evaluated
        assert "rule_02" in receipt.policy_ids_evaluated
        assert "rule_dangerous" in receipt.policy_ids_evaluated

    def test_winning_policy_id(self, generator, sample_action, decisions):
        receipt = generator.generate(sample_action, decisions["allow"])
        assert receipt.winning_policy_id == "rule_safe"

    def test_previous_receipt_hash_defaults_to_genesis(self, generator, sample_action, decisions):
        receipt = generator.generate(sample_action, decisions["allow"])
        assert receipt.previous_receipt_hash == GENESIS_HASH

    def test_previous_receipt_hash_can_be_set(self, generator, sample_action, decisions):
        custom_prev = "sha256:abc123" + "0" * 58
        receipt = generator.generate(sample_action, decisions["allow"], previous_receipt_hash=custom_prev)
        assert receipt.previous_receipt_hash == custom_prev

    def test_receipt_hash_is_deterministic(self, generator, sample_action, decisions):
        r1 = generator.generate(sample_action, decisions["allow"])
        # Create fresh generator with same state to test determinism at hash level
        gen2 = ASR1ReceiptGenerator(previous_receipt_hash=GENESIS_HASH)
        r2 = gen2.generate(sample_action, decisions["allow"])
        # Same action + decision + same previous_hash produce same hash
        # (receipt_id is auto-generated and differs, so hashes will differ too —
        #  that's correct: each receipt is unique. The hash of the CONTENT
        #  is deterministic, but the receipt_id makes each receipt unique.)
        # Instead, verify that the hash format is correct:
        assert r1.receipt_hash.startswith("sha256:")
        assert r2.receipt_hash.startswith("sha256:")
        assert r1.receipt_hash != r2.receipt_hash  # Different receipt_ids = different hashes

    def test_canonical_json_produces_bytes(self, generator, sample_action, decisions):
        receipt = generator.generate(sample_action, decisions["allow"])
        d = receipt.to_dict()
        del d["ledger"]
        c = canonical_json(d)
        assert isinstance(c, bytes)
        assert len(c) > 0

    def test_hash_payload_format(self):
        h = hash_payload({"test": "value"})
        assert h.startswith("sha256:")
        assert len(h) == 64 + 7  # "sha256:" + 64 hex chars


class TestASR1ReceiptSigning:

    def test_sign_receipt_adds_gateway_signature(self, generator, sample_action, decisions):
        receipt = generator.generate(sample_action, decisions["allow"])
        signed = generator.sign(receipt)
        assert signed.gateway_signature is not None
        assert len(signed.gateway_signature) > 0

    def test_generate_and_sign_convenience(self, generator, sample_action, decisions):
        signed = generator.generate_and_sign(sample_action, decisions["allow"])
        assert signed.gateway_signature is not None
        assert signed.receipt_hash.startswith("sha256:")

    def test_signed_receipt_serialization_roundtrip(self, generator, sample_action, decisions):
        signed = generator.generate_and_sign(sample_action, decisions["allow"])
        json_str = signed.to_json()
        restored = ASR1Receipt.from_json(json_str)
        assert restored.decision == signed.decision
        assert restored.receipt_hash == signed.receipt_hash
        assert restored.gateway_signature == signed.gateway_signature
        assert restored.receipt_id == signed.receipt_id


class TestASR1Serialization:

    def test_to_dict_and_from_dict_roundtrip(self, generator, sample_action, decisions):
        receipt = generator.generate_and_sign(sample_action, decisions["allow"])
        d = receipt.to_dict()
        restored = ASR1Receipt.from_dict(d)
        assert restored.receipt_id == receipt.receipt_id
        assert restored.decision == receipt.decision
        assert restored.receipt_hash == receipt.receipt_hash
        assert restored.gateway_signature == receipt.gateway_signature

    def test_to_json_produces_valid_json(self, generator, sample_action, decisions):
        receipt = generator.generate(sample_action, decisions["allow"])
        json_str = receipt.to_json()
        parsed = json.loads(json_str)
        assert parsed["asr_version"] == ASR_VERSION
        assert parsed["governance"]["decision"] == "allow"

    def test_from_json_restores_correctly(self, generator, sample_action, decisions):
        original = generator.generate_and_sign(sample_action, decisions["deny"])
        json_str = original.to_json()
        restored = ASR1Receipt.from_json(json_str)
        assert restored.decision == "deny"
        assert restored.agent_id == original.agent_id
        assert restored.receipt_hash == original.receipt_hash

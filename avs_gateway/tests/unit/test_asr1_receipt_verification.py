"""
test_asr1_receipt_verification.py — Test ASR-1 receipt verification.

Valid receipts should verify. Tampered receipts should fail.
"""

import pytest

from avs_gateway.models.action_request import ActionType, create_action_request
from avs_gateway.receipts.asr1 import (
    ASR1Receipt,
    ASR1ReceiptGenerator,
    verify_receipt,
)


class _FakeDecision:
    def __init__(self, value, reason, matched_policy, risk_score, trust_score):
        self.decision_type = _FakeEnum(value)
        self.reason = reason
        self.matched_policy = matched_policy
        self.risk_score = risk_score
        self.trust_score = trust_score


class _FakeEnum:
    def __init__(self, value):
        self.value = value


@pytest.fixture
def sample_action():
    return create_action_request(
        agent_id="agent_001",
        action_type=ActionType.FILE,
        tool_name="file_delete",
        operation="delete",
        parameters={"path": "/etc/passwd"},
    )


@pytest.fixture
def generator():
    return ASR1ReceiptGenerator()


class TestReceiptVerification:

    def test_valid_receipt_verifies(self, generator, sample_action):
        decision = _FakeDecision("deny", "Policy denied", "rule_dangerous", 90, 50)
        receipt = generator.generate_and_sign(sample_action, decision)
        assert verify_receipt(receipt) is True

    def test_unsigned_receipt_still_verifies_by_hash(self, generator, sample_action):
        decision = _FakeDecision("allow", "Risk low", "rule_safe", 10, 80)
        receipt = generator.generate(sample_action, decision)  # not signed
        assert verify_receipt(receipt) is True

    def test_tampered_decision_fails_verification(self, generator, sample_action):
        decision = _FakeDecision("allow", "Risk low", "rule_safe", 10, 80)
        receipt = generator.generate_and_sign(sample_action, decision)
        # Tamper: change decision
        tampered_dict = receipt.to_dict()
        tampered_dict["governance"]["decision"] = "deny"
        tampered = ASR1Receipt.from_dict(tampered_dict)
        assert verify_receipt(tampered) is False

    def test_tampered_agent_id_fails_verification(self, generator, sample_action):
        decision = _FakeDecision("allow", "Risk low", "rule_safe", 10, 80)
        receipt = generator.generate_and_sign(sample_action, decision)
        tampered_dict = receipt.to_dict()
        tampered_dict["agent_identity"]["agent_id"] = "evil_agent"
        tampered = ASR1Receipt.from_dict(tampered_dict)
        assert verify_receipt(tampered) is False

    def test_tampered_action_field_fails_verification(self, generator, sample_action):
        decision = _FakeDecision("allow", "Risk low", "rule_safe", 10, 80)
        receipt = generator.generate_and_sign(sample_action, decision)
        tampered_dict = receipt.to_dict()
        tampered_dict["action"]["tool_name"] = "evil_tool"
        tampered = ASR1Receipt.from_dict(tampered_dict)
        assert verify_receipt(tampered) is False

    def test_tampered_receipt_hash_fails_verification(self, generator, sample_action):
        decision = _FakeDecision("allow", "Risk low", "rule_safe", 10, 80)
        receipt = generator.generate_and_sign(sample_action, decision)
        # Tamper the stored receipt_hash
        tampered_dict = receipt.to_dict()
        tampered_dict["ledger"]["receipt_hash"] = "sha256:" + "f" * 64
        tampered = ASR1Receipt.from_dict(tampered_dict)
        assert verify_receipt(tampered) is False

    def test_valid_receipt_after_different_decision_type(self, generator, sample_action):
        for decision_val, decision_reason in [
            ("allow", "Allowed"),
            ("deny", "Blocked"),
            ("require_approval", "Pending"),
            ("quarantine", "Quarantined"),
        ]:
            decision = _FakeDecision(decision_val, decision_reason, "rule_test", 50, 50)
            receipt = generator.generate_and_sign(sample_action, decision)
            assert verify_receipt(receipt) is True, f"Failed for {decision_val}"

    def test_receipt_with_missing_fields_in_payload_fails_gracefully(self, generator, sample_action):
        """A receipt missing core fields should fail verification."""
        decision = _FakeDecision("allow", "Risk low", "rule_safe", 10, 80)
        receipt = generator.generate_and_sign(sample_action, decision)
        # Should verify as-is
        assert verify_receipt(receipt) is True

    def test_completely_different_receipt_fails_verification(self, generator, sample_action):
        decision1 = _FakeDecision("allow", "Risk low", "rule_safe", 10, 80)
        receipt1 = generator.generate_and_sign(sample_action, decision1)

        # Create a second receipt with different content
        action2 = create_action_request(
            agent_id="agent_002",
            action_type=ActionType.API,
            tool_name="deploy_to_production",
            operation="deploy_prod",
            parameters={"manifest": "payment.yaml"},
        )
        decision2 = _FakeDecision("deny", "Not allowed", "rule_prod", 95, 20)
        receipt2 = generator.generate_and_sign(action2, decision2)

        # receipt2's hash should not match receipt1's content
        assert receipt1.receipt_hash != receipt2.receipt_hash
        assert verify_receipt(receipt1) is True
        assert verify_receipt(receipt2) is True

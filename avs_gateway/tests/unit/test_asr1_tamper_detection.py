"""
test_asr1_tamper_detection.py — Test tamper detection on ASR-1 receipts.

Any modification to a receipt should break verification.
Chain integrity should detect removed or phantom receipts.
"""

import pytest

from avs_gateway.models.action_request import ActionType, create_action_request
from avs_gateway.receipts.asr1 import (
    ASR1Receipt,
    ASR1ReceiptGenerator,
    verify_receipt,
    verify_chain,
    GENESIS_HASH,
)


class _FakeDecision:
    def __init__(self, value, reason="", matched_policy=None, risk_score=50, trust_score=50):
        self.decision_type = _FakeEnum(value)
        self.reason = reason
        self.matched_policy = matched_policy
        self.risk_score = risk_score
        self.trust_score = trust_score


class _FakeEnum:
    def __init__(self, value):
        self.value = value


@pytest.fixture
def generator():
    return ASR1ReceiptGenerator()


class TestTamperDetection:

    def test_changing_one_character_breaks_verification(self, generator):
        action = create_action_request(
            agent_id="agent_001", action_type=ActionType.FILE,
            tool_name="file_read", operation="read",
            parameters={"path": "report.txt"},
        )
        decision = _FakeDecision("allow", "Safe read", "rule_read", 5, 90)
        receipt = generator.generate_and_sign(action, decision)

        # Modify one character in the decision_reason
        tampered_dict = receipt.to_dict()
        tampered_dict["governance"]["decision_reason"] = receipt.decision_reason + "X"
        tampered = ASR1Receipt.from_dict(tampered_dict)

        assert verify_receipt(receipt) is True
        assert verify_receipt(tampered) is False

    def test_swapping_previous_receipt_hash_breaks_chain(self, generator):
        action1 = create_action_request(
            agent_id="agent_001", action_type=ActionType.FILE,
            tool_name="file_read", operation="read", parameters={"path": "a.txt"},
        )
        action2 = create_action_request(
            agent_id="agent_001", action_type=ActionType.FILE,
            tool_name="file_read", operation="read", parameters={"path": "b.txt"},
        )

        receipt1 = generator.generate_and_sign(action1, _FakeDecision("allow"))
        receipt2 = generator.generate_and_sign(action2, _FakeDecision("allow"))

        # receipt2 should link to receipt1
        assert receipt2.previous_receipt_hash == receipt1.receipt_hash
        assert verify_chain([receipt1, receipt2]) is True

        # Tamper: swap receipt2's previous hash
        tampered_dict = receipt2.to_dict()
        tampered_dict["ledger"]["previous_receipt_hash"] = GENESIS_HASH  # wrong
        tampered = ASR1Receipt.from_dict(tampered_dict)

        assert verify_chain([receipt1, tampered]) is False

    def test_removing_receipt_from_chain_breaks_verification(self, generator):
        actions = [
            create_action_request(
                agent_id="agent_001", action_type=ActionType.FILE,
                tool_name="file_read", operation="read", parameters={"path": f"{i}.txt"},
            )
            for i in range(3)
        ]
        receipts = [
            generator.generate_and_sign(a, _FakeDecision("allow"))
            for a in actions
        ]

        # Full chain is valid
        assert verify_chain(receipts) is True

        # Remove middle receipt
        partial = [receipts[0], receipts[2]]
        # receipts[2] previous should point to receipts[1] which is missing
        assert verify_chain(partial) is False

    def test_adding_phantom_receipt_breaks_chain(self, generator):
        actions = [
            create_action_request(
                agent_id="agent_001", action_type=ActionType.FILE,
                tool_name="file_read", operation="read", parameters={"path": f"{i}.txt"},
            )
            for i in range(2)
        ]
        receipts = [
            generator.generate_and_sign(a, _FakeDecision("allow"))
            for a in actions
        ]

        # Valid 2-receipt chain
        assert verify_chain(receipts) is True

        # Insert phantom between them
        phantom_action = create_action_request(
            agent_id="hacker", action_type=ActionType.API,
            tool_name="evil_tool", operation="hack", parameters={},
        )
        phantom = generator.generate_and_sign(phantom_action, _FakeDecision("allow"))
        # Force phantom to link to first receipt (like it's in the chain)
        phantom_dict = phantom.to_dict()
        phantom_dict["ledger"]["previous_receipt_hash"] = receipts[0].receipt_hash
        phantom_fixed = ASR1Receipt.from_dict(phantom_dict)

        # Chain with phantom inserted
        poisoned = [receipts[0], phantom_fixed, receipts[1]]
        # receipts[1] expects phantom's hash as previous, but got something else
        assert verify_chain(poisoned) is False

    def test_empty_chain_verifies(self):
        assert verify_chain([]) is True

    def test_single_receipt_chain_verifies(self, generator):
        action = create_action_request(
            agent_id="agent_001", action_type=ActionType.FILE,
            tool_name="file_read", operation="read", parameters={"path": "x.txt"},
        )
        receipt = generator.generate_and_sign(action, _FakeDecision("allow"))
        assert verify_chain([receipt]) is True

    def test_tampered_risk_score_fails_verification(self, generator):
        action = create_action_request(
            agent_id="agent_001", action_type=ActionType.API,
            tool_name="deploy", operation="deploy_prod", parameters={"manifest": "pay.yaml"},
        )
        decision = _FakeDecision("require_approval", "Needs approval", "rule_prod", 85, 50)
        receipt = generator.generate_and_sign(action, decision)

        tampered_dict = receipt.to_dict()
        tampered_dict["governance"]["risk_score"] = 10.0  # changed
        tampered = ASR1Receipt.from_dict(tampered_dict)

        assert verify_receipt(receipt) is True
        assert verify_receipt(tampered) is False

    def test_tampered_trust_score_fails_verification(self, generator):
        action = create_action_request(
            agent_id="agent_001", action_type=ActionType.FILE,
            tool_name="file_read", operation="read", parameters={"path": "ok.txt"},
        )
        receipt = generator.generate_and_sign(action, _FakeDecision("allow"))

        tampered_dict = receipt.to_dict()
        tampered_dict["governance"]["trust_score"] = 99.9  # changed
        tampered = ASR1Receipt.from_dict(tampered_dict)

        assert verify_receipt(tampered) is False

    def test_tampered_tool_name_fails_verification(self, generator):
        action = create_action_request(
            agent_id="agent_001", action_type=ActionType.FILE,
            tool_name="file_read", operation="read", parameters={"path": "ok.txt"},
        )
        receipt = generator.generate_and_sign(action, _FakeDecision("allow"))

        tampered_dict = receipt.to_dict()
        tampered_dict["action"]["tool_name"] = "file_delete"
        tampered = ASR1Receipt.from_dict(tampered_dict)

        assert verify_receipt(tampered) is False

    def test_tampered_parameter_hash_fails_verification(self, generator):
        action = create_action_request(
            agent_id="agent_001", action_type=ActionType.FILE,
            tool_name="file_read", operation="read", parameters={"path": "ok.txt"},
        )
        receipt = generator.generate_and_sign(action, _FakeDecision("allow"))

        tampered_dict = receipt.to_dict()
        tampered_dict["action"]["parameter_hash"] = "sha256:" + "f" * 64
        tampered = ASR1Receipt.from_dict(tampered_dict)

        assert verify_receipt(tampered) is False

    def test_tampered_timestamp_fails_verification(self, generator):
        action = create_action_request(
            agent_id="agent_001", action_type=ActionType.FILE,
            tool_name="file_read", operation="read", parameters={"path": "ok.txt"},
        )
        receipt = generator.generate_and_sign(action, _FakeDecision("allow"))

        tampered_dict = receipt.to_dict()
        tampered_dict["timestamp_ns"] = 9999999999999999999
        tampered = ASR1Receipt.from_dict(tampered_dict)

        assert verify_receipt(tampered) is False

    def test_five_receipt_chain_verifies(self, generator):
        actions = [
            create_action_request(
                agent_id=f"agent_00{i}", action_type=ActionType.FILE,
                tool_name="file_read", operation="read", parameters={"path": f"{i}.txt"},
            )
            for i in range(5)
        ]
        receipts = [
            generator.generate_and_sign(a, _FakeDecision("allow"))
            for a in actions
        ]
        assert verify_chain(receipts) is True

    def test_changing_agent_type_breaks_verification(self, generator):
        action = create_action_request(
            agent_id="agent_001", action_type=ActionType.FILE,
            tool_name="file_read", operation="read", parameters={"path": "ok.txt"},
        )
        receipt = generator.generate_and_sign(action, _FakeDecision("allow"))

        tampered_dict = receipt.to_dict()
        tampered_dict["agent_identity"]["agent_type"] = "hacker"
        tampered = ASR1Receipt.from_dict(tampered_dict)

        assert verify_receipt(tampered) is False

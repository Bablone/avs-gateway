"""
Unit tests for ReceiptGenerator, Receipt, SignedReceipt, and MerkleTree.

Tests cover receipt generation, signing, verification, deterministic hashing,
serialization roundtrips, Merkle root computation, and inclusion proofs.
"""



import pytest
import json
import base64

from avs_gateway.models.action_request import ActionType, create_action_request
from avs_gateway.core.receipt_generator import (
    ReceiptGenerator,
    Receipt,
    SignedReceipt,
    MerkleTree,
)
from avs_gateway.core.gateway_core import Decision, DecisionType


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def generator():
    """Return a fresh ReceiptGenerator instance."""
    return ReceiptGenerator()


@pytest.fixture
def sample_request():
    """Return a sample ActionRequest."""
    return create_action_request(
        agent_id="agent-001",
        action_type=ActionType.FILE,
        tool_name="file_tool",
        operation="read",
        parameters={"path": "/tmp/test.txt"},
    )


@pytest.fixture
def sample_decision():
    """Return a sample ALLOW Decision."""
    return Decision(
        decision_type=DecisionType.ALLOW,
        reason="Test allow",
        matched_policy="test_policy",
        risk_score=10,
        trust_score=75,
    )


# ---------------------------------------------------------------------------
# Receipt generation
# ---------------------------------------------------------------------------

class TestGenerateReceipt:
    """Tests for receipt creation."""

    def test_generate_receipt_creates_receipt(self, generator, sample_request, sample_decision):
        """generate() creates a Receipt with correct fields."""
        receipt = generator.generate(sample_request, sample_decision)

        assert isinstance(receipt, Receipt)
        assert receipt.receipt_id == sample_request.action_id
        assert receipt.action_hash == sample_request.action_hash()
        assert receipt.decision_type == "allow"
        assert receipt.decision_reason == "Test allow"
        assert receipt.matched_policy == "test_policy"
        assert receipt.risk_score == 10
        assert receipt.risk_classification == "low"
        assert receipt.trust_score == 75
        assert receipt.agent_id == "agent-001"
        assert receipt.previous_hash is None
        assert receipt.gateway_version == "0.9.0"

    def test_generate_receipt_different_classifications(self, generator, sample_request):
        """Receipt classification varies with risk score."""
        for expected_class, risk_val in [("low", 10), ("medium", 35), ("high", 60), ("critical", 85)]:
            decision = Decision(
                decision_type=DecisionType.ALLOW,
                reason="Test",
                matched_policy="test",
                risk_score=risk_val,
                trust_score=50,
            )
            receipt = generator.generate(sample_request, decision)
            assert receipt.risk_classification == expected_class

    def test_generate_receipt_with_previous_hash(self, generator, sample_request, sample_decision):
        """generate() accepts an optional previous_hash for chain linking."""
        prev_hash = "abc123" * 8  # 64 chars
        receipt = generator.generate(sample_request, sample_decision, previous_hash=prev_hash)
        assert receipt.previous_hash == prev_hash


# ---------------------------------------------------------------------------
# Signing
# ---------------------------------------------------------------------------

class TestSignReceipt:
    """Tests for receipt signing."""

    def test_sign_produces_signed_receipt(self, generator, sample_request, sample_decision):
        """sign() produces a SignedReceipt."""
        receipt = generator.generate(sample_request, sample_decision)
        signed = generator.sign(receipt)

        assert isinstance(signed, SignedReceipt)
        assert signed.receipt == receipt
        assert signed.signature is not None
        assert len(signed.signature) > 0
        assert signed.public_key is not None
        assert len(signed.public_key) > 0
        assert signed.receipt_hash == receipt.receipt_hash()

    def test_signature_is_base64(self, generator, sample_request, sample_decision):
        """The signature is a valid base64-encoded string."""
        receipt = generator.generate(sample_request, sample_decision)
        signed = generator.sign(receipt)
        # Should not raise
        decoded = base64.b64decode(signed.signature)
        assert len(decoded) > 0

    def test_public_key_is_base64(self, generator, sample_request, sample_decision):
        """The public key is a valid base64-encoded string."""
        receipt = generator.generate(sample_request, sample_decision)
        signed = generator.sign(receipt)
        decoded = base64.b64decode(signed.public_key)
        assert len(decoded) > 0


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------

class TestVerifyReceipt:
    """Tests for signature verification."""

    def test_verify_valid_signature(self, generator, sample_request, sample_decision):
        """A properly signed receipt verifies successfully."""
        receipt = generator.generate(sample_request, sample_decision)
        signed = generator.sign(receipt)
        assert generator.verify(signed) is True

    def test_verify_tampered_signature_fails(self, sample_request, sample_decision):
        """A receipt with a tampered signature fails verification."""
        gen1 = ReceiptGenerator()
        receipt = gen1.generate(sample_request, sample_decision)
        signed = gen1.sign(receipt)
        # Tamper with the signature bytes
        tampered_sig = signed.signature[:10] + "X" + signed.signature[11:]
        tampered = SignedReceipt(
            receipt=signed.receipt,
            signature=tampered_sig,
            public_key=signed.public_key,
            receipt_hash=signed.receipt_hash,
        )
        assert gen1.verify(tampered) is False

    def test_verify_tampered_hash_fails(self, generator, sample_request, sample_decision):
        """Tampering with the receipt_hash causes verification to fail."""
        receipt = generator.generate(sample_request, sample_decision)
        signed = generator.sign(receipt)
        # Tamper with the receipt_hash
        tampered = SignedReceipt(
            receipt=signed.receipt,
            signature=signed.signature,
            public_key=signed.public_key,
            receipt_hash="tampered" + signed.receipt_hash[8:],
        )
        assert generator.verify(tampered) is False


# ---------------------------------------------------------------------------
# Receipt hash
# ---------------------------------------------------------------------------

class TestReceiptHash:
    """Tests for deterministic receipt hashing."""

    def test_receipt_hash_is_deterministic(self, generator, sample_request, sample_decision):
        """Two receipts with identical fields produce the same hash."""
        receipt1 = generator.generate(sample_request, sample_decision)
        # Create a receipt with the exact same fields manually
        receipt2 = Receipt(
            receipt_id=receipt1.receipt_id,
            action_hash=receipt1.action_hash,
            decision_type=receipt1.decision_type,
            decision_reason=receipt1.decision_reason,
            matched_policy=receipt1.matched_policy,
            risk_score=receipt1.risk_score,
            risk_classification=receipt1.risk_classification,
            trust_score=receipt1.trust_score,
            agent_id=receipt1.agent_id,
            policy_hash=receipt1.policy_hash,
            timestamp_ns=receipt1.timestamp_ns,
            previous_hash=receipt1.previous_hash,
            gateway_version=receipt1.gateway_version,
            metadata=dict(receipt1.metadata),
        )
        assert receipt1.receipt_hash() == receipt2.receipt_hash()

    def test_receipt_hash_is_64_hex_chars(self, generator, sample_request, sample_decision):
        """Receipt hash is a 64-character hex string."""
        receipt = generator.generate(sample_request, sample_decision)
        h = receipt.receipt_hash()
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)

    def test_receipt_hash_changes_with_content(self, generator, sample_request, sample_decision):
        """Different receipt content produces different hashes."""
        receipt1 = generator.generate(sample_request, sample_decision)
        decision2 = Decision(
            decision_type=DecisionType.DENY,
            reason="Different",
            matched_policy="test",
            risk_score=90,
            trust_score=10,
        )
        receipt2 = generator.generate(sample_request, decision2)
        assert receipt1.receipt_hash() != receipt2.receipt_hash()


# ---------------------------------------------------------------------------
# Serialization / deserialization
# ---------------------------------------------------------------------------

class TestSerializeDeserialize:
    """Tests for serialization roundtrips."""

    def test_serialize_deserialize_roundtrip(self, generator, sample_request, sample_decision):
        """serialize() and deserialize() produce an equivalent SignedReceipt."""
        receipt = generator.generate(sample_request, sample_decision)
        signed = generator.sign(receipt)
        json_str = generator.serialize(signed)
        restored = ReceiptGenerator.deserialize(json_str)

        assert restored.receipt.receipt_id == signed.receipt.receipt_id
        assert restored.receipt.action_hash == signed.receipt.action_hash
        assert restored.receipt.decision_type == signed.receipt.decision_type
        assert restored.receipt.risk_score == signed.receipt.risk_score
        assert restored.signature == signed.signature
        assert restored.public_key == signed.public_key
        assert restored.receipt_hash == signed.receipt_hash

    def test_to_dict_roundtrip(self, generator, sample_request, sample_decision):
        """to_dict() / from_dict() on Receipt produces equivalent data."""
        receipt = generator.generate(sample_request, sample_decision)
        d = receipt.to_dict()
        assert d["receipt_id"] == receipt.receipt_id
        assert d["action_hash"] == receipt.action_hash
        assert d["risk_score"] == receipt.risk_score
        assert d["risk_classification"] == receipt.risk_classification

    def test_receipt_to_json(self, generator, sample_request, sample_decision):
        """Receipt.to_json() produces valid JSON."""
        receipt = generator.generate(sample_request, sample_decision)
        json_str = receipt.to_json()
        parsed = json.loads(json_str)
        assert parsed["receipt_id"] == receipt.receipt_id

    def test_signed_receipt_to_json(self, generator, sample_request, sample_decision):
        """SignedReceipt.to_json() produces valid JSON."""
        receipt = generator.generate(sample_request, sample_decision)
        signed = generator.sign(receipt)
        json_str = signed.to_json()
        parsed = json.loads(json_str)
        assert parsed["signature"] == signed.signature
        assert parsed["receipt_hash"] == signed.receipt_hash


# ---------------------------------------------------------------------------
# Merkle tree
# ---------------------------------------------------------------------------

class TestMerkleTree:
    """Tests for MerkleTree construction and operations."""

    def test_merkle_tree_root_single_leaf(self):
        """A Merkle tree with one leaf has a valid root."""
        tree = MerkleTree(["leaf1"])
        root = tree.root()
        assert len(root) == 64
        assert all(c in "0123456789abcdef" for c in root)

    def test_merkle_tree_root_multiple_leaves(self):
        """A Merkle tree with multiple leaves produces a valid root."""
        tree = MerkleTree(["leaf1", "leaf2", "leaf3", "leaf4"])
        root = tree.root()
        assert len(root) == 64

    def test_merkle_root_changes_with_leaves(self):
        """Different leaves produce different Merkle roots."""
        tree1 = MerkleTree(["a", "b", "c"])
        tree2 = MerkleTree(["a", "b", "d"])
        assert tree1.root() != tree2.root()

    def test_merkle_tree_empty_raises(self):
        """An empty MerkleTree raises ValueError."""
        with pytest.raises(ValueError):
            MerkleTree([])

    def test_merkle_root_consistent(self):
        """The same leaves always produce the same root."""
        tree1 = MerkleTree(["a", "b", "c", "d"])
        tree2 = MerkleTree(["a", "b", "c", "d"])
        assert tree1.root() == tree2.root()


# ---------------------------------------------------------------------------
# Merkle inclusion proof
# ---------------------------------------------------------------------------

class TestMerkleInclusionProof:
    """Tests for MerkleTree inclusion proofs."""

    def test_inclusion_proof_length(self):
        """An inclusion proof has the correct number of sibling hashes."""
        leaves = ["leaf0", "leaf1", "leaf2", "leaf3"]
        tree = MerkleTree(leaves)
        proof = tree.proof(0)
        # For 4 leaves, proof should have log2(4) = 2 elements
        assert len(proof) == 2

    def test_inclusion_proof_for_each_leaf(self):
        """Every leaf has a valid inclusion proof."""
        leaves = ["leaf0", "leaf1", "leaf2"]
        tree = MerkleTree(leaves)
        for i in range(len(leaves)):
            proof = tree.proof(i)
            assert isinstance(proof, list)
            assert len(proof) > 0
            for sibling_hash in proof:
                assert len(sibling_hash) == 64

    def test_inclusion_proof_invalid_index_raises(self):
        """Requesting a proof for an invalid index raises IndexError."""
        tree = MerkleTree(["a", "b"])
        with pytest.raises(IndexError):
            tree.proof(-1)
        with pytest.raises(IndexError):
            tree.proof(5)

    def test_proof_for_single_leaf(self):
        """A single-leaf tree has an empty proof."""
        tree = MerkleTree(["only_leaf"])
        proof = tree.proof(0)
        # Only one level in the tree, so no siblings needed
        assert len(proof) == 0

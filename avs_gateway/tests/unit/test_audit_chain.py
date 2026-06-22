"""
Unit tests for AuditChain and ChainEntry.

Tests cover chain growth, integrity verification, hash linking,
range queries, and JSON export.
"""



import pytest
import json

from avs_gateway.models.action_request import ActionType, create_action_request
from avs_gateway.core.audit_chain import AuditChain, ChainEntry
from avs_gateway.core.receipt_generator import ReceiptGenerator
from avs_gateway.core.gateway_core import Decision, DecisionType


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def chain():
    """Return a fresh AuditChain instance."""
    return AuditChain()


@pytest.fixture
def generator():
    """Return a fresh ReceiptGenerator."""
    return ReceiptGenerator()


def _make_signed_receipt(generator):
    """Helper to create a signed receipt."""
    request = create_action_request(
        agent_id="agent-001",
        action_type=ActionType.FILE,
        tool_name="file_tool",
        operation="read",
    )
    decision = Decision(
        decision_type=DecisionType.ALLOW,
        reason="Test",
        matched_policy="test_policy",
        risk_score=10,
        trust_score=75,
    )
    receipt = generator.generate(request, decision)
    return generator.sign(receipt)


# ---------------------------------------------------------------------------
# Append entry
# ---------------------------------------------------------------------------

class TestAppendEntry:
    """Tests for appending entries to the chain."""

    def test_append_increases_length(self, chain, generator):
        """Appending an entry increases chain length."""
        assert chain.length() == 0
        signed = _make_signed_receipt(generator)
        chain.append(signed)
        assert chain.length() == 1

    def test_append_returns_chain_entry(self, chain, generator):
        """append() returns a ChainEntry."""
        signed = _make_signed_receipt(generator)
        entry = chain.append(signed)
        assert isinstance(entry, ChainEntry)
        assert entry.sequence_number == 0

    def test_append_multiple_entries(self, chain, generator):
        """Appending multiple entries increases length correctly."""
        for i in range(5):
            signed = _make_signed_receipt(generator)
            entry = chain.append(signed)
            assert entry.sequence_number == i
        assert chain.length() == 5

    def test_last_hash_changes_after_append(self, chain, generator):
        """The chain's last hash changes after each append."""
        hash_before = chain.last_hash()
        signed = _make_signed_receipt(generator)
        chain.append(signed)
        hash_after = chain.last_hash()
        assert hash_after != hash_before

    def test_genesis_hash_is_zeros(self, chain):
        """The initial last_hash is 64 zeros."""
        assert chain.last_hash() == "0" * 64


# ---------------------------------------------------------------------------
# Chain integrity
# ---------------------------------------------------------------------------

class TestChainIntegrity:
    """Tests for chain integrity verification."""

    def test_empty_chain_verifies(self, chain):
        """An empty chain verifies successfully."""
        valid, errors = chain.verify()
        assert valid is True
        assert errors == []

    def test_single_entry_verifies(self, chain, generator):
        """A chain with one entry verifies successfully."""
        signed = _make_signed_receipt(generator)
        chain.append(signed)
        valid, errors = chain.verify()
        assert valid is True
        assert errors == []

    def test_multiple_entries_verify(self, chain, generator):
        """A chain with multiple entries verifies successfully."""
        for _ in range(10):
            signed = _make_signed_receipt(generator)
            chain.append(signed)
        valid, errors = chain.verify()
        assert valid is True
        assert errors == []


# ---------------------------------------------------------------------------
# Chain linking
# ---------------------------------------------------------------------------

class TestChainLinking:
    """Tests for cryptographic linking between entries."""

    def test_first_entry_links_to_genesis(self, chain, generator):
        """The first entry links to the genesis hash (64 zeros)."""
        signed = _make_signed_receipt(generator)
        entry = chain.append(signed)
        assert entry.previous_block_hash == "0" * 64

    def test_subsequent_entries_link_to_previous(self, chain, generator):
        """Each entry links to the previous entry's block hash."""
        signed1 = _make_signed_receipt(generator)
        entry1 = chain.append(signed1)
        signed2 = _make_signed_receipt(generator)
        entry2 = chain.append(signed2)
        assert entry2.previous_block_hash == entry1.block_hash

    def test_block_hash_is_sha256(self, chain, generator):
        """Each block hash is a 64-character hex string."""
        signed = _make_signed_receipt(generator)
        entry = chain.append(signed)
        assert len(entry.block_hash) == 64
        assert all(c in "0123456789abcdef" for c in entry.block_hash)


# ---------------------------------------------------------------------------
# Range queries
# ---------------------------------------------------------------------------

class TestGetRange:
    """Tests for range queries."""

    def test_get_range(self, chain, generator):
        """get_range returns entries in the specified range."""
        for _ in range(10):
            signed = _make_signed_receipt(generator)
            chain.append(signed)
        subset = chain.get_range(2, 5)
        assert len(subset) == 3
        assert subset[0].sequence_number == 2
        assert subset[1].sequence_number == 3
        assert subset[2].sequence_number == 4

    def test_get_range_empty(self, chain, generator):
        """get_range with no matching entries returns empty list."""
        for _ in range(3):
            signed = _make_signed_receipt(generator)
            chain.append(signed)
        subset = chain.get_range(10, 20)
        assert subset == []

    def test_get_entry_by_index(self, chain, generator):
        """get_entry returns the correct entry by index."""
        for _ in range(5):
            signed = _make_signed_receipt(generator)
            chain.append(signed)
        entry = chain.get_entry(2)
        assert entry is not None
        assert entry.sequence_number == 2

    def test_get_entry_out_of_range(self, chain):
        """get_entry returns None for out-of-range indices."""
        assert chain.get_entry(0) is None
        assert chain.get_entry(-1) is None


# ---------------------------------------------------------------------------
# Export / import
# ---------------------------------------------------------------------------

class TestExportImport:
    """Tests for JSON export."""

    def test_export_json(self, chain, generator):
        """export_json produces valid JSON."""
        for _ in range(3):
            signed = _make_signed_receipt(generator)
            chain.append(signed)
        json_str = chain.export_json()
        data = json.loads(json_str)
        assert data["chain_length"] == 3
        assert len(data["entries"]) == 3
        assert data["last_hash"] == chain.last_hash()

    def test_export_json_contains_entry_fields(self, chain, generator):
        """Each exported entry contains the expected fields."""
        signed = _make_signed_receipt(generator)
        chain.append(signed)
        json_str = chain.export_json()
        data = json.loads(json_str)
        entry = data["entries"][0]
        assert "sequence_number" in entry
        assert "block_hash" in entry
        assert "previous_block_hash" in entry
        assert "timestamp_ns" in entry
        assert "signed_receipt" in entry

    def test_get_all_entries(self, chain, generator):
        """get_all_entries returns all entries."""
        for _ in range(5):
            signed = _make_signed_receipt(generator)
            chain.append(signed)
        entries = chain.get_all_entries()
        assert len(entries) == 5
        assert entries[0].sequence_number == 0
        assert entries[4].sequence_number == 4

    def test_find_by_receipt_hash(self, chain, generator):
        """find_by_receipt_hash locates the correct entry."""
        signed = _make_signed_receipt(generator)
        chain.append(signed)
        entry = chain.find_by_receipt_hash(signed.receipt_hash)
        assert entry is not None
        assert entry.sequence_number == 0

    def test_find_by_receipt_hash_not_found(self, chain):
        """find_by_receipt_hash returns None for unknown hash."""
        assert chain.find_by_receipt_hash("nonexistent_hash") is None


# ---------------------------------------------------------------------------
# CSV export
# ---------------------------------------------------------------------------

class TestExportCSV:
    """Tests for CSV export."""

    def test_export_csv(self, chain, generator):
        """export_csv produces a valid CSV string."""
        for _ in range(3):
            signed = _make_signed_receipt(generator)
            chain.append(signed)
        csv_str = chain.export_csv()
        lines = csv_str.strip().split("\n")
        assert len(lines) == 4  # header + 3 entries
        assert "sequence_number" in lines[0]

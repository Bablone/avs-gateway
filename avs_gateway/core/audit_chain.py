"""
audit_chain.py -- Immutable append-only audit chain.

Every receipt is linked to its predecessor via SHA-256 hash.
Tamper detection through chain integrity verification.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from datetime import datetime
import hashlib
import json
import csv
import io
import logging
import threading
import time as time_mod

logger = logging.getLogger("avs_gateway.audit")


@dataclass(frozen=True)
class ChainEntry:
    """A single entry in the audit chain.

    Links each signed receipt to its predecessor via SHA-256 hash,
    forming an immutable append-only chain.
    """

    sequence_number: int
    signed_receipt: Dict[str, Any]
    block_hash: str
    previous_block_hash: str
    timestamp_ns: int
    metadata: Dict[str, Any] = field(default_factory=dict)


class AuditChain:
    """Immutable append-only audit chain.

    Each entry contains a signed receipt and is cryptographically
    linked to the previous entry via SHA-256 hash. Thread-safe via
    :class:`threading.RLock`.
    """

    def __init__(self) -> None:
        self._entries: List[ChainEntry] = []
        self._last_hash: str = "0" * 64
        self._lock = threading.RLock()
        logger.info("AuditChain initialized (genesis hash: %s)", self._last_hash)

    def append(self, signed_receipt: Any) -> ChainEntry:
        """Append a *signed_receipt* to the chain.

        Computes the block hash as
        ``SHA-256(previous_block_hash + receipt_hash + timestamp)``,
        updates the chain head, and returns the new entry.
        """
        with self._lock:
            seq = len(self._entries)
            timestamp_ns = time_mod.time_ns()

            receipt_hash = signed_receipt.receipt_hash
            prev_hash = self._last_hash

            payload = f"{prev_hash}{receipt_hash}{timestamp_ns}"
            block_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()

            entry = ChainEntry(
                sequence_number=seq,
                signed_receipt=signed_receipt.to_dict(),
                block_hash=block_hash,
                previous_block_hash=prev_hash,
                timestamp_ns=timestamp_ns,
                metadata={},
            )

            self._entries.append(entry)
            self._last_hash = block_hash

            logger.debug(
                "Appended entry %d (block_hash=%s...)", seq, block_hash[:16]
            )
            return entry

    def length(self) -> int:
        """Return the number of entries in the chain."""
        with self._lock:
            return len(self._entries)

    def last_hash(self) -> str:
        """Return the hash of the most recent block."""
        with self._lock:
            return self._last_hash

    def get_entry(self, index: int) -> Optional[ChainEntry]:
        """Get a chain entry by its *index* (sequence number).

        Returns ``None`` if the index is out of range.
        """
        with self._lock:
            if 0 <= index < len(self._entries):
                return self._entries[index]
            return None

    def get_all_entries(self) -> List[ChainEntry]:
        """Return a shallow copy of all chain entries."""
        with self._lock:
            return list(self._entries)

    def verify(self) -> tuple[bool, List[str]]:
        """Verify the integrity of the entire chain.

        Checks that each entry's *previous_block_hash* matches the
        *block_hash* of the preceding entry, and that each block
        hash is correctly recomputed.

        Returns ``(is_valid, list_of_error_messages)``.
        """
        with self._lock:
            errors: List[str] = []

            if not self._entries:
                return True, errors

            expected_hash = "0" * 64
            for idx, entry in enumerate(self._entries):
                if entry.previous_block_hash != expected_hash:
                    errors.append(
                        f"Entry {idx}: previous_block_hash mismatch "
                        f"(expected {expected_hash[:16]}..., got "
                        f"{entry.previous_block_hash[:16]}...)"
                    )

                receipt_hash = entry.signed_receipt.get("receipt_hash", "")
                payload = (
                    f"{entry.previous_block_hash}{receipt_hash}"
                    f"{entry.timestamp_ns}"
                )
                recomputed = hashlib.sha256(payload.encode("utf-8")).hexdigest()
                if recomputed != entry.block_hash:
                    errors.append(
                        f"Entry {idx}: block_hash mismatch "
                        f"(expected {recomputed[:16]}..., got "
                        f"{entry.block_hash[:16]}...)"
                    )

                expected_hash = entry.block_hash

            return len(errors) == 0, errors

    def export_json(self) -> str:
        """Export the entire chain as a JSON string."""
        with self._lock:
            data = {
                "chain_length": len(self._entries),
                "last_hash": self._last_hash,
                "exported_at_ns": time_mod.time_ns(),
                "entries": [
                    {
                        "sequence_number": e.sequence_number,
                        "signed_receipt": e.signed_receipt,
                        "block_hash": e.block_hash,
                        "previous_block_hash": e.previous_block_hash,
                        "timestamp_ns": e.timestamp_ns,
                        "metadata": e.metadata,
                    }
                    for e in self._entries
                ],
            }
            return json.dumps(data, sort_keys=True, indent=2)

    def export_csv(self) -> str:
        """Export the chain as a CSV string."""
        with self._lock:
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(
                [
                    "sequence_number",
                    "receipt_id",
                    "receipt_hash",
                    "block_hash",
                    "previous_block_hash",
                    "timestamp_ns",
                    "agent_id",
                    "decision_type",
                    "risk_score",
                ]
            )

            for entry in self._entries:
                receipt = entry.signed_receipt.get("receipt", {})
                writer.writerow(
                    [
                        entry.sequence_number,
                        receipt.get("receipt_id", ""),
                        entry.signed_receipt.get("receipt_hash", ""),
                        entry.block_hash,
                        entry.previous_block_hash,
                        entry.timestamp_ns,
                        receipt.get("agent_id", ""),
                        receipt.get("decision_type", ""),
                        receipt.get("risk_score", ""),
                    ]
                )

            return output.getvalue()

    def find_by_receipt_hash(self, receipt_hash: str) -> Optional[ChainEntry]:
        """Find the chain entry whose signed receipt has the given *receipt_hash*."""
        with self._lock:
            for entry in self._entries:
                if entry.signed_receipt.get("receipt_hash") == receipt_hash:
                    return entry
            return None

    def get_range(self, start: int, end: int) -> List[ChainEntry]:
        """Return entries whose indices fall in ``[start, end)``."""
        with self._lock:
            return list(self._entries[start:end])


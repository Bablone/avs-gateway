"""
ASR-1 Receipt Module — Proof-of-Action Foundation.

ASR-1 is an experimental draft receipt format for AI agent actions.
It is NOT an official external standard. It is an AVS-native receipt profile.

Every agent action decision is captured as a structured, portable,
tamper-evident evidence object.

Agent Identity + Tool Manifest + Action Receipt = Proof of Action.
"""

from avs_gateway.receipts.asr1 import (
    ASR1Receipt,
    ASR1ReceiptGenerator,
    canonical_json,
    hash_payload,
    verify_receipt,
    verify_chain,
)

__all__ = [
    "ASR1Receipt",
    "ASR1ReceiptGenerator",
    "canonical_json",
    "hash_payload",
    "verify_receipt",
    "verify_chain",
]

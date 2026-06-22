"""
receipt_generator.py -- Cryptographic receipt generation.

Every action/decision pair produces a signed receipt.
Ed25519 signatures, SHA-256 hashing, hash-chain linking.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
import hashlib
import json
import time
import base64
import logging
import uuid

logger = logging.getLogger("avs_gateway.receipt")

# Ed25519 imports
try:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import (
        Ed25519PrivateKey,
        Ed25519PublicKey,
    )
    from cryptography.hazmat.primitives import serialization
    from cryptography.exceptions import InvalidSignature

    HAS_CRYPTO = True
except ImportError:
    HAS_CRYPTO = False
    logger.warning("cryptography library not available; using mock signing")


@dataclass(frozen=True)
class Receipt:
    """An unsigned receipt capturing an action/decision pair."""

    receipt_id: str
    action_hash: str
    decision_type: str
    decision_reason: str
    matched_policy: Optional[str]
    risk_score: int
    risk_classification: str
    trust_score: int
    agent_id: str
    policy_hash: str
    timestamp_ns: int
    previous_hash: Optional[str]
    gateway_version: str = "0.9.0"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def receipt_hash(self) -> str:
        """Compute SHA-256 hash of canonical JSON representation."""
        canonical = json.dumps(
            self.to_dict(),
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        """Convert receipt to a dictionary."""
        return {
            "receipt_id": self.receipt_id,
            "action_hash": self.action_hash,
            "decision_type": self.decision_type,
            "decision_reason": self.decision_reason,
            "matched_policy": self.matched_policy,
            "risk_score": self.risk_score,
            "risk_classification": self.risk_classification,
            "trust_score": self.trust_score,
            "agent_id": self.agent_id,
            "policy_hash": self.policy_hash,
            "timestamp_ns": self.timestamp_ns,
            "previous_hash": self.previous_hash,
            "gateway_version": self.gateway_version,
            "metadata": self.metadata,
        }

    def to_json(self) -> str:
        """Serialize receipt to JSON string."""
        return json.dumps(self.to_dict(), sort_keys=True, indent=2)


@dataclass(frozen=True)
class SignedReceipt:
    """A receipt bundled with its Ed25519 (or mock) signature."""

    receipt: Receipt
    signature: str  # base64-encoded
    public_key: str  # base64-encoded
    receipt_hash: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert signed receipt to a dictionary."""
        return {
            "receipt": self.receipt.to_dict(),
            "signature": self.signature,
            "public_key": self.public_key,
            "receipt_hash": self.receipt_hash,
        }

    def to_json(self, indent: Optional[int] = None) -> str:
        """Serialize signed receipt to JSON string."""
        return json.dumps(self.to_dict(), sort_keys=True, indent=indent)


class ReceiptGenerator:
    """Generates cryptographically signed receipts for action/decision pairs.

    Uses Ed25519 signatures when the *cryptography* library is available,
    otherwise falls back to deterministic mock signing for testing.
    """

    def __init__(
        self,
        private_key_path: Optional[str] = None,
        private_key: Optional[Any] = None,
        policy_hash: str = "default_policy_hash",
    ) -> None:
        self._policy_hash = policy_hash
        self._private_key: Optional[Any] = private_key
        self._public_key: Optional[Any] = None

        if private_key_path:
            self._private_key = self._load_key(private_key_path)
        elif private_key:
            self._private_key = private_key
        else:
            self._private_key = self._generate_key()

        if HAS_CRYPTO and isinstance(self._private_key, Ed25519PrivateKey):
            self._public_key = self._private_key.public_key()
        else:
            self._public_key = None

        logger.info(
            "ReceiptGenerator initialized (crypto=%s, policy=%s)",
            HAS_CRYPTO,
            policy_hash,
        )

    def _generate_key(self) -> Any:
        """Generate a new Ed25519 key pair or a mock key."""
        if HAS_CRYPTO:
            key = Ed25519PrivateKey.generate()
            logger.debug("Generated new Ed25519 key pair")
            return key
        else:
            mock_key = hashlib.sha256(b"mock_seed_" + str(uuid.uuid4()).encode()).digest()
            logger.debug("Generated mock signing key")
            return mock_key

    def _load_key(self, path: str) -> Any:
        """Load an Ed25519 private key from a PEM file."""
        if HAS_CRYPTO:
            with open(path, "rb") as f:
                key = serialization.load_pem_private_key(f.read(), password=None)
                if not isinstance(key, Ed25519PrivateKey):
                    raise ValueError("Key is not an Ed25519 private key")
                logger.debug("Loaded Ed25519 key from %s", path)
                return key
        else:
            with open(path, "rb") as f:
                data = f.read()
                logger.debug("Loaded mock key from %s", path)
                return hashlib.sha256(data).digest()

    def export_public_key(self, path: str) -> None:
        """Export the public key to a PEM file."""
        if HAS_CRYPTO and self._public_key:
            pem = self._public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            )
            with open(path, "wb") as f:
                f.write(pem)
            logger.info("Exported public key to %s", path)
        else:
            mock_pem = b"-----BEGIN MOCK PUBLIC KEY-----\n"
            mock_pem += base64.b64encode(b"mock_public_" + self._private_key)
            mock_pem += b"\n-----END MOCK PUBLIC KEY-----\n"
            with open(path, "wb") as f:
                f.write(mock_pem)
            logger.info("Exported mock public key to %s", path)

    def generate(
        self,
        action_request: Any,
        decision: Any,
        previous_hash: Optional[str] = None,
    ) -> Receipt:
        """Create a Receipt from an action_request and a decision.

        *action_request* must provide ``action_id``, ``action_hash()``,
        and ``agent_id`` attributes.
        *decision* must provide ``decision_type`` (with ``.value``),
        ``reason``, ``matched_policy``, ``risk_score``, ``trust_score``,
        and ``risk_score`` attributes.
        """
        risk_score = decision.risk_score
        if risk_score <= 25:
            risk_classification = "low"
        elif risk_score <= 50:
            risk_classification = "medium"
        elif risk_score <= 75:
            risk_classification = "high"
        else:
            risk_classification = "critical"

        receipt = Receipt(
            receipt_id=action_request.action_id,
            action_hash=action_request.action_hash(),
            decision_type=decision.decision_type.value,
            decision_reason=decision.reason,
            matched_policy=decision.matched_policy,
            risk_score=risk_score,
            risk_classification=risk_classification,
            trust_score=decision.trust_score,
            agent_id=action_request.agent_id,
            policy_hash=self._policy_hash,
            timestamp_ns=time.time_ns(),
            previous_hash=previous_hash,
            gateway_version="0.9.0",
            metadata={},
        )
        logger.debug(
            "Generated receipt %s for action %s", receipt.receipt_id, action_request.action_id
        )
        return receipt

    def sign(self, receipt: Receipt) -> SignedReceipt:
        """Sign *receipt* and return a :class:`SignedReceipt`."""
        rhash = receipt.receipt_hash()

        if HAS_CRYPTO and isinstance(self._private_key, Ed25519PrivateKey):
            signature_bytes = self._private_key.sign(rhash.encode("utf-8"))
            signature_b64 = base64.b64encode(signature_bytes).decode("utf-8")
            pub_bytes = self._public_key.public_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PublicFormat.Raw,
            )
            pub_b64 = base64.b64encode(pub_bytes).decode("utf-8")
        else:
            mock_sig = hashlib.sha256(b"mock:" + rhash.encode("utf-8") + self._private_key).digest()
            signature_b64 = base64.b64encode(mock_sig).decode("utf-8")
            pub_b64 = base64.b64encode(b"mock_public_" + self._private_key).decode("utf-8")

        signed = SignedReceipt(
            receipt=receipt,
            signature=signature_b64,
            public_key=pub_b64,
            receipt_hash=rhash,
        )
        logger.debug("Signed receipt %s", receipt.receipt_id)
        return signed

    def verify(self, signed_receipt: SignedReceipt) -> bool:
        """Verify the signature on a *signed_receipt*."""
        rhash = signed_receipt.receipt_hash
        sig_b64 = signed_receipt.signature
        pub_b64 = signed_receipt.public_key

        if HAS_CRYPTO:
            try:
                pub_bytes = base64.b64decode(pub_b64.encode("utf-8"))
                public_key = Ed25519PublicKey.from_public_bytes(pub_bytes)
                sig_bytes = base64.b64decode(sig_b64.encode("utf-8"))
                public_key.verify(sig_bytes, rhash.encode("utf-8"))
                logger.debug("Verified receipt %s (valid)", signed_receipt.receipt.receipt_id)
                return True
            except (InvalidSignature, Exception) as exc:
                logger.debug(
                    "Signature verification failed for receipt %s: %s",
                    signed_receipt.receipt.receipt_id,
                    exc,
                )
                return False
        else:
            expected = hashlib.sha256(
                b"mock:" + rhash.encode("utf-8") + b"mock_public_" + self._private_key
            ).digest()
            try:
                actual = base64.b64decode(sig_b64.encode("utf-8"))
                valid = actual == expected
                logger.debug(
                    "Mock verification for receipt %s: %s",
                    signed_receipt.receipt.receipt_id,
                    valid,
                )
                return valid
            except Exception as exc:
                logger.debug("Mock verification failed: %s", exc)
                return False

    def serialize(self, signed_receipt: SignedReceipt) -> str:
        """JSON-serialize a *signed_receipt*."""
        return signed_receipt.to_json()

    @classmethod
    def deserialize(cls, json_str: str) -> "SignedReceipt":
        """Reconstruct a :class:`SignedReceipt` from a JSON string."""
        data = json.loads(json_str)
        receipt_data = data["receipt"]
        receipt = Receipt(
            receipt_id=receipt_data["receipt_id"],
            action_hash=receipt_data["action_hash"],
            decision_type=receipt_data["decision_type"],
            decision_reason=receipt_data["decision_reason"],
            matched_policy=receipt_data.get("matched_policy"),
            risk_score=receipt_data["risk_score"],
            risk_classification=receipt_data["risk_classification"],
            trust_score=receipt_data["trust_score"],
            agent_id=receipt_data["agent_id"],
            policy_hash=receipt_data["policy_hash"],
            timestamp_ns=receipt_data["timestamp_ns"],
            previous_hash=receipt_data.get("previous_hash"),
            gateway_version=receipt_data.get("gateway_version", "0.9.0"),
            metadata=receipt_data.get("metadata", {}),
        )
        return SignedReceipt(
            receipt=receipt,
            signature=data["signature"],
            public_key=data["public_key"],
            receipt_hash=data["receipt_hash"],
        )


class MerkleTree:
    """SHA-256 Merkle tree built from a list of leaf hashes.

    Provides the Merkle root and per-leaf inclusion proofs.
    """

    def __init__(self, leaves: List[str]) -> None:
        if not leaves:
            raise ValueError("MerkleTree requires at least one leaf")
        self.leaves: List[str] = leaves
        self._levels: List[List[str]] = []
        self._build_tree()

    def _build_tree(self) -> None:
        """Build the tree bottom-up from the leaves."""
        current_level = [hashlib.sha256(leaf.encode("utf-8")).hexdigest() for leaf in self.leaves]
        self._levels = [current_level]

        while len(current_level) > 1:
            next_level: List[str] = []
            for i in range(0, len(current_level), 2):
                left = current_level[i]
                right = current_level[i + 1] if i + 1 < len(current_level) else left
                combined = left + right
                parent = hashlib.sha256(combined.encode("utf-8")).hexdigest()
                next_level.append(parent)
            self._levels.append(next_level)
            current_level = next_level

    def root(self) -> str:
        """Return the Merkle root hash."""
        return self._levels[-1][0]

    def proof(self, index: int) -> List[str]:
        """Generate an inclusion proof for the leaf at *index*.

        Returns a list of sibling hashes from leaf level up to the root.
        """
        if index < 0 or index >= len(self.leaves):
            raise IndexError(f"Leaf index {index} out of range")

        proof: List[str] = []
        current_index = index

        for level in self._levels[:-1]:
            sibling_index = (
                current_index + 1 if current_index % 2 == 0 else current_index - 1
            )
            if sibling_index < len(level):
                proof.append(level[sibling_index])
            else:
                proof.append(level[current_index])
            current_index //= 2

        return proof

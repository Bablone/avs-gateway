"""
gateway_core.py -- Core Gateway orchestration module.

Every agent action passes through Gateway.intercept() -> evaluate() -> decide() -> record().
Fail-closed: any unhandled exception results in a deny decision.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Tuple
from enum import Enum
import time
import traceback
import logging
import threading

from avs_gateway.models.action_request import ActionRequest, ActionType
from avs_gateway.core.policy_engine import PolicyEngine, DecisionType as PolicyDecisionType, PolicyResult
from avs_gateway.core.risk_engine import RiskEngine, RiskScore
from avs_gateway.core.trust_memory import TrustMemory, TrustScore
from avs_gateway.core.receipt_generator import ReceiptGenerator, Receipt, SignedReceipt
from avs_gateway.core.audit_chain import AuditChain, ChainEntry

logger = logging.getLogger("avs_gateway.core")


class DecisionType(Enum):
    """Gateway decision types resulting from the intercept-decide flow.

    Attributes:
        ALLOW: Action is permitted to proceed.
        DENY: Action is blocked.
        REQUIRE_APPROVAL: Action requires human approval before proceeding.
        QUARANTINE: Action is isolated for further investigation.
    """

    ALLOW = "allow"
    DENY = "deny"
    REQUIRE_APPROVAL = "require_approval"
    QUARANTINE = "quarantine"


@dataclass(frozen=True)
class Decision:
    """Immutable decision record produced by the Gateway.

    Attributes:
        decision_type: The type of decision rendered.
        reason: Human-readable explanation for the decision.
        matched_policy: Name of the policy that matched, if any.
        risk_score: Numeric risk score (0-100) at decision time.
        trust_score: Numeric trust score (0-100) at decision time.
        processing_time_ms: Wall-clock time spent processing this decision.
        timestamp_ns: Nanosecond timestamp when the decision was made.
    """

    decision_type: DecisionType
    reason: str
    matched_policy: Optional[str] = None
    risk_score: int = 0
    trust_score: int = 50
    processing_time_ms: float = 0.0
    timestamp_ns: int = field(default_factory=lambda: time.time_ns())

    def is_blocking(self) -> bool:
        """Return True if this decision blocks the action.

        Blocking decisions are DENY and QUARANTINE, which prevent
        the action from executing without further intervention.
        """
        return self.decision_type in (DecisionType.DENY, DecisionType.QUARANTINE)

    def requires_human(self) -> bool:
        """Return True if this decision requires human intervention.

        REQUIRE_APPROVAL decisions need a human to explicitly approve
        or deny before the action can proceed.
        """
        return self.decision_type == DecisionType.REQUIRE_APPROVAL


class Gateway:
    """Central gateway orchestrator for proof-gated agent execution.

    The Gateway intercepts every agent action, evaluates it through
    multiple engines (policy, risk, trust), renders a decision, and
    produces an auditable signed receipt.

    Fail-closed semantics: any unhandled exception during processing
    results in a DENY decision to ensure the system never
    inadvertently allows a dangerous action.

    Thread-safe: all mutable state is protected by an RLock.
    """

    def __init__(
        self,
        policy_engine: PolicyEngine,
        risk_engine: RiskEngine,
        trust_memory: TrustMemory,
        receipt_generator: ReceiptGenerator,
        audit_chain: AuditChain,
        config: Optional[Dict[str, Any]] = None,
        approval_service: Optional[Any] = None,
    ) -> None:
        """Initialize the Gateway with all required subsystems.

        Args:
            policy_engine: Engine for evaluating policies against requests.
            risk_engine: Engine for scoring action risk levels.
            trust_memory: Memory store for agent trust scores.
            receipt_generator: Generator for signing receipts.
            audit_chain: Append-only audit chain for recording decisions.
            config: Optional configuration dictionary.
            approval_service: Optional ApprovalService for v0.2 human approval loop.
        """
        self.policy_engine: PolicyEngine = policy_engine
        self.risk_engine: RiskEngine = risk_engine
        self.trust_memory: TrustMemory = trust_memory
        self.receipt_generator: ReceiptGenerator = receipt_generator
        self.audit_chain: AuditChain = audit_chain
        self.config: Dict[str, Any] = config or {}
        # v0.2: optional approval service for REQUIRE_APPROVAL lifecycle
        self.approval_service: Optional[Any] = approval_service

        # Thread-safe counters
        self._lock: threading.RLock = threading.RLock()
        self._intercept_count: int = 0
        self._decision_counts: Dict[DecisionType, int] = {
            DecisionType.ALLOW: 0,
            DecisionType.DENY: 0,
            DecisionType.REQUIRE_APPROVAL: 0,
            DecisionType.QUARANTINE: 0,
        }

        # v0.1 hardening: rejection log for invalid requests
        # These are NOT in the audit chain (can't produce signed receipts
        # for invalid actions) but are captured for security monitoring
        self._rejection_log: List[Dict[str, Any]] = []

        logger.info("Gateway initialized with config keys: %s", list(self.config.keys()))

    def intercept(self, action_request: ActionRequest) -> Decision:
        """Main entry point for the Gateway.

        Evaluates an action request through the full pipeline:
        validate -> policy -> risk -> trust -> decide.

        Fail-closed: any unhandled exception results in a DENY decision.

        Args:
            action_request: The action request from an agent.

        Returns:
            A Decision object containing the rendered decision.
        """
        start_ns: int = time.time_ns()

        with self._lock:
            self._intercept_count += 1

        try:
            # Step 1: Validate the request
            if not action_request.validate():
                decision = Decision(
                    decision_type=DecisionType.DENY,
                    reason="Action request validation failed",
                    matched_policy=None,
                    risk_score=100,
                    trust_score=0,
                    processing_time_ms=(time.time_ns() - start_ns) / 1_000_000.0,
                )
                with self._lock:
                    self._decision_counts[DecisionType.DENY] += 1
                # v0.1 hardening: log validation failures separately
                # Audit chain only contains signed receipts for valid actions;
                # rejection_log captures invalid attempts for security monitoring
                with self._lock:
                    self._rejection_log.append({
                        "timestamp_ns": time.time_ns(),
                        "action_id": action_request.action_id,
                        "agent_id": getattr(action_request, 'agent_id', '<missing>'),
                        "reason": "validation_failed",
                        "decision": DecisionType.DENY.value,
                        "processing_time_ms": (time.time_ns() - start_ns) / 1_000_000.0,
                    })
                logger.warning("Request %s denied: validation failed (rejection #%d)",
                               action_request.action_id, len(self._rejection_log))
                return decision

            # Step 2: Evaluate policy
            policy_result: PolicyResult = self.policy_engine.evaluate(action_request)

            # Step 3: Score risk
            risk_score: RiskScore = self.risk_engine.score(action_request)

            # Step 4: Get trust score
            trust_score: TrustScore = self.trust_memory.get_score(action_request.agent_id)

            # Step 5: Render decision
            decision: Decision = self._decide(
                action_request, policy_result, risk_score, trust_score, start_ns
            )

            # Step 6: Update counters
            with self._lock:
                self._decision_counts[decision.decision_type] += 1

            # v0.2: persist REQUIRE_APPROVAL to approval queue
            if (
                decision.decision_type == DecisionType.REQUIRE_APPROVAL
                and self.approval_service is not None
            ):
                try:
                    approval_id = self.approval_service.create_approval_request(
                        action_request, decision
                    )
                    logger.info(
                        "Approval request %s created for action %s",
                        approval_id, action_request.action_id,
                    )
                except Exception as exc:
                    logger.warning("Failed to create approval request: %s", exc)

            logger.info(
                "Request %s -> %s (risk=%d, trust=%d, reason=%s)",
                action_request.action_id,
                decision.decision_type.value,
                decision.risk_score,
                decision.trust_score,
                decision.reason,
            )

            return decision

        except Exception as exc:
            # FAIL CLOSED: any unhandled exception -> DENY
            error_msg = f"Unhandled exception in intercept: {type(exc).__name__}: {str(exc)}"
            logger.error("%s\n%s", error_msg, traceback.format_exc())

            decision = Decision(
                decision_type=DecisionType.DENY,
                reason=error_msg,
                matched_policy=None,
                risk_score=100,
                trust_score=0,
                processing_time_ms=(time.time_ns() - start_ns) / 1_000_000.0,
            )

            with self._lock:
                self._decision_counts[DecisionType.DENY] += 1

            return decision

    def _decide(
        self,
        action_request: ActionRequest,
        policy_result: PolicyResult,
        risk_score: RiskScore,
        trust_score: TrustScore,
        start_ns: int,
    ) -> Decision:
        """Render a decision based on policy, risk, and trust inputs.

        Decision logic (in order of precedence):
        1. If policy_result.decision is DENY -> DENY
        2. If risk_score.classification == "critical" -> DENY
        3. If policy_result.decision is REQUIRE_APPROVAL -> REQUIRE_APPROVAL
        4. If risk_score.classification == "high" -> QUARANTINE
        5. If trust_score.tier == "untrusted" -> REQUIRE_APPROVAL
        6. If risk_score.classification == "medium" -> REQUIRE_APPROVAL
        7. If policy_result.decision is ALLOW OR risk_score.classification == "low" -> ALLOW
        8. Default -> REQUIRE_APPROVAL

        Args:
            action_request: The original action request.
            policy_result: Result from policy engine evaluation.
            risk_score: Risk score from the risk engine.
            trust_score: Trust score from trust memory.
            start_ns: Nanosecond timestamp when processing started.

        Returns:
            A fully populated Decision object.
        """
        processing_time_ms: float = (time.time_ns() - start_ns) / 1_000_000.0

        # Decision precedence (highest first):
        # 1. Critical risk -> DENY (safety override)
        if risk_score.classification == "critical":
            return Decision(
                decision_type=DecisionType.DENY,
                reason=f"Critical risk detected (score={risk_score.value})",
                matched_policy=policy_result.matched_rule,
                risk_score=risk_score.value,
                trust_score=trust_score.value,
                processing_time_ms=processing_time_ms,
            )

        # 2. Policy DENY -> DENY (explicit deny)
        if policy_result.decision == PolicyDecisionType.DENY:
            return Decision(
                decision_type=DecisionType.DENY,
                reason=f"Policy denied: {policy_result.matched_rule or 'unknown policy'}",
                matched_policy=policy_result.matched_rule,
                risk_score=risk_score.value,
                trust_score=trust_score.value,
                processing_time_ms=processing_time_ms,
            )

        # 3. Policy REQUIRE_APPROVAL -> REQUIRE_APPROVAL (explicit)
        if policy_result.decision == PolicyDecisionType.REQUIRE_APPROVAL:
            return Decision(
                decision_type=DecisionType.REQUIRE_APPROVAL,
                reason=f"Policy requires approval: {policy_result.matched_rule or 'unknown policy'}",
                matched_policy=policy_result.matched_rule,
                risk_score=risk_score.value,
                trust_score=trust_score.value,
                processing_time_ms=processing_time_ms,
            )

        # 4. Policy ALLOW -> ALLOW (explicit allow overrides medium/high risk)
        if policy_result.decision == PolicyDecisionType.ALLOW:
            return Decision(
                decision_type=DecisionType.ALLOW,
                reason=f"Policy allowed: {policy_result.matched_rule or 'unknown policy'}",
                matched_policy=policy_result.matched_rule,
                risk_score=risk_score.value,
                trust_score=trust_score.value,
                processing_time_ms=processing_time_ms,
            )

        # 5. High risk -> QUARANTINE
        if risk_score.classification == "high":
            return Decision(
                decision_type=DecisionType.QUARANTINE,
                reason=f"High risk detected (score={risk_score.value}), quarantining",
                matched_policy=policy_result.matched_rule,
                risk_score=risk_score.value,
                trust_score=trust_score.value,
                processing_time_ms=processing_time_ms,
            )

        # 6. Untrusted agent -> REQUIRE_APPROVAL
        if trust_score.tier == "untrusted":
            return Decision(
                decision_type=DecisionType.REQUIRE_APPROVAL,
                reason=f"Agent untrusted (trust_score={trust_score.value})",
                matched_policy=policy_result.matched_rule,
                risk_score=risk_score.value,
                trust_score=trust_score.value,
                processing_time_ms=processing_time_ms,
            )

        # 7. Medium risk -> REQUIRE_APPROVAL
        if risk_score.classification == "medium":
            return Decision(
                decision_type=DecisionType.REQUIRE_APPROVAL,
                reason=f"Medium risk requires approval (score={risk_score.value})",
                matched_policy=policy_result.matched_rule,
                risk_score=risk_score.value,
                trust_score=trust_score.value,
                processing_time_ms=processing_time_ms,
            )

        # 8. Low risk -> ALLOW
        if risk_score.classification == "low":
            return Decision(
                decision_type=DecisionType.ALLOW,
                reason=f"Low risk (score={risk_score.value}), allowing",
                matched_policy=policy_result.matched_rule,
                risk_score=risk_score.value,
                trust_score=trust_score.value,
                processing_time_ms=processing_time_ms,
            )

        # 9. Default fallback -> REQUIRE_APPROVAL
        return Decision(
            decision_type=DecisionType.REQUIRE_APPROVAL,
            reason="Default: approval required",
            matched_policy=policy_result.matched_rule,
            risk_score=risk_score.value,
            trust_score=trust_score.value,
            processing_time_ms=processing_time_ms,
        )

    def record(self, action_request: ActionRequest, decision: Decision) -> SignedReceipt:
        """Record a decision by generating a signed receipt and appending to the audit chain.

        Also updates trust memory based on the decision outcome.

        Args:
            action_request: The original action request.
            decision: The rendered decision.

        Returns:
            A SignedReceipt proving the decision was recorded.
        """
        # Step 1: Generate receipt
        receipt: Receipt = self.receipt_generator.generate(action_request, decision)

        # Step 2: Sign the receipt
        signed_receipt: SignedReceipt = self.receipt_generator.sign(receipt)

        # Step 3: Append to audit chain
        self.audit_chain.append(signed_receipt)

        # Step 4: Update trust memory based on decision
        if decision.decision_type == DecisionType.ALLOW:
            self.trust_memory.record_behavior(action_request.agent_id, "success")
        elif decision.decision_type == DecisionType.DENY:
            self.trust_memory.record_behavior(action_request.agent_id, "failure")
        elif decision.decision_type == DecisionType.QUARANTINE:
            self.trust_memory.record_behavior(action_request.agent_id, "quarantine")
        elif decision.decision_type == DecisionType.REQUIRE_APPROVAL:
            # Don't update trust yet -- wait for human decision
            logger.debug(
                "Request %s requires human approval, trust not updated yet",
                action_request.action_id,
            )

        logger.info(
            "Recorded %s decision for request %s, audit chain length: %d",
            decision.decision_type.value,
            action_request.action_id,
            self.audit_chain.length(),
        )

        return signed_receipt

    def get_rejection_log(self) -> List[Dict[str, Any]]:
        """Return the rejection log for invalid requests.

        These entries capture validation failures that are NOT in the
        audit chain (invalid requests cannot produce signed receipts).

        Returns:
            List of rejection entries, each containing:
            timestamp_ns, action_id, agent_id, reason, decision,
            processing_time_ms.
        """
        with self._lock:
            return list(self._rejection_log)

    def get_stats(self) -> Dict[str, Any]:
        """Return gateway statistics.

        Returns:
            Dictionary containing total intercepts, decision counts,
            audit chain length, and last receipt hash.
        """
        with self._lock:
            decision_counts = {
                dt.value: count for dt, count in self._decision_counts.items()
            }

        return {
            "total_intercepts": self._intercept_count,
            "valid_decisions": sum(decision_counts.values()),
            "decisions": decision_counts,
            "audit_chain_length": self.audit_chain.length(),
            "rejection_count": len(self._rejection_log),
            "last_receipt_hash": self.audit_chain.last_hash(),
        }

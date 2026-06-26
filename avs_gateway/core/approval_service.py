"""
approval_service.py -- Human approval lifecycle for AVS Gateway v0.2.

Manages the state machine:
    pending -> approved -> executed (once only)
    pending -> denied (blocked forever)
    pending -> expired (optional)

The ApprovalService is the ONLY way approved actions execute.
It enforces replay protection: execute_approved_once() sets status to
'executed' atomically; a second call returns None (blocked).
"""

import json
import logging
import threading
import time
from typing import Any, Dict, List, Optional

from avs_gateway.storage.sqlite_store import SqliteStore
from avs_gateway.tools.simulated_tools import ToolRegistry, ToolResult

logger = logging.getLogger("avs_gateway.approval")

# Trust deltas for human decisions
TRUST_DELTA_APPROVED = 3.0
TRUST_DELTA_DENIED = -7.0
TRUST_DELTA_EXPIRED = -2.0


class ApprovalService:
    """Human approval lifecycle manager.

    Usage:
        service = ApprovalService(store, trust_memory)
        approval_id = service.create_approval_request(action_request, decision)
        pending = service.list_pending()
        service.approve(approval_id, decided_by="human_001", reason="Verified")
        result = service.execute_approved_once(approval_id, tool_registry)
        # result is None if already executed, denied, or not approved
    """

    def __init__(
        self,
        store: SqliteStore,
        trust_memory: Optional[Any] = None,
        default_timeout: int = 300,  # 5 minutes default
    ) -> None:
        self.store = store
        self.trust_memory = trust_memory
        self._timeout_seconds = default_timeout
        self._shutdown_event = threading.Event()
        self._expiry_thread = threading.Thread(target=self._expiry_loop, daemon=True)
        self._expiry_thread.start()
        logger.info("ApprovalService initialized (timeout=%ds)", self._timeout_seconds)

    # ------------------------------------------------------------------
    # Create
    # ------------------------------------------------------------------

    def create_approval_request(
        self,
        action_request,
        decision,
    ) -> str:
        """Persist a REQUIRE_APPROVAL decision as a pending approval request.

        Args:
            action_request: The ActionRequest that triggered REQUIRE_APPROVAL.
            decision: The Gateway Decision (must be REQUIRE_APPROVAL).

        Returns:
            The approval_id for the newly created request.
        """
        approval_id = self.store.create_approval_request(
            action_request_dict=action_request.to_dict(),
            decision_dict={
                "risk_score": decision.risk_score,
                "trust_score": decision.trust_score,
                "reason": decision.reason,
            },
        )
        self.store.record_audit_event(
            event_type="approval_created",
            agent_id=action_request.agent_id,
            action_id=action_request.action_id,
            approval_id=approval_id,
            details={
                "tool_name": action_request.tool_name,
                "operation": action_request.operation,
                "risk_score": decision.risk_score,
                "trust_score": decision.trust_score,
                "reason": decision.reason,
            },
        )
        logger.info(
            "Approval %s created for agent=%s tool=%s.%s",
            approval_id,
            action_request.agent_id,
            action_request.tool_name,
            action_request.operation,
        )
        return approval_id

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def list_pending(self) -> List[Dict[str, Any]]:
        """Return all approval requests with status='pending'."""
        return self.store.list_pending_approvals()

    def get_approval(self, approval_id: str) -> Optional[Dict[str, Any]]:
        """Return a single approval request by ID, or None if not found."""
        return self.store.get_approval_request(approval_id)

    def get_approval_timeline(self, approval_id: str) -> List[Dict[str, Any]]:
        """Return the full audit timeline for an approval request."""
        return self.store.get_audit_events_for_approval(approval_id)

    # ------------------------------------------------------------------
    # Approve / Deny
    # ------------------------------------------------------------------

    def approve(
        self,
        approval_id: str,
        decided_by: str,
        reason: str = "",
    ) -> bool:
        """Approve a pending approval request.

        Args:
            approval_id: The approval to approve.
            decided_by: Identifier of the human who approved.
            reason: Optional human-readable reason.

        Returns:
            True if approved successfully, False if not found or not pending.
        """
        approval = self.store.get_approval_request(approval_id)
        if approval is None:
            logger.warning("approve: approval %s not found", approval_id)
            return False
        if approval["status"] != "pending":
            logger.warning(
                "approve: approval %s status=%s (expected pending)",
                approval_id, approval["status"],
            )
            return False

        updated = self.store.update_approval_status(
            approval_id, "approved", decided_by=decided_by, decision_reason=reason,
        )
        if not updated:
            return False

        self.store.record_approval_decision(
            approval_id, "approved", decided_by, reason,
        )
        self.store.record_audit_event(
            event_type="approval_approved",
            agent_id=approval.get("agent_id"),
            approval_id=approval_id,
            details={"decided_by": decided_by, "reason": reason},
        )

        # Update trust: human approval is a positive signal
        agent_id = approval.get("agent_id", "")
        if self.trust_memory and agent_id:
            self.trust_memory.record_behavior(
                agent_id, "approval_granted",
                {"approval_id": approval_id, "decided_by": decided_by},
            )
            self.store.record_trust_event(
                agent_id=agent_id,
                delta=TRUST_DELTA_APPROVED,
                reason="human_approved",
                approval_id=approval_id,
            )

        logger.info("Approval %s approved by %s", approval_id, decided_by)
        return True

    def deny(
        self,
        approval_id: str,
        decided_by: str,
        reason: str = "",
    ) -> bool:
        """Deny a pending approval request (blocks execution forever).

        Args:
            approval_id: The approval to deny.
            decided_by: Identifier of the human who denied.
            reason: Optional human-readable reason.

        Returns:
            True if denied successfully, False if not found or not pending.
        """
        approval = self.store.get_approval_request(approval_id)
        if approval is None:
            logger.warning("deny: approval %s not found", approval_id)
            return False
        if approval["status"] != "pending":
            logger.warning(
                "deny: approval %s status=%s (expected pending)",
                approval_id, approval["status"],
            )
            return False

        updated = self.store.update_approval_status(
            approval_id, "denied", decided_by=decided_by, decision_reason=reason,
        )
        if not updated:
            return False

        self.store.record_approval_decision(
            approval_id, "denied", decided_by, reason,
        )
        self.store.record_audit_event(
            event_type="approval_denied",
            agent_id=approval.get("agent_id"),
            approval_id=approval_id,
            details={"decided_by": decided_by, "reason": reason},
        )

        # Update trust: human denial is a negative signal
        agent_id = approval.get("agent_id", "")
        if self.trust_memory and agent_id:
            self.trust_memory.record_behavior(
                agent_id, "approval_denied",
                {"approval_id": approval_id, "decided_by": decided_by},
            )
            self.store.record_trust_event(
                agent_id=agent_id,
                delta=TRUST_DELTA_DENIED,
                reason="human_denied",
                approval_id=approval_id,
            )

        logger.info("Approval %s denied by %s", approval_id, decided_by)
        return True

    # ------------------------------------------------------------------
    # Execute (once only -- replay protected)
    # ------------------------------------------------------------------

    def execute_approved_once(
        self,
        approval_id: str,
        tool_registry: ToolRegistry,
    ) -> Optional[Dict[str, Any]]:
        """Execute an approved action exactly once through the tool registry.

        This is the ONLY way approved actions execute. It enforces:
        - Status must be 'approved' (not already executed, not denied, not pending)
        - After successful execution, status becomes 'executed'
        - Subsequent calls return None (replay blocked)

        Args:
            approval_id: The approval to execute.
            tool_registry: The ToolRegistry to route execution through.

        Returns:
            Tool execution result dict if executed successfully,
            None if replay blocked, not approved, or execution failed.
        """
        from avs_gateway.models.action_request import ActionRequest, ActionType

        approval = self.store.get_approval_request(approval_id)
        if approval is None:
            logger.warning("execute: approval %s not found", approval_id)
            return None

        # Replay protection: must be 'approved', not already 'executed'
        if approval["status"] != "approved":
            if approval["status"] == "executed":
                logger.warning(
                    "execute: REPLAY BLOCKED on approval %s (already executed)",
                    approval_id,
                )
                self.store.record_audit_event(
                    event_type="approval_replay_blocked",
                    agent_id=approval.get("agent_id"),
                    approval_id=approval_id,
                    details={"status": approval["status"]},
                )
            elif approval["status"] == "denied":
                logger.warning(
                    "execute: BLOCKED on approval %s (was denied)", approval_id,
                )
            elif approval["status"] == "pending":
                logger.warning(
                    "execute: BLOCKED on approval %s (not yet approved)", approval_id,
                )
            return None

        # Reconstruct ActionRequest from stored data
        try:
            action_type = ActionType(approval["action_type"])
        except (ValueError, KeyError):
            logger.error("execute: invalid action_type %r", approval.get("action_type"))
            return None

        action_request = ActionRequest(
            action_id=approval["action_id"],
            agent_id=approval["agent_id"],
            action_type=action_type,
            tool_name=approval["tool_name"],
            operation=approval["operation"],
            parameters=json.loads(approval["parameters_json"] or "{}"),
            context=json.loads(approval["context_json"] or "{}"),
            timestamp_ns=approval["created_at_ns"],
        )

        # Execute through tool registry
        try:
            tool_result = tool_registry.execute(action_request)
        except Exception as exc:
            logger.error("execute: tool_registry failed: %s", exc)
            tool_result = None

        # Record execution regardless of tool success
        result_dict = tool_result.to_dict() if tool_result and hasattr(tool_result, "to_dict") else {"error": str(tool_result) if tool_result else "no_result"}
        self.store.record_execution_result(
            approval_id,
            result_json=json.dumps(result_dict),
            receipt_hash=None,
        )
        self.store.record_audit_event(
            event_type="approval_executed",
            agent_id=approval["agent_id"],
            action_id=approval["action_id"],
            approval_id=approval_id,
            details={"tool_result": result_dict},
        )

        # Update trust: execution success/failure
        if self.trust_memory and approval["agent_id"]:
            if tool_result and getattr(tool_result, "success", False):
                self.trust_memory.record_behavior(
                    approval["agent_id"], "success",
                    {"approval_id": approval_id, "executed": True},
                )
            else:
                self.trust_memory.record_behavior(
                    approval["agent_id"], "failure",
                    {"approval_id": approval_id, "executed": True, "tool_failed": True},
                )

        logger.info("Approval %s executed (replay no longer possible)", approval_id)
        return result_dict

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        """Return aggregate approval statistics."""
        return self.store.get_approval_stats()

    # ------------------------------------------------------------------
    # Expiry daemon
    # ------------------------------------------------------------------

    def _expiry_loop(self) -> None:
        """Daemon thread: check for expired pending approvals every 30 seconds.

        Transitions approvals from PENDING to EXPIRED after timeout.
        This prevents indefinite agent blockage when humans don't review.
        """
        while not self._shutdown_event.is_set():
            self._shutdown_event.wait(30)
            if self._shutdown_event.is_set():
                break
            try:
                self._expire_stale_approvals()
            except Exception as exc:
                logger.error("Approval expiry loop error: %s", exc)

    def _expire_stale_approvals(self) -> int:
        """Expire all pending approvals past their timeout.

        Returns:
            Number of approvals expired.
        """
        cutoff_ns = int((time.time() - self._timeout_seconds) * 1_000_000_000)
        pending = self.store.list_pending_approvals()
        expired_count = 0
        for approval in pending:
            created_at_ns = approval.get("created_at_ns", 0)
            if created_at_ns and created_at_ns < cutoff_ns:
                approval_id = approval["approval_id"]
                self.store.update_approval_status(
                    approval_id, "expired",
                    decided_by="system", decision_reason=f"Timeout after {self._timeout_seconds}s"
                )
                self.store.record_audit_event(
                    event_type="approval_expired",
                    agent_id=approval.get("agent_id"),
                    approval_id=approval_id,
                    details={"timeout_seconds": self._timeout_seconds},
                )
                if self.trust_memory and approval.get("agent_id"):
                    self.trust_memory.record_behavior(
                        approval["agent_id"], "approval_expired",
                        {"approval_id": approval_id, "reason": "timeout"},
                    )
                    self.store.record_trust_event(
                        agent_id=approval["agent_id"],
                        delta=-2.0,  # TRUST_DELTA_EXPIRED
                        reason="approval_expired",
                        approval_id=approval_id,
                    )
                expired_count += 1
                logger.info("Approval %s expired (timeout %ds)",
                           approval_id, self._timeout_seconds)
        return expired_count

    def shutdown(self) -> None:
        """Gracefully shutdown the approval service.

        Signals the expiry thread to stop and waits for it to finish.
        """
        self._shutdown_event.set()
        if hasattr(self, '_expiry_thread') and self._expiry_thread.is_alive():
            self._expiry_thread.join(timeout=5)

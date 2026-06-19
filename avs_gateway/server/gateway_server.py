"""
gateway_server.py -- FastAPI server for AVS Gateway.

Provides REST API endpoints for intercepting actions,
retrieving receipts, and monitoring gateway health.
"""

import json
import logging
import time
import os
import sys
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from functools import lru_cache

# Handle import errors gracefully
try:
    from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, status
    from pydantic import BaseModel, Field
except ImportError as _import_exc:
    print(f"ERROR: Required dependencies not installed: {_import_exc}", file=sys.stderr)
    print("Install with: pip install fastapi uvicorn pydantic", file=sys.stderr)
    sys.exit(1)

# Gateway imports
from avs_gateway.models.action_request import (
    ActionRequest,
    ActionType,
    create_action_request,
)
from avs_gateway.core.gateway_core import Gateway, Decision, DecisionType
from avs_gateway.core.policy_engine import PolicyEngine
from avs_gateway.core.risk_engine import RiskEngine
from avs_gateway.core.trust_memory import TrustMemory
from avs_gateway.core.receipt_generator import ReceiptGenerator
from avs_gateway.core.audit_chain import AuditChain
from avs_gateway.core.approval_service import ApprovalService
from avs_gateway.storage.sqlite_store import SqliteStore

logger = logging.getLogger("avs_gateway.server")

# ---------------------------------------------------------------------------
# Pydantic request/response models
# ---------------------------------------------------------------------------


class InterceptRequest(BaseModel):
    """Request model for the /intercept and /decide endpoints.

    Represents an agent action that the Gateway should evaluate.
    """

    agent_id: str = Field(..., description="Unique identifier of the agent")
    action_type: str = Field(
        ...,
        description="Action category: file, email, api, payment, database, security_scan",
    )
    tool_name: str = Field(..., description="Name of the specific tool being invoked")
    operation: str = Field(..., description="Operation being performed (e.g., read, POST)")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Tool-specific parameters")
    context: Dict[str, Any] = Field(default_factory=dict, description="Execution context")
    session_id: Optional[str] = Field(default=None, description="Optional session identifier")
    agent_version: Optional[str] = Field(default=None, description="Version string of the agent software")


class InterceptResponse(BaseModel):
    """Response model for the /intercept and /decide endpoints.

    Contains the Gateway's decision and supporting metadata.
    """

    decision: str = Field(..., description="Decision: allow, deny, require_approval, quarantine")
    reason: str = Field(..., description="Human-readable explanation for the decision")
    risk_score: int = Field(..., description="Risk score at decision time (0-100)")
    trust_score: int = Field(..., description="Trust score at decision time (0-100)")
    matched_policy: Optional[str] = Field(default=None, description="Name of the matched policy, if any")
    receipt_hash: Optional[str] = Field(default=None, description="Signed receipt hash (only on /intercept)")
    processing_time_ms: float = Field(..., description="Wall-clock processing time in milliseconds")


class ReceiptsResponse(BaseModel):
    """Response model for the /receipts endpoint."""

    total: int = Field(..., description="Total number of receipts available")
    receipts: List[Dict[str, Any]] = Field(default_factory=list, description="List of receipt dictionaries")


class HealthResponse(BaseModel):
    """Response model for the /health endpoint."""

    status: str = Field(..., description="Overall health status: healthy, degraded, or unhealthy")
    version: str = Field(..., description="Gateway version string")
    timestamp: str = Field(..., description="ISO 8601 timestamp of the health check")
    uptime_seconds: float = Field(..., description="Server uptime in seconds")
    total_intercepts: int = Field(..., description="Total number of intercepted actions")


class MetricsResponse(BaseModel):
    """Response model for the /metrics endpoint."""

    total_intercepts: int = Field(..., description="Total number of intercepted actions")
    decisions: Dict[str, int] = Field(default_factory=dict, description="Count of each decision type")
    trust_stats: Dict[str, Any] = Field(default_factory=dict, description="Trust memory statistics")
    audit_chain_length: int = Field(..., description="Number of entries in the audit chain")
    avg_latency_ms: float = Field(..., description="Average processing latency in milliseconds")


# ---------------------------------------------------------------------------
# v0.2: Approval request/response models
# ---------------------------------------------------------------------------


class ApproveRequest(BaseModel):
    """Request to approve a pending approval request."""

    decided_by: str = Field(..., description="Identifier of the human approver")
    reason: str = Field(default="", description="Optional reason for approval")


class DenyRequest(BaseModel):
    """Request to deny a pending approval request."""

    decided_by: str = Field(..., description="Identifier of the human denier")
    reason: str = Field(default="", description="Optional reason for denial")


class ApprovalResponse(BaseModel):
    """Response model for a single approval request."""

    approval_id: str
    action_id: str
    agent_id: str
    action_type: str
    tool_name: str
    operation: str
    parameters: Dict[str, Any] = {}
    context: Dict[str, Any] = {}
    risk_score: float
    trust_score: float
    reason: str
    status: str
    created_at_ns: int
    decided_at_ns: Optional[int] = None
    decided_by: Optional[str] = None
    decision_reason: Optional[str] = None


class ApprovalsListResponse(BaseModel):
    """Response model for listing approval requests."""

    total: int
    pending: int
    approvals: List[ApprovalResponse]


class ApprovalActionResponse(BaseModel):
    """Response model for approve/deny actions."""

    success: bool
    approval_id: str
    new_status: str
    message: str


# ---------------------------------------------------------------------------
# Application state
# ---------------------------------------------------------------------------

# Module-level start time for uptime tracking
_START_TIME_NS: int = time.time_ns()

# Track latencies for avg calculation
_latencies_ms: List[float] = []
_MAX_LATENCY_HISTORY = 10000

# Module-level gateway instance (set on startup)
_gateway_instance: Optional[Gateway] = None

# ---------------------------------------------------------------------------
# Gateway initialization (singleton)
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def get_gateway() -> Gateway:
    """Initialize and return the Gateway singleton.

    Creates all required subsystems (PolicyEngine, RiskEngine, TrustMemory,
    ReceiptGenerator, AuditChain) and wires them into the Gateway.

    Returns:
        The initialized Gateway instance.
    """
    logger.info("Initializing Gateway components...")

    policy_engine = PolicyEngine()
    risk_engine = RiskEngine()
    trust_memory = TrustMemory()
    receipt_generator = ReceiptGenerator()
    audit_chain = AuditChain()

    # v0.2: initialize SQLite store and approval service
    store = SqliteStore()
    store.init_schema()
    approval_service = ApprovalService(store, trust_memory=trust_memory)

    gateway = Gateway(
        policy_engine=policy_engine,
        risk_engine=risk_engine,
        trust_memory=trust_memory,
        receipt_generator=receipt_generator,
        audit_chain=audit_chain,
        approval_service=approval_service,
    )

    logger.info("Gateway initialized successfully (v0.2 with approval service)")
    return gateway


# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------

app = FastAPI(
    title="AVS Gateway v0",
    description="Proof-gated execution system for agent action interception.",
    version="0.9.0",
)


@app.on_event("startup")
def startup_event() -> None:
    """Initialize the Gateway on application startup.

    Loads default policies from the configuration file and logs
    the successful startup of the AVS Gateway.
    """
    global _gateway_instance

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    gateway = get_gateway()
    _gateway_instance = gateway

    # Load default policies
    config_path = os.path.join(
        os.path.dirname(__file__), "..", "config", "default_policies.yaml"
    )
    config_path = os.path.abspath(config_path)

    if os.path.exists(config_path):
        try:
            loaded = gateway.policy_engine.load_policies(config_path)
            logger.info("Loaded %d default policies from %s", loaded, config_path)
        except Exception as exc:
            logger.warning("Failed to load default policies from %s: %s", config_path, exc)
    else:
        logger.warning("Default policies file not found at %s", config_path)

    logger.info("AVS Gateway v0.9.0 started")


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def _parse_action_type(action_type_str: str) -> ActionType:
    """Parse an action type string into an ActionType enum.

    Args:
        action_type_str: The action type as a string (e.g., "file", "api").

    Returns:
        The corresponding ActionType enum value.

    Raises:
        HTTPException: If the action type string is not recognized.
    """
    try:
        return ActionType(action_type_str.lower())
    except ValueError:
        valid = [at.value for at in ActionType]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid action_type '{action_type_str}'. Valid values: {valid}",
        )


def _decision_to_response(
    decision: Decision, receipt_hash: Optional[str] = None
) -> InterceptResponse:
    """Convert a Gateway Decision to an InterceptResponse.

    Args:
        decision: The Decision from the Gateway.
        receipt_hash: Optional signed receipt hash.

    Returns:
        The InterceptResponse Pydantic model.
    """
    return InterceptResponse(
        decision=decision.decision_type.value,
        reason=decision.reason,
        risk_score=decision.risk_score,
        trust_score=decision.trust_score,
        matched_policy=decision.matched_policy,
        receipt_hash=receipt_hash,
        processing_time_ms=round(decision.processing_time_ms, 3),
    )


def _record_latency(latency_ms: float) -> None:
    """Record a processing latency for metrics calculation.

    Args:
        latency_ms: The processing time in milliseconds.
    """
    _latencies_ms.append(latency_ms)
    if len(_latencies_ms) > _MAX_LATENCY_HISTORY:
        _latencies_ms.pop(0)


# ---------------------------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------------------------


@app.post("/intercept", response_model=InterceptResponse)
def intercept(request: InterceptRequest) -> InterceptResponse:
    """Intercept an agent action, render a decision, and generate a receipt.

    This endpoint evaluates the action through the full Gateway pipeline
    (policy, risk, trust) and produces a signed receipt for audit purposes.
    The receipt hash is included in the response.

    Args:
        request: The intercept request containing action details.

    Returns:
        InterceptResponse with the decision and receipt hash (if allowed).

    Raises:
        HTTPException: If the request is malformed or processing fails.
    """
    try:
        gateway = get_gateway()
        action_type = _parse_action_type(request.action_type)

        action_request = create_action_request(
            agent_id=request.agent_id,
            action_type=action_type,
            tool_name=request.tool_name,
            operation=request.operation,
            parameters=request.parameters,
            context=request.context,
            session_id=request.session_id,
            agent_version=request.agent_version,
        )

        decision = gateway.intercept(action_request)
        _record_latency(decision.processing_time_ms)

        # Generate receipt and record on audit chain
        receipt_hash: Optional[str] = None
        try:
            signed_receipt = gateway.record(action_request, decision)
            receipt_hash = signed_receipt.receipt_hash
        except Exception as exc:
            logger.warning("Failed to generate receipt: %s", exc)

        return _decision_to_response(decision, receipt_hash=receipt_hash)

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Error in /intercept: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(exc)}",
        )


@app.post("/decide", response_model=InterceptResponse)
def decide(request: InterceptRequest) -> InterceptResponse:
    """Intercept an agent action and render a decision (no receipt).

    This is the lightweight version of /intercept that evaluates the action
    through the Gateway pipeline but does not generate a signed receipt.
    Use this endpoint when you only need the decision.

    Args:
        request: The intercept request containing action details.

    Returns:
        InterceptResponse with the decision (no receipt_hash).

    Raises:
        HTTPException: If the request is malformed or processing fails.
    """
    try:
        gateway = get_gateway()
        action_type = _parse_action_type(request.action_type)

        action_request = create_action_request(
            agent_id=request.agent_id,
            action_type=action_type,
            tool_name=request.tool_name,
            operation=request.operation,
            parameters=request.parameters,
            context=request.context,
            session_id=request.session_id,
            agent_version=request.agent_version,
        )

        decision = gateway.intercept(action_request)
        _record_latency(decision.processing_time_ms)

        return _decision_to_response(decision, receipt_hash=None)

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Error in /decide: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(exc)}",
        )


@app.get("/receipts", response_model=ReceiptsResponse)
def get_receipts(
    limit: int = 100,
    offset: int = 0,
) -> ReceiptsResponse:
    """Retrieve signed receipts from the audit chain.

    Returns a paginated view of all receipts in the audit chain,
    sorted by sequence number (oldest first).

    Args:
        limit: Maximum number of receipts to return (default 100).
        offset: Number of receipts to skip (default 0).

    Returns:
        ReceiptsResponse with total count and receipt list.

    Raises:
        HTTPException: If pagination parameters are invalid.
    """
    try:
        if limit < 0 or offset < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="limit and offset must be non-negative",
            )

        gateway = get_gateway()
        entries = gateway.audit_chain.get_all_entries()
        total = len(entries)

        # Pagination: entries are in insertion order (oldest first)
        paginated = entries[offset : offset + limit]
        receipts = [entry.signed_receipt for entry in paginated]

        return ReceiptsResponse(total=total, receipts=receipts)

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Error in /receipts: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(exc)}",
        )


@app.get("/receipts/{receipt_hash}")
def get_receipt_by_hash(receipt_hash: str) -> Dict[str, Any]:
    """Retrieve a single receipt by its hash.

    Args:
        receipt_hash: The SHA-256 hash of the signed receipt.

    Returns:
        The signed receipt dictionary.

    Raises:
        HTTPException: 404 if the receipt is not found.
    """
    try:
        gateway = get_gateway()
        entry = gateway.audit_chain.find_by_receipt_hash(receipt_hash)

        if entry is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Receipt with hash '{receipt_hash}' not found",
            )

        return entry.signed_receipt

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Error in /receipts/%s: %s", receipt_hash, exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(exc)}",
        )


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Check the health status of the AVS Gateway.

    Returns the current health status, version, uptime, and total intercepts.
    The status is 'healthy' if the gateway is operational, 'degraded' if
    there are non-critical issues, and 'unhealthy' if critical errors exist.

    Returns:
        HealthResponse with status details.
    """
    try:
        gateway = get_gateway()
        stats = gateway.get_stats()

        uptime_seconds = (time.time_ns() - _START_TIME_NS) / 1_000_000_000.0

        # Determine health status based on gateway state
        status_str = "healthy"
        try:
            is_valid, errors = gateway.audit_chain.verify()
            if not is_valid:
                status_str = "unhealthy"
        except Exception:
            status_str = "degraded"

        return HealthResponse(
            status=status_str,
            version="0.9.0",
            timestamp=datetime.now(timezone.utc).isoformat(),
            uptime_seconds=round(uptime_seconds, 3),
            total_intercepts=stats.get("total_intercepts", 0),
        )

    except Exception as exc:
        logger.error("Error in /health: %s", exc, exc_info=True)
        # Even on error, return a degraded response rather than 500
        uptime_seconds = (time.time_ns() - _START_TIME_NS) / 1_000_000_000.0
        return HealthResponse(
            status="unhealthy",
            version="0.9.0",
            timestamp=datetime.now(timezone.utc).isoformat(),
            uptime_seconds=round(uptime_seconds, 3),
            total_intercepts=0,
        )


@app.get("/metrics", response_model=MetricsResponse)
def metrics() -> MetricsResponse:
    """Retrieve detailed metrics about the AVS Gateway.

    Returns statistics about total intercepts, decision distribution,
    trust memory state, audit chain length, and average latency.

    Returns:
        MetricsResponse with detailed metrics.
    """
    try:
        gateway = get_gateway()
        stats = gateway.get_stats()

        avg_latency = 0.0
        if _latencies_ms:
            avg_latency = sum(_latencies_ms) / len(_latencies_ms)

        trust_stats = gateway.trust_memory.get_stats()

        return MetricsResponse(
            total_intercepts=stats.get("total_intercepts", 0),
            decisions=stats.get("decisions", {}),
            trust_stats=trust_stats,
            audit_chain_length=stats.get("audit_chain_length", 0),
            avg_latency_ms=round(avg_latency, 3),
        )

    except Exception as exc:
        logger.error("Error in /metrics: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(exc)}",
        )


# ---------------------------------------------------------------------------
# v0.2: Approval endpoints
# ---------------------------------------------------------------------------


def _approval_dict_to_response(approval: Dict[str, Any]) -> ApprovalResponse:
    """Convert a raw approval dict from sqlite_store to ApprovalResponse."""
    return ApprovalResponse(
        approval_id=approval["approval_id"],
        action_id=approval["action_id"],
        agent_id=approval["agent_id"],
        action_type=approval["action_type"],
        tool_name=approval["tool_name"],
        operation=approval["operation"],
        parameters=json.loads(approval.get("parameters_json", "{}")),
        context=json.loads(approval.get("context_json", "{}")),
        risk_score=approval["risk_score"],
        trust_score=approval["trust_score"],
        reason=approval["reason"],
        status=approval["status"],
        created_at_ns=approval["created_at_ns"],
        decided_at_ns=approval.get("decided_at_ns"),
        decided_by=approval.get("decided_by"),
        decision_reason=approval.get("decision_reason"),
    )


@app.get("/approvals", response_model=ApprovalsListResponse)
def list_approvals(
    status_filter: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> ApprovalsListResponse:
    """List approval requests with optional status filter.

    Returns a paginated list of approval requests. If status_filter is
    'pending', only pending approvals are returned. Otherwise all
    approvals are returned.
    """
    try:
        gateway = get_gateway()
        if gateway.approval_service is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Approval service not initialized",
            )

        if status_filter == "pending":
            approvals = gateway.approval_service.list_pending()
        else:
            approvals = gateway.approval_service.store.list_all_approvals(
                limit=limit, offset=offset
            )

        stats = gateway.approval_service.get_stats()
        responses = [_approval_dict_to_response(a) for a in approvals]

        return ApprovalsListResponse(
            total=stats["total"],
            pending=stats["pending"],
            approvals=responses,
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Error in /approvals: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(exc)}",
        )


@app.get("/approvals/{approval_id}", response_model=ApprovalResponse)
def get_approval(approval_id: str) -> ApprovalResponse:
    """Get a single approval request by ID."""
    try:
        gateway = get_gateway()
        if gateway.approval_service is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Approval service not initialized",
            )

        approval = gateway.approval_service.get_approval(approval_id)
        if approval is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Approval '{approval_id}' not found",
            )

        return _approval_dict_to_response(approval)

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Error in /approvals/%s: %s", approval_id, exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(exc)}",
        )


@app.post("/approvals/{approval_id}/approve", response_model=ApprovalActionResponse)
def approve_approval(
    approval_id: str, request: ApproveRequest
) -> ApprovalActionResponse:
    """Approve a pending approval request.

    After approval, the action can be executed via the
    /approvals/{approval_id}/execute endpoint.
    """
    try:
        gateway = get_gateway()
        if gateway.approval_service is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Approval service not initialized",
            )

        success = gateway.approval_service.approve(
            approval_id, decided_by=request.decided_by, reason=request.reason
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Approval '{approval_id}' could not be approved (not found or not pending)",
            )

        return ApprovalActionResponse(
            success=True,
            approval_id=approval_id,
            new_status="approved",
            message=f"Approval approved by {request.decided_by}",
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Error approving %s: %s", approval_id, exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(exc)}",
        )


@app.post("/approvals/{approval_id}/deny", response_model=ApprovalActionResponse)
def deny_approval(
    approval_id: str, request: DenyRequest
) -> ApprovalActionResponse:
    """Deny a pending approval request (blocks execution forever)."""
    try:
        gateway = get_gateway()
        if gateway.approval_service is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Approval service not initialized",
            )

        success = gateway.approval_service.deny(
            approval_id, decided_by=request.decided_by, reason=request.reason
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Approval '{approval_id}' could not be denied (not found or not pending)",
            )

        return ApprovalActionResponse(
            success=True,
            approval_id=approval_id,
            new_status="denied",
            message=f"Approval denied by {request.decided_by}",
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Error denying %s: %s", approval_id, exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(exc)}",
        )


@app.post("/approvals/{approval_id}/execute")
def execute_approved(
    approval_id: str,
) -> Dict[str, Any]:
    """Execute an approved action through the simulated tool registry.

    This endpoint can only be called AFTER an approval has been
    approved via POST /approvals/{id}/approve. It executes the
    action exactly once; subsequent calls are replay-blocked.
    """
    try:
        gateway = get_gateway()
        if gateway.approval_service is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Approval service not initialized",
            )

        from avs_gateway.tools.simulated_tools import ToolRegistry

        tool_registry = ToolRegistry.create_default_registry()
        result = gateway.approval_service.execute_approved_once(
            approval_id, tool_registry
        )

        if result is None:
            # Could be: not found, not approved, already executed, or denied
            approval = gateway.approval_service.get_approval(approval_id)
            if approval is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Approval '{approval_id}' not found",
                )
            status_str = approval.get("status", "unknown")
            if status_str == "executed":
                return {
                    "executed": False,
                    "reason": "replay_blocked",
                    "message": "This action has already been executed",
                }
            if status_str == "denied":
                return {
                    "executed": False,
                    "reason": "was_denied",
                    "message": "This action was denied and cannot be executed",
                }
            return {
                "executed": False,
                "reason": f"status_is_{status_str}",
                "message": f"Cannot execute: status is {status_str}",
            }

        return {
            "executed": True,
            "result": result,
        }

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Error executing %s: %s", approval_id, exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(exc)}",
        )


@app.get("/approvals/{approval_id}/timeline")
def get_approval_timeline(approval_id: str) -> Dict[str, Any]:
    """Get the audit timeline for an approval request.

    Returns all events related to the approval lifecycle:
    approval_created, approval_approved, approval_denied,
    approval_executed, approval_replay_blocked, trust_updated.

    Args:
        approval_id: The approval request ID.

    Returns:
        Dict with approval_id and a list of timeline events.
    """
    try:
        gateway = get_gateway()
        if gateway.approval_service is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Approval service not initialized",
            )

        approval = gateway.approval_service.get_approval(approval_id)
        if approval is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Approval '{approval_id}' not found",
            )

        events = gateway.approval_service.get_approval_timeline(approval_id)

        return {
            "approval_id": approval_id,
            "status": approval["status"],
            "events": [
                {
                    "event_type": e["event_type"],
                    "timestamp_ns": e["timestamp_ns"],
                    "details": json.loads(e.get("details_json", "{}")),
                }
                for e in events
            ],
        }

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Error in /approvals/%s/timeline: %s", approval_id, exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(exc)}",
        )


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "avs_gateway.server.gateway_server:app",
        host="0.0.0.0",
        port=int(os.environ.get("GATEWAY_PORT", "8000")),
        reload=os.environ.get("GATEWAY_RELOAD", "").lower() in ("1", "true", "yes"),
    )

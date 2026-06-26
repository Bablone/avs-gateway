"""
risk_engine.py -- Risk scoring engine.

Scores ActionRequests across 8 dimensions.
Pure function: no side effects, no mutable state.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Callable
from enum import Enum
import logging

logger = logging.getLogger("avs_gateway.risk")


class RiskClassification(Enum):
    """Enumeration of risk classification levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass(frozen=True)
class RiskDimension:
    """
    A single risk dimension with its score and weight.

    Attributes:
        name: The dimension identifier (e.g., "sensitivity").
        value: Raw score for this dimension, 0-100.
        weight: Weight factor used in aggregation.
    """

    name: str
    value: int
    weight: float = 1.0


@dataclass(frozen=True)
class RiskExplanation:
    """Human-readable explanation of a risk score.

    Every scoring dimension is broken down so auditors and operators
    can understand WHY a decision was made. This is the advantage of
    heuristic scoring over black-box ML: every score is explainable.
    """
    overall_score: int
    classification: str
    dominant_factor: str  # which dimension had the highest weighted score
    dimension_breakdown: Dict[str, Dict[str, Any]]
    human_readable: str  # one-sentence summary


@dataclass(frozen=True)
class RiskScore:
    """
    Aggregated risk score for an ActionRequest.

    Attributes:
        value: The final aggregated risk score, 0-100.
        classification: Human-readable classification (low/medium/high/critical).
        dimensions: Dictionary of RiskDimension objects with weights.
        raw_dimensions: Dictionary of raw dimension scores.
        explanation: Structured explanation of how the score was derived.

    Methods:
        is_blocking: Return True if the score blocks execution.
    """

    value: int
    classification: str
    dimensions: Dict[str, RiskDimension]
    raw_dimensions: Dict[str, int]
    explanation: Optional[RiskExplanation] = None

    def is_blocking(self) -> bool:
        """
        Determine whether this risk score should block execution.

        Returns:
            True if the classification is 'high' or 'critical'.
        """
        return self.classification in ("high", "critical")


class RiskEngine:
    """
    Risk scoring engine for the AVS Gateway.

    Scores ActionRequests across 8 risk dimensions using weighted
    aggregation. The engine is stateless and deterministic.

    Attributes:
        DEFAULT_WEIGHTS: Default weight distribution across dimensions.
    """

    DEFAULT_WEIGHTS: Dict[str, float] = {
        "sensitivity": 0.15,
        "scope": 0.10,
        "reversibility": 0.15,
        "permission_level": 0.10,
        "external_impact": 0.10,
        "financial_impact": 0.15,
        "data_exposure": 0.10,
        "historical_behavior": 0.15,
    }

    def __init__(
        self,
        weights: Optional[Dict[str, float]] = None,
        custom_scorers: Optional[Dict[str, Callable]] = None,
    ) -> None:
        """
        Initialize the RiskEngine with optional custom weights and scorers.

        If weights do not sum to 1.0, they are automatically normalized.

        Args:
            weights: Optional dictionary of dimension weights.
                     Must sum to approximately 1.0.
            custom_scorers: Optional dictionary of callable overrides
                            for individual dimension scoring.
        """
        self.weights = dict(weights) if weights is not None else dict(self.DEFAULT_WEIGHTS)
        self.custom_scorers: Dict[str, Callable] = dict(custom_scorers) if custom_scorers is not None else {}
        self._validate_weights()
        logger.info("RiskEngine initialized with %d dimensions", len(self.weights))

    def _validate_weights(self) -> None:
        """
        Validate and normalize dimension weights.

        If the sum of weights is not within 0.01 of 1.0, all weights
        are scaled proportionally so that they sum to 1.0.
        """
        total = sum(self.weights.values())
        if total == 0:
            n = len(self.weights)
            if n > 0:
                for k in self.weights:
                    self.weights[k] = 1.0 / n
            return
        if abs(total - 1.0) > 0.01:
            factor = 1.0 / total
            for k in self.weights:
                self.weights[k] *= factor
            logger.debug("Weights normalized by factor %.4f", factor)

    def score(self, action_request) -> RiskScore:
        """
        Compute the risk score for an ActionRequest.

        Scores across 8 dimensions, applies custom scorers if configured,
        clamps values to the 0-100 range, and returns an aggregated score.

        Args:
            action_request: The ActionRequest to score.

        Returns:
            A RiskScore containing the aggregated score and per-dimension breakdown.
        """
        raw: Dict[str, int] = {}
        raw["sensitivity"] = self._score_sensitivity(action_request)
        raw["scope"] = self._score_scope(action_request)
        raw["reversibility"] = self._score_reversibility(action_request)
        raw["permission_level"] = self._score_permission_level(action_request)
        raw["external_impact"] = self._score_external_impact(action_request)
        raw["financial_impact"] = self._score_financial_impact(action_request)
        raw["data_exposure"] = self._score_data_exposure(action_request)
        raw["historical_behavior"] = self._score_historical_behavior(action_request)

        # Apply custom scorer overrides
        for name, scorer in self.custom_scorers.items():
            if name in raw:
                raw[name] = int(scorer(action_request, raw[name]))

        # Clamp all raw scores to [0, 100]
        raw = {k: max(0, min(100, v)) for k, v in raw.items()}

        dimensions = {
            name: RiskDimension(name=name, value=value, weight=self.weights.get(name, 1.0))
            for name, value in raw.items()
        }

        weighted_sum = sum(d.value * d.weight for d in dimensions.values())
        aggregated = int(round(weighted_sum))
        aggregated = max(0, min(100, aggregated))

        classification = self.classify(aggregated)

        explanation = self._explain_score(raw, dimensions, aggregated, classification)

        return RiskScore(
            value=aggregated,
            classification=classification,
            dimensions=dimensions,
            raw_dimensions=raw,
            explanation=explanation,
        )

    def classify(self, score: int) -> str:
        """
        Classify a numeric score into a risk category.

        Args:
            score: Integer score in the range 0-100.

        Returns:
            One of: 'low', 'medium', 'high', 'critical'.
        """
        if score <= 25:
            return "low"
        if score <= 50:
            return "medium"
        if score <= 75:
            return "high"
        return "critical"

    def _explain_score(self, raw: Dict[str, int], dimensions: Dict[str, RiskDimension],
                       aggregated: int, classification: str) -> RiskExplanation:
        """Generate human-readable explanation of risk score.

        This is what makes heuristic scoring auditable: every dimension
        is broken down with its score, weight, and contribution.
        """
        # Find dominant factor
        dominant = max(dimensions.items(), key=lambda x: x[1].value * x[1].weight)
        dominant_name, dominant_dim = dominant

        # Build dimension breakdown
        breakdown: Dict[str, Dict[str, Any]] = {}
        for name, dim in dimensions.items():
            contribution = dim.value * dim.weight
            breakdown[name] = {
                "score": dim.value,
                "weight": round(dim.weight, 2),
                "contribution": round(contribution, 1),
                "max_possible": round(100 * dim.weight, 1),
            }

        # Generate human-readable summary
        if classification == "low":
            human = f"Low risk: {dominant_name} scored {dominant_dim.value}/100 (within acceptable range)"
        elif classification == "medium":
            human = f"Medium risk: {dominant_name} elevated at {dominant_dim.value}/100 — requires approval"
        elif classification == "high":
            human = f"High risk: {dominant_name} at {dominant_dim.value}/100 — action quarantined"
        else:
            human = f"Critical risk: {dominant_name} at {dominant_dim.value}/100 — action denied"

        return RiskExplanation(
            overall_score=aggregated,
            classification=classification,
            dominant_factor=dominant_name,
            dimension_breakdown=breakdown,
            human_readable=human,
        )

    def threshold_check(self, score: RiskScore) -> str:
        """
        Map a RiskScore to an action recommendation.

        Args:
            score: The RiskScore to evaluate.

        Returns:
            One of: 'allow', 'require_approval', 'quarantine', 'deny'.
        """
        mapping = {
            "low": "allow",
            "medium": "require_approval",
            "high": "quarantine",
            "critical": "deny",
        }
        return mapping.get(score.classification, "require_approval")

    def _score_sensitivity(self, action_request) -> int:
        """
        Score the sensitivity of the action request.

        Examines tool name and parameters for sensitive keywords
        and assigns a base score based on action type.

        Args:
            action_request: The ActionRequest to score.

        Returns:
            Sensitivity score in the range 0-100.
        """
        tool = action_request.tool_name.lower()
        params = action_request.parameters
        sensitive_patterns = [
            "password",
            "secret",
            "key",
            "token",
            "credential",
            "private",
            "ssn",
            "pii",
        ]
        param_str = str(params).lower()
        sensitivity_hits = sum(1 for p in sensitive_patterns if p in param_str)
        base_scores = {
            "file": 30 if any(x in tool for x in ["config", "secret"]) else 15,
            "email": 40 if any(p in param_str for p in ["external", "outside"]) else 20,
            "api": 50 if any(x in tool for x in ["payment", "financial"]) else 25,
            "payment": 90,
            "database": 60 if any(x in tool for x in ["production", "prod"]) else 35,
            "security_scan": 45,
        }
        base = base_scores.get(action_request.action_type.value, 25)
        return min(100, base + sensitivity_hits * 10)

    def _score_scope(self, action_request) -> int:
        """
        Score the scope of impact of the action request.

        Args:
            action_request: The ActionRequest to score.

        Returns:
            Scope score in the range 0-100.
        """
        params = action_request.parameters
        scope = params.get("scope", "single")
        scope_scores: Dict[str, int] = {
            "single": 5,
            "multiple": 30,
            "all": 80,
            "global": 95,
        }
        return scope_scores.get(scope, 20)

    def _score_reversibility(self, action_request) -> int:
        """
        Score the reversibility of the action.

        Irreversible actions (e.g., DELETE, DROP) receive higher scores.

        Args:
            action_request: The ActionRequest to score.

        Returns:
            Reversibility score in the range 0-100.
        """
        op = action_request.operation
        action_type = action_request.action_type.value
        irreversible: Dict[str, Dict[str, int]] = {
            "file": {"delete": 85, "write": 40, "read": 5, "append": 30},
            "email": {"send": 70, "read": 0, "delete": 60},
            "api": {"DELETE": 80, "POST": 45, "PUT": 40, "GET": 5, "PATCH": 35},
            "payment": {"transfer": 90, "refund": 50, "query": 5},
            "database": {"DROP": 95, "DELETE": 75, "UPDATE": 50, "INSERT": 40, "SELECT": 0},
            "security_scan": {"run_scan": 20, "access_results": 10},
        }
        type_scores = irreversible.get(action_type, {})
        return type_scores.get(op, 50)

    def _score_permission_level(self, action_request) -> int:
        """
        Score based on the permission level in the request context.

        Args:
            action_request: The ActionRequest to score.

        Returns:
            Permission level score in the range 0-100.
        """
        context = action_request.context
        permission = context.get("permission_level", "user")
        level_scores: Dict[str, int] = {
            "public": 0,
            "user": 15,
            "admin": 50,
            "superuser": 75,
            "system": 90,
        }
        return level_scores.get(permission, 30)

    def _score_external_impact(self, action_request) -> int:
        """
        Score the external impact of the action.

        Actions targeting external systems receive higher scores.

        Args:
            action_request: The ActionRequest to score.

        Returns:
            External impact score in the range 0-100.
        """
        params = action_request.parameters
        context = action_request.context
        if params.get("external", False):
            return 70
        if "external" in str(context).lower():
            return 50
        if action_request.action_type.value == "api":
            return 40
        if action_request.action_type.value == "email":
            return 45
        return 15

    def _score_financial_impact(self, action_request) -> int:
        """
        Score the financial impact of the action.

        Payment actions are scored based on transaction amount.

        Args:
            action_request: The ActionRequest to score.

        Returns:
            Financial impact score in the range 0-100.
        """
        params = action_request.parameters
        amount = params.get("amount", 0)
        if action_request.action_type.value == "payment":
            if amount == 0:
                return 50
            if amount < 100:
                return 30
            if amount < 1000:
                return 60
            if amount < 10000:
                return 85
            return 100
        return 10

    def _score_data_exposure(self, action_request) -> int:
        """
        Score the potential data exposure of the action.

        Considers query patterns, file paths, and email attachments.

        Args:
            action_request: The ActionRequest to score.

        Returns:
            Data exposure score in the range 0-100.
        """
        action_type = action_request.action_type.value
        params = action_request.parameters
        if action_type == "database" and params.get("query"):
            query = str(params["query"]).lower()
            if "select *" in query or "where" in query:
                return 50
        if action_type == "file" and action_request.operation == "read":
            path = str(params.get("path", "")).lower()
            if any(p in path for p in ["secret", "config", "credential", "key"]):
                return 75
            return 30
        if action_type == "email":
            return 40 if params.get("attachments") else 25
        if action_type == "security_scan":
            return 35 if action_request.operation == "access_results" else 15
        return 10

    def _score_historical_behavior(self, action_request) -> int:
        """
        Score based on historical behavior.

        Returns a neutral score of 50. Trust scoring is applied
        separately by the Gateway layer.

        Args:
            action_request: The ActionRequest to score (unused).

        Returns:
            Historical behavior score of 50 (neutral).
        """
        return 50

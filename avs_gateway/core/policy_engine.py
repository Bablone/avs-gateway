"""
policy_engine.py -- Policy evaluation engine.

Loads policies from YAML/JSON, evaluates ActionRequests against rules.
First matching rule wins. Policies are immutable after load.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from enum import Enum
import json
import re
import logging
from pathlib import Path

logger = logging.getLogger("avs_gateway.policy")

# Attempt to import PyYAML with a fallback for environments without it.
try:
    import yaml
except ImportError:
    yaml = None  # type: ignore[assignment]

    # Minimal fallback so yaml.safe_load works for the default-policies file.
    class _MinimalYaml:
        @staticmethod
        def safe_load(stream):
            """
            Minimal YAML subset loader sufficient for the default policies file.

            Supports basic key-value mappings, lists, and scalars.
            This is a fallback when PyYAML is not installed.
            """
            if isinstance(stream, str):
                text = stream
            else:
                text = stream.read()
            return _MinimalYaml._parse(text)

        @staticmethod
        def _parse(text: str) -> Any:
            import json as _json

            text = text.strip()
            if not text:
                return {}

            # Convert YAML to a rough JSON-like structure for simple cases
            try:
                # Try json first in case it's actually JSON
                return _json.loads(text)
            except Exception:
                pass

            result: Dict[str, Any] = {}
            current_list: Optional[List[Any]] = None
            current_list_key: Optional[str] = None
            current_item: Optional[Dict[str, Any]] = None
            indent_stack: List[int] = []
            key_stack: List[str] = []
            container_stack: List[Any] = []

            i = 0
            lines = text.splitlines()

            while i < len(lines):
                line = lines[i]
                stripped = line.lstrip()
                if not stripped or stripped.startswith("#"):
                    i += 1
                    continue

                indent = len(line) - len(stripped)

                if stripped.startswith("- "):
                    item_text = stripped[2:].strip()
                    if ":" in item_text and not item_text.startswith("{"):
                        key_part, val_part = item_text.split(":", 1)
                        key_part = key_part.strip()
                        val_part = val_part.strip()
                        if val_part:
                            if current_list is None:
                                current_list = []
                                if key_stack:
                                    parent = container_stack[-1] if container_stack else result
                                    parent[key_stack[-1]] = current_list
                            if current_item is None:
                                current_item = {}
                                current_list.append(current_item)
                            current_item[key_part] = _MinimalYaml._parse_value(val_part)
                        else:
                            if current_list is None:
                                current_list = []
                                if key_stack:
                                    parent = container_stack[-1] if container_stack else result
                                    parent[key_stack[-1]] = current_list
                            if current_item is None:
                                current_item = {}
                                current_list.append(current_item)
                            current_item[key_part] = {}
                            key_stack.append(key_part)
                            container_stack.append(current_item)
                            indent_stack.append(indent)
                            current_item = None
                    else:
                        parsed_val = _MinimalYaml._parse_value(item_text)
                        if current_list is None:
                            current_list = []
                            parent = container_stack[-1] if container_stack else result
                            parent[key_stack[-1]] = current_list
                        current_list.append(parsed_val)
                        current_item = None
                elif ":" in stripped:
                    key, val = stripped.split(":", 1)
                    key = key.strip()
                    val = val.strip()

                    while indent_stack and indent <= indent_stack[-1]:
                        indent_stack.pop()
                        key_stack.pop()
                        container_stack.pop()
                        current_item = None

                    target = container_stack[-1] if container_stack else result

                    if val == "":
                        if key not in target:
                            target[key] = {}
                        key_stack.append(key)
                        container_stack.append(target[key])
                        indent_stack.append(indent)
                        current_item = None
                    else:
                        target[key] = _MinimalYaml._parse_value(val)
                i += 1

            return result

        @staticmethod
        def _parse_value(val: str) -> Any:
            val = val.strip()
            if val.startswith("[") and val.endswith("]"):
                inner = val[1:-1]
                if not inner.strip():
                    return []
                return [v.strip().strip('"\'') for v in inner.split(",")]
            if val == "true" or val == "True":
                return True
            if val == "false" or val == "False":
                return False
            if val == "null" or val == "None" or val == "~":
                return None
            if val.startswith("{") and val.endswith("}"):
                import json as _json

                try:
                    return _json.loads(val)
                except Exception:
                    return val
            try:
                if "." in val and "e" not in val.lower():
                    return float(val)
                return int(val)
            except ValueError:
                pass
            return val.strip('"\'')

    yaml = _MinimalYaml()  # type: ignore[assignment]


class DecisionType(Enum):
    """Enumeration of possible policy decisions."""

    ALLOW = "allow"
    DENY = "deny"
    REQUIRE_APPROVAL = "require_approval"
    QUARANTINE = "quarantine"


@dataclass(frozen=True)
class PolicyRule:
    """
    A single policy rule for evaluating action requests.

    Attributes:
        name: Unique identifier for the rule.
        description: Human-readable description of what the rule does.
        priority: Integer priority; lower numbers are evaluated first.
        condition: Dictionary defining the match condition.
        decision: The decision to return if this rule matches.
        reason: Human-readable explanation for the decision.
        enabled: Whether the rule is active.
        tags: Optional list of tags for categorization.
    """

    name: str
    description: str
    priority: int
    condition: Dict[str, Any]
    decision: DecisionType
    reason: str
    enabled: bool = True
    tags: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class PolicyResult:
    """
    Result of evaluating an ActionRequest against the policy engine.

    Attributes:
        matched: Whether any rule matched.
        matched_rule: Name of the matching rule, or None.
        decision: The policy decision, or None if no match.
        reason: Explanation for the decision.
        all_evaluated: List of all rule names that were evaluated.
    """

    matched: bool
    matched_rule: Optional[str]
    decision: Optional[DecisionType]
    reason: Optional[str]
    all_evaluated: List[str] = field(default_factory=list)


class PolicyEngine:
    """
    Policy evaluation engine for the AVS Gateway.

    Loads policies from YAML or JSON files and evaluates ActionRequests
    against a prioritized list of rules. The first matching rule wins.

    Attributes:
        config: Optional configuration dictionary.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        self._rules: List[PolicyRule] = []
        self._rule_index: Dict[str, PolicyRule] = {}
        self.config = config or {}
        self._default_decision = DecisionType.REQUIRE_APPROVAL
        logger.info("PolicyEngine initialized")

    def load_policies(self, path: str) -> int:
        """
        Load policy rules from a YAML or JSON file.

        The file must contain a top-level 'rules' key with a list of rule
        definitions. Each rule definition must have at minimum 'name',
        'condition', 'decision', and 'reason' keys.

        Args:
            path: Filesystem path to the policy file.

        Returns:
            Number of rules loaded.

        Raises:
            FileNotFoundError: If the policy file does not exist.
            ValueError: If the file format is invalid or a rule is malformed.
        """
        path_obj = Path(path)
        if not path_obj.exists():
            raise FileNotFoundError(f"Policy file not found: {path}")
        with open(path, "r", encoding="utf-8") as fh:
            if path.endswith(".json"):
                data = json.load(fh)
            else:
                data = yaml.safe_load(fh)
        if data is None:
            raise ValueError("Policy file is empty or could not be parsed")
        if not isinstance(data, dict) or "rules" not in data:
            raise ValueError("Policy file must contain a top-level 'rules' list")
        count = 0
        for rule_data in data["rules"]:
            if not isinstance(rule_data, dict):
                raise ValueError(f"Each rule must be a dict, got {type(rule_data).__name__}")
            required = {"name", "condition", "decision", "reason"}
            missing = required - set(rule_data.keys())
            if missing:
                raise ValueError(f"Rule is missing required fields: {missing}")
            rule = PolicyRule(
                name=rule_data["name"],
                description=rule_data.get("description", ""),
                priority=rule_data.get("priority", 100),
                condition=rule_data["condition"],
                decision=DecisionType(rule_data["decision"]),
                reason=rule_data["reason"],
                enabled=rule_data.get("enabled", True),
                tags=rule_data.get("tags", []),
            )
            self.add_rule(rule)
            count += 1
        logger.info("Loaded %d policy rules from %s", count, path)
        return count

    def add_rule(self, rule: PolicyRule) -> None:
        """
        Add a policy rule to the engine.

        Rules are stored sorted by ascending priority.

        Args:
            rule: The PolicyRule to add.
        """
        self._rules.append(rule)
        self._rule_index[rule.name] = rule
        self._rules.sort(key=lambda r: r.priority)

    def remove_rule(self, name: str) -> bool:
        """
        Remove a policy rule by name.

        Args:
            name: The unique name of the rule to remove.

        Returns:
            True if the rule was found and removed, False otherwise.
        """
        if name in self._rule_index:
            self._rules = [r for r in self._rules if r.name != name]
            del self._rule_index[name]
            return True
        return False

    def get_rule(self, name: str) -> Optional[PolicyRule]:
        """
        Retrieve a policy rule by name.

        Args:
            name: The unique name of the rule.

        Returns:
            The PolicyRule if found, None otherwise.
        """
        return self._rule_index.get(name)

    def list_rules(self) -> List[PolicyRule]:
        """
        List all loaded policy rules in priority order.

        Returns:
            List of PolicyRule instances.
        """
        return list(self._rules)

    def evaluate(self, action_request) -> PolicyResult:
        """
        Evaluate an ActionRequest against all loaded policy rules.

        Rules are checked in priority order. The first enabled rule whose
        condition matches wins. If no rule matches, the default decision
        (REQUIRE_APPROVAL) is returned.

        Args:
            action_request: The ActionRequest to evaluate.

        Returns:
            A PolicyResult describing the outcome.
        """
        evaluated: List[str] = []
        matches: List[PolicyRule] = []

        for rule in self._rules:
            if not rule.enabled:
                continue
            evaluated.append(rule.name)
            if self._match_rule(rule.condition, action_request):
                matches.append(rule)

        if matches:
            winner = matches[0]

            # Log conflicts: multiple rules matched with different decisions
            if len(matches) > 1:
                decisions = {r.decision for r in matches}
                if len(decisions) > 1:
                    logger.warning(
                        "Policy conflict: %d rules matched with different decisions. "
                        "Winner: %s (decision=%s). Losers: %s",
                        len(matches),
                        winner.name,
                        winner.decision.value,
                        [(r.name, r.decision.value) for r in matches[1:]],
                    )

            logger.debug(
                "Rule '%s' matched for action %s", winner.name, action_request.action_id
            )
            return PolicyResult(
                matched=True,
                matched_rule=winner.name,
                decision=winner.decision,
                reason=winner.reason,
                all_evaluated=evaluated,
            )

        logger.debug(
            "No matching rule for action %s; defaulting to %s",
            action_request.action_id,
            self._default_decision.value,
        )
        return PolicyResult(
            matched=False,
            matched_rule=None,
            decision=self._default_decision,
            reason="No matching policy rule; defaulting to require_approval",
            all_evaluated=evaluated,
        )

    def _match_rule(self, condition: Dict[str, Any], action_request) -> bool:
        """
        Check whether a condition matches an action request.

        Args:
            condition: The condition dictionary from the rule.
            action_request: The ActionRequest to match against.

        Returns:
            True if the condition matches, False otherwise.
        """
        return self._evaluate_condition(condition, action_request)

    def _evaluate_condition(self, condition: Any, action_request, prefix: str = "") -> bool:
        """
        Recursively evaluate a condition against an action request.

        Supports logical operators ($or, $and, $not) and field comparisons.
        Field paths use dot notation for nested access (e.g. "parameters.amount").
        Nested dict conditions are automatically flattened into dot notation.

        Args:
            condition: The condition to evaluate.
            action_request: The ActionRequest to evaluate against.
            prefix: Current field path prefix for recursive nested evaluation.

        Returns:
            True if the condition is satisfied.
        """
        if isinstance(condition, dict):
            if "$or" in condition:
                sub_conditions = condition["$or"]
                if not isinstance(sub_conditions, list):
                    raise ValueError("$or operator requires a list of conditions")
                return any(self._evaluate_condition(c, action_request) for c in sub_conditions)
            if "$and" in condition:
                sub_conditions = condition["$and"]
                if not isinstance(sub_conditions, list):
                    raise ValueError("$and operator requires a list of conditions")
                return all(self._evaluate_condition(c, action_request) for c in sub_conditions)
            if "$not" in condition:
                return not self._evaluate_condition(condition["$not"], action_request)
            for field_path, expected in condition.items():
                full_path = f"{prefix}.{field_path}" if prefix else field_path
                # If expected is a dict that contains only operator keys,
                # treat it as operator comparisons on the field value.
                if isinstance(expected, dict) and self._is_operator_dict(expected):
                    actual = self._get_field(action_request, full_path)
                    if not self._apply_operator(actual, expected):
                        return False
                # If expected is a plain dict (not operators), recurse into it
                # to build up the dot-notation path (e.g. parameters.amount).
                elif isinstance(expected, dict):
                    if not self._evaluate_condition(expected, action_request, full_path):
                        return False
                else:
                    actual = self._get_field(action_request, full_path)
                    if actual != expected:
                        return False
            return True
        return bool(condition)

    @staticmethod
    def _is_operator_dict(value: Dict[str, Any]) -> bool:
        """
        Check whether a dict is an operator dict (contains only operator keys).

        Operator keys include: eq, ne, gt, gte, lt, lte, in, nin, regex, exists, contains.

        Args:
            value: The dictionary to check.

        Returns:
            True if all keys in the dict are recognized operators.
        """
        operators = {"eq", "ne", "gt", "gte", "lt", "lte", "in", "nin", "regex", "exists", "contains"}
        if not value:
            return False
        return all(k in operators for k in value.keys())

    def _get_field(self, action_request, field_path: str) -> Any:
        """
        Retrieve a field value from an ActionRequest using dot notation.

        Supports nested dictionary keys (e.g., "parameters.amount") and
        attribute access on objects. Enum values are automatically unwrapped
        to their string representation.

        Args:
            action_request: The object to extract the field from.
            field_path: Dot-separated path to the field.

        Returns:
            The field value, or None if the path does not resolve.
            Enum instances are returned as their .value string.
        """
        if not field_path:
            return None
        parts = field_path.split(".")
        current: Any = action_request
        for part in parts:
            if current is None:
                return None
            if isinstance(current, dict):
                current = current.get(part)
            elif hasattr(current, part):
                current = getattr(current, part)
            elif hasattr(current, "to_dict"):
                current = current.to_dict().get(part)
            else:
                return None
        # Unwrap Enum instances to their string value for policy matching
        if isinstance(current, Enum):
            return current.value
        return current

    def _apply_operator(self, actual: Any, op_dict: Dict[str, Any]) -> bool:
        """
        Apply a comparison operator to an actual value.

        Supported operators: eq, ne, gt, gte, lt, lte, in, nin,
        regex, exists, contains.

        Args:
            actual: The actual value from the action request.
            op_dict: Dictionary mapping operator names to expected values.

        Returns:
            True if all operators in op_dict are satisfied.
        """
        for op, expected in op_dict.items():
            if op == "eq":
                if actual != expected:
                    return False
            elif op == "ne":
                if actual == expected:
                    return False
            elif op == "gt":
                if actual is None or actual <= expected:
                    return False
            elif op == "gte":
                if actual is None or actual < expected:
                    return False
            elif op == "lt":
                if actual is None or actual >= expected:
                    return False
            elif op == "lte":
                if actual is None or actual > expected:
                    return False
            elif op == "in":
                if actual not in expected:
                    return False
            elif op == "nin":
                if actual in expected:
                    return False
            elif op == "regex":
                if actual is None:
                    return False
                try:
                    if not bool(re.search(expected, str(actual))):
                        return False
                except re.error:
                    return False
            elif op == "exists":
                if (actual is not None) != expected:
                    return False
            elif op == "contains":
                if actual is None:
                    return False
                if expected not in str(actual):
                    return False
            else:
                logger.warning("Unknown operator '%s' in condition; treating as False", op)
                return False
        return True

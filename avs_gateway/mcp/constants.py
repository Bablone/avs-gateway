"""
mcp/constants.py — AVS MCP Guard v0.4.0

Reason codes, enums, and defaults for MCP tool-call admission control.
Every decision has a stable reason code for SIEM, audit, and policy analytics.
"""

from enum import Enum, auto


class MCPActionClass(str, Enum):
    """Deterministic classification of MCP tool actions."""
    READ_ONLY = "read_only"
    FILESYSTEM_READ = "filesystem_read"
    FILESYSTEM_WRITE = "filesystem_write"
    DESTRUCTIVE = "destructive"
    NETWORK = "network"
    DATABASE_READ = "database_read"
    DATABASE_WRITE = "database_write"
    MESSAGE_SEND = "message_send"
    CODE_EXECUTION = "code_execution"
    CREDENTIAL_ACCESS = "credential_access"
    PAYMENT_TRIGGER = "payment_trigger"
    DEPLOYMENT = "deployment"
    # v0.4.0 — Sovereign execution control: mutation classes
    FINANCIAL_MUTATION = "financial_mutation"       # Transfers, trades, balance changes
    INFRASTRUCTURE_MUTATION = "infrastructure_mutation"  # Infra changes: DNS, IAM, networking
    CODE_MUTATION = "code_mutation"                 # Code changes: commits, merges, releases
    REPOSITORY_WRITE = "repository_write"           # Registry/package writes
    UNKNOWN = "unknown"


class MCPDecision(str, Enum):
    """Admission decision for an MCP tool call."""
    ALLOW = "allow"
    DENY = "deny"
    REQUIRE_APPROVAL = "require_approval"
    QUARANTINE = "quarantine"
    WOULD_DENY = "would_deny"  # Observe mode truthfulness


class MCPReasonCode(str, Enum):
    """Stable reason codes for every MCP admission decision."""
    # Manifest / tool identity
    MCP_MANIFEST_DRIFT = "MCP_MANIFEST_DRIFT"
    MCP_UNKNOWN_TOOL = "MCP_UNKNOWN_TOOL"
    MCP_DESCRIPTOR_HASH_MISMATCH = "MCP_DESCRIPTOR_HASH_MISMATCH"
    MCP_SCHEMA_INVALID = "MCP_SCHEMA_INVALID"
    MCP_TOOL_DESCRIPTION_POISONING_SUSPECTED = "MCP_TOOL_DESCRIPTION_POISONING_SUSPECTED"
    MCP_SERVER_UNTRUSTED = "MCP_SERVER_UNTRUSTED"
    MCP_DUPLICATE_TOOL_NAME = "MCP_DUPLICATE_TOOL_NAME"
    MCP_UNICODE_HOMOGLYPH_DETECTED = "MCP_UNICODE_HOMOGLYPH_DETECTED"

    # Action class policy
    MCP_DESTRUCTIVE_ACTION_DENIED = "MCP_DESTRUCTIVE_ACTION_DENIED"
    MCP_WRITE_REQUIRES_APPROVAL = "MCP_WRITE_REQUIRES_APPROVAL"
    MCP_CODE_EXECUTION_DENIED = "MCP_CODE_EXECUTION_DENIED"
    MCP_CREDENTIAL_ACCESS_DENIED = "MCP_CREDENTIAL_ACCESS_DENIED"
    MCP_PAYMENT_REQUIRES_APPROVAL = "MCP_PAYMENT_REQUIRES_APPROVAL"
    MCP_DEPLOYMENT_REQUIRES_APPROVAL = "MCP_DEPLOYMENT_REQUIRES_APPROVAL"
    MCP_DATABASE_WRITE_REQUIRES_APPROVAL = "MCP_DATABASE_WRITE_REQUIRES_APPROVAL"
    MCP_MESSAGE_SEND_REQUIRES_APPROVAL = "MCP_MESSAGE_SEND_REQUIRES_APPROVAL"
    # v0.4.0 — Sovereign execution control: mutation reason codes
    MCP_FINANCIAL_MUTATION_REQUIRES_APPROVAL = "MCP_FINANCIAL_MUTATION_REQUIRES_APPROVAL"
    MCP_FINANCIAL_MUTATION_DENIED = "MCP_FINANCIAL_MUTATION_DENIED"
    MCP_INFRASTRUCTURE_MUTATION_REQUIRES_APPROVAL = "MCP_INFRASTRUCTURE_MUTATION_REQUIRES_APPROVAL"
    MCP_INFRASTRUCTURE_MUTATION_DENIED = "MCP_INFRASTRUCTURE_MUTATION_DENIED"
    MCP_CODE_MUTATION_REQUIRES_APPROVAL = "MCP_CODE_MUTATION_REQUIRES_APPROVAL"
    MCP_CODE_MUTATION_DENIED = "MCP_CODE_MUTATION_DENIED"
    MCP_REPOSITORY_WRITE_REQUIRES_APPROVAL = "MCP_REPOSITORY_WRITE_REQUIRES_APPROVAL"
    MCP_REPOSITORY_WRITE_DENIED = "MCP_REPOSITORY_WRITE_DENIED"

    # Network / path security
    MCP_PRIVATE_IP_QUARANTINED = "MCP_PRIVATE_IP_QUARANTINED"
    MCP_CLOUD_METADATA_BLOCKED = "MCP_CLOUD_METADATA_BLOCKED"
    MCP_PATH_TRAVERSAL = "MCP_PATH_TRAVERSAL"
    MCP_WORKSPACE_ESCAPE = "MCP_WORKSPACE_ESCAPE"
    MCP_SYMLINK_ESCAPE = "MCP_SYMLINK_ESCAPE"

    # Session / data flow
    MCP_SENSITIVE_SESSION_TAG = "MCP_SENSITIVE_SESSION_TAG"
    MCP_EXFILTRATION_RISK = "MCP_EXFILTRATION_RISK"

    # Sampling / protocol
    MCP_SAMPLING_DENIED = "MCP_SAMPLING_DENIED"
    MCP_LARGE_PAYLOAD_DENIED = "MCP_LARGE_PAYLOAD_DENIED"

    # General
    MCP_POLICY_MATCHED_ALLOW = "MCP_POLICY_MATCHED_ALLOW"
    MCP_OBSERVE_MODE_NO_BLOCK = "MCP_OBSERVE_MODE_NO_BLOCK"


class MCPResponseMode(str, Enum):
    """How AVS responds to blocked tool calls."""
    TOOL_RESULT_ERROR = "tool_result_error"  # Default: CallToolResult with isError=True
    PROTOCOL_ERROR = "protocol_error"        # JSON-RPC error


class MCPGuardMode(str, Enum):
    """Enforcement mode of the MCP Guard."""
    OBSERVE = "observe"      # Log and receipt, but do not block
    SOFT_GATE = "soft_gate"  # Block only high-risk calls
    HARD_GATE = "hard_gate"  # Block all denied calls


class MCPSessionTagType(str, Enum):
    """Deterministic session tags for data-flow tracking."""
    SENSITIVE_PATH_READ = "sensitive_path_read"
    SECRET_LIKE_CONTENT_SEEN = "secret_like_content_seen"
    CREDENTIAL_FILE_ACCESSED = "credential_file_accessed"
    ENV_FILE_ACCESSED = "env_file_accessed"
    PRIVATE_KEY_PATTERN_SEEN = "private_key_pattern_seen"
    PII_LIKE_CONTENT_SEEN = "pii_like_content_seen"


# Dangerous tool name patterns for classification
DANGEROUS_VERBS = {
    "delete", "remove", "drop", "destroy", "rm", "truncate", "purge",
    "exec", "execute", "run", "shell", "bash", "sh", "cmd", "powershell",
    "eval", "compile", "import", "load", "require",
    "send", "email", "mail", "notify", "post", "publish",
    "pay", "payment", "transfer", "charge", "invoice",
    "deploy", "release", "push", "publish",
    "chmod", "chown", "sudo", "su",
}

# Sensitive path patterns for session tagging
SENSITIVE_PATH_PATTERNS = [
    ".env", "secret", "credential", "password", "token", "api_key",
    "private_key", "id_rsa", "id_dsa", ".ssh", ".aws", ".docker",
    "/etc/passwd", "/etc/shadow", "/etc/sudoers",
]

# Private IP ranges
PRIVATE_IP_RANGES = [
    ("10.0.0.0", "10.255.255.255"),
    ("172.16.0.0", "172.31.255.255"),
    ("192.168.0.0", "192.168.255.255"),
    ("127.0.0.0", "127.255.255.255"),
    ("169.254.0.0", "169.254.255.255"),  # Link-local / cloud metadata
    ("0.0.0.0", "0.255.255.255"),
    ("::1", "::1"),  # IPv6 loopback
    ("fc00::", "fdff:ffff:ffff:ffff:ffff:ffff:ffff:ffff"),  # IPv6 unique local
]

# Cloud metadata endpoints
CLOUD_METADATA_ENDPOINTS = [
    "169.254.169.254",  # AWS, GCP, Azure metadata
    "metadata.google.internal",
    "metadata.aws.internal",
]

# Default configuration
DEFAULT_MCP_GUARD_CONFIG = {
    "mode": MCPGuardMode.HARD_GATE,
    "response_mode": MCPResponseMode.TOOL_RESULT_ERROR,
    "default_decision": MCPDecision.REQUIRE_APPROVAL,
    "sampling": {"decision": MCPDecision.DENY, "reason": MCPReasonCode.MCP_SAMPLING_DENIED},
    "unknown_tools": {"decision": MCPDecision.QUARANTINE, "reason": MCPReasonCode.MCP_UNKNOWN_TOOL},
    "manifest_drift": {"decision": MCPDecision.QUARANTINE, "reason": MCPReasonCode.MCP_MANIFEST_DRIFT},
    "schema_validation_failure": {"decision": MCPDecision.DENY, "reason": MCPReasonCode.MCP_SCHEMA_INVALID},
    "shadow_tool": {"decision": MCPDecision.DENY, "reason": MCPReasonCode.MCP_UNKNOWN_TOOL},
    "max_payload_size": 10 * 1024 * 1024,  # 10MB
    "manifest_refresh": {
        "on_initialize": True,
        "on_list_changed": True,
        "before_high_risk_call": True,
        "interval_seconds": 300,
    },
    "action_classes": {
        "read_only": {"decision": "allow", "max_risk_score": 25},
        "filesystem_read": {"decision": "allow", "max_risk_score": 25},
        "filesystem_write": {"decision": "require_approval", "max_risk_score": 60},
        "destructive": {"decision": "deny", "max_risk_score": 100},
        "network": {"decision": "require_approval", "max_risk_score": 70},
        "database_read": {"decision": "require_approval", "max_risk_score": 50},
        "database_write": {"decision": "require_approval", "max_risk_score": 75},
        "message_send": {"decision": "require_approval", "max_risk_score": 60},
        "code_execution": {"decision": "deny", "max_risk_score": 100},
        "credential_access": {"decision": "deny", "max_risk_score": 100},
        "payment_trigger": {"decision": "require_approval", "max_risk_score": 80},
        "deployment": {"decision": "require_approval", "max_risk_score": 85},
        # v0.4.0 — Sovereign execution control: mutation policies
        "financial_mutation": {"decision": "require_approval", "max_risk_score": 90},
        "infrastructure_mutation": {"decision": "require_approval", "max_risk_score": 85},
        "code_mutation": {"decision": "require_approval", "max_risk_score": 75},
        "repository_write": {"decision": "require_approval", "max_risk_score": 70},
        "unknown": {"decision": "quarantine", "max_risk_score": 75},
    },
    "workspace_root": "./workspace",
}

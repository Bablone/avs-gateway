"""
mcp/classifier.py — AVS MCP Guard v0.4.0

Step 3: Deterministic action classification.
NO LLM classification. Purely deterministic based on:
- Tool name patterns (known dangerous verbs)
- Description patterns
- Input schema fields
- Configured policy overrides
- Manifest labels

13 action classes. Cheap to evaluate. No stochasticity.
"""

import re
import logging
from typing import Dict, Any, Optional

from avs_gateway.mcp.models import MCPToolDescriptor
from avs_gateway.mcp.constants import MCPActionClass, DANGEROUS_VERBS

logger = logging.getLogger("avs_gateway.mcp.classifier")


def classify_tool(tool: MCPToolDescriptor, overrides: Optional[Dict[str, str]] = None) -> MCPActionClass:
    """Classify an MCP tool into an action class.
    
    Deterministic — same tool always produces same classification.
    Uses name patterns, description analysis, and schema heuristics.
    
    Args:
        tool: The tool descriptor to classify
        overrides: Optional dict of tool_name -> action_class overrides
        
    Returns:
        MCPActionClass enum value
    """
    # Check overrides first (highest priority)
    if overrides and tool.name in overrides:
        try:
            return MCPActionClass(overrides[tool.name])
        except ValueError:
            pass
    
    name_lower = tool.name.lower()
    desc_lower = (tool.description or "").lower()
    combined = name_lower + " " + desc_lower
    
    # Check annotations first (manifest labels)
    if tool.annotations:
        title = (tool.annotations.get("title") or "").lower()
        if "destructive" in title or "dangerous" in title:
            return MCPActionClass.DESTRUCTIVE
        if "read-only" in title:
            return MCPActionClass.READ_ONLY
    
    # Credential access — highest priority
    if _matches_any(combined, ["credential", "password", "secret", "token", "api_key", "auth"]):
        if _matches_any(combined, ["read", "get", "access", "view"]):
            return MCPActionClass.CREDENTIAL_ACCESS
    
    # Code execution
    if _matches_any(combined, ["exec", "execute", "shell", "bash", "powershell", "eval", "compile"]):
        return MCPActionClass.CODE_EXECUTION
    # "run" and "cmd" are checked separately with word-boundary awareness
    if _matches_word_any(combined, ["run", "cmd"]):
        return MCPActionClass.CODE_EXECUTION
    
    # Destructive
    if _matches_any(combined, ["delete", "remove", "drop", "destroy", "rm", "truncate", "purge", "wipe"]):
        return MCPActionClass.DESTRUCTIVE

    # Financial mutation — transfers, trades, balance changes (BEFORE payment_trigger since more specific)
    if _matches_any(combined, [
        "transfer", "trade", "swap", "buy", "sell", "stake", "unstake",
        "withdraw", "deposit", "balance_change", "escrow", "settle",
        "mint", "burn", "approve_token", "token_transfer",
    ]):
        return MCPActionClass.FINANCIAL_MUTATION

    # Payment trigger
    if _matches_any(combined, ["pay", "payment", "charge", "invoice", "billing", "checkout"]):
        return MCPActionClass.PAYMENT_TRIGGER

    # Repository write — package/registry writes (BEFORE deployment since "publish_package" is more specific)
    if _matches_any(combined, [
        "npm_publish", "docker_push", "registry_write", "upload_package",
        "pypi_upload", "gem_push", "cargo_publish", "helm_push",
        "publish_package", "push_image", "container_push",
    ]):
        return MCPActionClass.REPOSITORY_WRITE

    # Deployment
    if _matches_any(combined, ["deploy", "release", "ship"]):
        return MCPActionClass.DEPLOYMENT

    # Infrastructure mutation — DNS, IAM, networking changes
    if _matches_any(combined, [
        "dns", "iam", "firewall", "vpc", "subnet", "route53", "cloudflare",
        "load_balancer", "cdn", "ssl", "certificate", "ingress", "egress",
        "network_acl", "security_group", "bucket_policy", "iam_policy",
        "create_user", "delete_user", "attach_policy", "detach_policy",
    ]):
        return MCPActionClass.INFRASTRUCTURE_MUTATION

    # Code mutation — commits, merges, code changes
    if _matches_any(combined, [
        "commit", "merge", "pull_request", "branch", "tag",
        "code_change", "git_push", "git_merge", "approve_change",
    ]):
        return MCPActionClass.CODE_MUTATION

    # Message send
    if _matches_any(combined, ["send", "email", "mail", "notify", "message", "sms", "alert"]):
        return MCPActionClass.MESSAGE_SEND
    
    # Network
    if _matches_any(combined, ["fetch", "get_url", "http", "curl", "wget", "request", "download"]):
        return MCPActionClass.NETWORK
    
    # Database write
    if _matches_any(combined, ["insert", "update", "upsert", "create", "write_db", "sql_write"]):
        return MCPActionClass.DATABASE_WRITE
    
    # Database read
    if _matches_any(combined, ["query", "select", "read_db", "sql_read", "search", "find"]):
        return MCPActionClass.DATABASE_READ
    
    # Filesystem write
    if _matches_any(combined, ["write_file", "create_file", "append", "save", "upload"]):
        return MCPActionClass.FILESYSTEM_WRITE
    
    # Filesystem read
    if _matches_any(combined, ["read_file", "cat", "open_file", "load_file", "view"]):
        return MCPActionClass.FILESYSTEM_READ
    
    # Read-only fallback
    if _matches_any(combined, ["get_", "read_", "view_", "list_", "search_", "find_", "lookup"]):
        return MCPActionClass.READ_ONLY
    
    # Default
    return MCPActionClass.UNKNOWN


def _matches_any(text: str, patterns: list) -> bool:
    """Check if text contains any of the patterns."""
    for pattern in patterns:
        if pattern in text:
            return True
    return False


def _matches_word_any(text: str, patterns: list) -> bool:
    """Check if text contains any of the patterns as whole words.

    Uses regex word boundaries to avoid matching substrings inside
    other words (e.g., 'sh' inside 'publish').
    """
    import re
    for pattern in patterns:
        if re.search(r'\b' + re.escape(pattern) + r'\b', text):
            return True
    return False

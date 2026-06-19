"""
http_sandbox.py -- Secure HTTP sandbox for AVS Gateway v0.3.2-beta.

Governs outbound HTTP requests with defense-in-depth protections:

    1. Method validation (GET only by default)
    2. URL parsing + scheme validation (http/https only)
    3. Credential rejection (no user:pass in URLs)
    4. Domain allowlist (explicit permit required)
    5. DNS resolution + IP blocklist (SSRF protection)
    6. Credential header stripping
    7. Redirect prevention (allow_redirects=False)
    8. Response size cap (stream + byte count)
    9. Timeout enforcement
    10. Redirect status blocking (300-399 = DENY)

All blocked operations return structured SandboxResult with full audit
evidence: url, hostname, resolved_ip, decision, reason.

Usage:
    sandbox = HTTPSandbox(allowed_domains={"example.com"})
    result = sandbox.get("https://example.com/data")
    # result.status == "success" or "blocked"
    # result.resolved_ip shows what DNS resolved to
    # result.reason explains why it was allowed or blocked
"""

import ipaddress
import logging
import socket
import urllib.parse
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import requests

logger = logging.getLogger("avs_gateway.tools.http_sandbox")


class HTTPSandboxSecurityError(Exception):
    """Raised when an HTTP sandbox security boundary is violated."""
    pass


@dataclass(frozen=True)
class HTTPSandboxResult:
    """Structured result from an HTTP sandbox operation.

    Fields provide complete audit evidence for every request,
    whether allowed or blocked.
    """
    status: str                    # "success", "blocked", or "error"
    operation: str                 # "http_get", "http_post", etc.
    url: str
    hostname: Optional[str] = None
    resolved_ip: Optional[str] = None
    success: bool = False
    error: Optional[str] = None
    decision: Optional[str] = None  # "allow" or "deny"
    reason: Optional[str] = None
    status_code: Optional[int] = None
    body_preview: Optional[str] = None
    bytes_read: int = 0
    receipt_hash: Optional[str] = None  # set by caller

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "operation": self.operation,
            "url": self.url,
            "hostname": self.hostname,
            "resolved_ip": self.resolved_ip,
            "success": self.success,
            "error": self.error,
            "decision": self.decision,
            "reason": self.reason,
            "status_code": self.status_code,
            "bytes_read": self.bytes_read,
        }


class HTTPSandbox:
    """Secure HTTP sandbox with comprehensive SSRF and exfiltration protection.

    Design: standalone security utility following the FileSandbox pattern.
    Called from RealToolRegistry after Gateway policy approval.

    Usage:
        sandbox = HTTPSandbox(allowed_domains={"api.example.com"})
        result = sandbox.get("https://api.example.com/data")
        blocked = sandbox.get("https://evil.com/exfil")
        # blocked.status == "blocked", blocked.reason explains why
    """

    # ------------------------------------------------------------------
    # RFC 1918 + reserved + special-use IP ranges to block
    # ------------------------------------------------------------------
    DEFAULT_BLOCKED_NETWORKS: List[str] = [
        # IPv4 private (RFC 1918)
        "10.0.0.0/8",
        "172.16.0.0/12",
        "192.168.0.0/16",
        # IPv4 loopback
        "127.0.0.0/8",
        # IPv4 link-local (AWS metadata, APIPA)
        "169.254.0.0/16",
        # IPv4 carrier-grade NAT
        "100.64.0.0/10",
        # IPv4 special use
        "0.0.0.0/8",
        "192.0.0.0/24",
        "192.0.2.0/24",
        "192.88.99.0/24",
        "198.18.0.0/15",
        "198.51.100.0/24",
        "203.0.113.0/24",
        "224.0.0.0/4",
        "240.0.0.0/4",
        "255.255.255.255/32",
        # IPv6 loopback
        "::1/128",
        # IPv6 unique local
        "fc00::/7",
        # IPv6 link-local
        "fe80::/10",
        # IPv6 unspecified
        "::/128",
        # IPv6 multicast
        "ff00::/8",
        # IPv6 documentation
        "2001:db8::/32",
    ]

    # Headers that must never leave the sandbox (credential leakage)
    BLOCKED_HEADERS: Set[str] = {
        "authorization",
        "cookie",
        "set-cookie",
        "x-api-key",
        "x-auth-token",
        "x-csrf-token",
        "proxy-authorization",
    }

    DEFAULT_MAX_RESPONSE_BYTES = 102_400   # 100 KB
    DEFAULT_TIMEOUT_SECONDS = 5
    DEFAULT_ALLOWED_METHODS: Set[str] = {"GET"}

    # Cloud metadata endpoints (explicit block, defense in depth)
    METADATA_HOSTNAMES: Set[str] = {
        "169.254.169.254",
        "metadata.google.internal",
        "metadata.google.internal.",
        "100.100.100.200",
        "alibaba.inter",
    }

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    def __init__(
        self,
        allowed_domains: Optional[Set[str]] = None,
        allow_loopback: bool = False,
        max_response_bytes: int = DEFAULT_MAX_RESPONSE_BYTES,
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
        allowed_methods: Optional[Set[str]] = None,
        blocked_networks: Optional[List[str]] = None,
    ) -> None:
        """Initialize HTTP sandbox with security configuration.

        Args:
            allowed_domains: Set of hostnames permitted (empty = deny all).
            allow_loopback: If True, permits 127.0.0.0/8 and ::1/128.
                            Default False. Enable ONLY for local testing.
            max_response_bytes: Maximum response body size (default 100KB).
            timeout_seconds: Request timeout in seconds (default 5).
            allowed_methods: HTTP methods permitted (default {GET}).
            blocked_networks: Override default blocked IP ranges.
        """
        self._allowed_domains: Set[str] = set(d.lower() for d in (allowed_domains or set()))
        self._allow_loopback: bool = allow_loopback
        self._max_bytes: int = max_response_bytes
        self._timeout: int = timeout_seconds
        self._allowed_methods: Set[str] = set(m.upper() for m in (allowed_methods or self.DEFAULT_ALLOWED_METHODS))

        # Compile blocked networks using ipaddress (robust against all notations)
        network_strings = blocked_networks or self.DEFAULT_BLOCKED_NETWORKS
        self._blocked_networks: List[ipaddress.IPv4Network | ipaddress.IPv6Network] = []
        for cidr in network_strings:
            try:
                self._blocked_networks.append(ipaddress.ip_network(cidr, strict=False))
            except ValueError as exc:
                logger.warning("Invalid CIDR in blocked_networks: %s (%s)", cidr, exc)

        logger.info(
            "HTTPSandbox init: domains=%d loopback=%s max_bytes=%d timeout=%d methods=%s blocked_networks=%d",
            len(self._allowed_domains), self._allow_loopback, self._max_bytes,
            self._timeout, sorted(self._allowed_methods), len(self._blocked_networks),
        )

    # ------------------------------------------------------------------
    # Factory: load from YAML config
    # ------------------------------------------------------------------

    @classmethod
    def from_config(cls, config_path: str) -> "HTTPSandbox":
        """Create HTTPSandbox from YAML config file.

        Expected YAML structure::

            network:
              allowed_domains:
                - example.com
                - api.public.org
              allow_loopback_for_testing: false
              max_response_bytes: 102400
              timeout_seconds: 5
              allowed_methods:
                - GET
        """
        import yaml

        path = Path(config_path)
        if not path.exists():
            raise FileNotFoundError(f"Network policy config not found: {config_path}")

        with open(path, "r") as f:
            data = yaml.safe_load(f)

        net = data.get("network", {})
        return cls(
            allowed_domains=set(net.get("allowed_domains", [])),
            allow_loopback=net.get("allow_loopback_for_testing", False),
            max_response_bytes=net.get("max_response_bytes", cls.DEFAULT_MAX_RESPONSE_BYTES),
            timeout_seconds=net.get("timeout_seconds", cls.DEFAULT_TIMEOUT_SECONDS),
            allowed_methods=set(net.get("allowed_methods", ["GET"])),
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get(self, url: str, headers: Optional[Dict[str, str]] = None) -> HTTPSandboxResult:
        """Execute secure HTTP GET with full protection pipeline.

        Args:
            url: Target URL (must be http/https, no embedded credentials).
            headers: Optional request headers (credential headers stripped).

        Returns:
            HTTPSandboxResult with full audit evidence.
        """
        return self._execute("GET", url, headers)

    def post(self, url: str, headers: Optional[Dict[str, str]] = None, data: Optional[Any] = None) -> HTTPSandboxResult:
        """Execute HTTP POST (blocked by default unless configured)."""
        return self._execute("POST", url, headers, data)

    # ------------------------------------------------------------------
    # Core: 10-layer security pipeline
    # ------------------------------------------------------------------

    def _execute(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        data: Optional[Any] = None,
    ) -> HTTPSandboxResult:
        """Execute HTTP request through the full security pipeline."""
        start_ts = __import__("time").time()
        result_fields = {
            "operation": f"http_{method.lower()}",
            "url": url,
        }

        try:
            # -- Layer 1: Method validation --------------------------------
            if method.upper() not in self._allowed_methods:
                return self._blocked(
                    **result_fields,
                    reason=f"HTTP method {method.upper()} not allowed (configured: {sorted(self._allowed_methods)})",
                )

            # -- Layer 2: URL parsing + scheme validation ------------------
            try:
                parsed = urllib.parse.urlparse(url)
            except ValueError as exc:
                return self._blocked(**result_fields, reason=f"URL parse error: {exc}")

            if parsed.scheme not in ("http", "https"):
                return self._blocked(
                    **result_fields,
                    hostname=parsed.hostname,
                    reason=f"Scheme '{parsed.scheme}' not allowed (only http/https)",
                )

            hostname = parsed.hostname
            port = parsed.port

            # -- Layer 3: Credential rejection -----------------------------
            if parsed.username or parsed.password:
                return self._blocked(
                    **result_fields,
                    hostname=hostname,
                    reason="URL contains embedded credentials (security risk)",
                )

            # -- Layer 4: Domain allowlist ---------------------------------
            if hostname is None:
                return self._blocked(**result_fields, reason="No hostname in URL")

            hostname_lower = hostname.lower()

            # Strip trailing dot for comparison
            if hostname_lower.endswith("."):
                hostname_lower = hostname_lower[:-1]

            if hostname_lower not in self._allowed_domains:
                return self._blocked(
                    **result_fields,
                    hostname=hostname,
                    reason=f"Domain '{hostname}' not in allowlist",
                )

            # -- Layer 5: DNS resolution + IP blocklist (SSRF) -------------
            resolved_ip = self._resolve_and_validate(hostname)

            # Extra: explicit metadata endpoint block (defense in depth)
            if hostname_lower in self.METADATA_HOSTNAMES:
                return self._blocked(
                    **result_fields,
                    hostname=hostname,
                    resolved_ip=resolved_ip,
                    reason=f"Cloud metadata endpoint blocked: {hostname}",
                )

            # -- Layer 6: Credential header stripping ----------------------
            safe_headers: Dict[str, str] = {}
            if headers:
                for key, value in headers.items():
                    if key.lower() not in self.BLOCKED_HEADERS:
                        safe_headers[key] = value
                    else:
                        logger.debug("Stripped credential header: %s", key)

            # -- Layers 7-9: Execute with protections ----------------------
            response = requests.request(
                method.upper(),
                url,
                headers=safe_headers,
                data=data,
                timeout=self._timeout,
                allow_redirects=False,      # Layer 7: sever redirect chains
                stream=True,                # Layer 8: stream for size cap
            )

            # Layer 10: Redirect status blocking
            if 300 <= response.status_code < 400:
                response.close()
                return self._blocked(
                    **result_fields,
                    hostname=hostname,
                    resolved_ip=resolved_ip,
                    status_code=response.status_code,
                    reason=f"HTTP {response.status_code} redirect blocked (SSRF prevention)",
                )

            # Layer 8: Response size cap (stream + count)
            body_bytes = self._read_capped(response)

            body_text = body_bytes.decode("utf-8", errors="replace")

            # Generate receipt hash
            import hashlib
            receipt = hashlib.sha256(
                f"{url}:{method}:{response.status_code}:{resolved_ip}".encode()
            ).hexdigest()

            latency = (__import__("time").time() - start_ts) * 1000

            logger.info(
                "HTTP %s %s -> %d (ip=%s bytes=%d latency=%.1fms)",
                method, url, response.status_code, resolved_ip,
                len(body_bytes), latency,
            )

            return HTTPSandboxResult(
                status="success",
                operation=result_fields["operation"],
                url=url,
                hostname=hostname,
                resolved_ip=resolved_ip,
                success=True,
                decision="allow",
                reason="All security checks passed",
                status_code=response.status_code,
                body_preview=body_text[:500],
                bytes_read=len(body_bytes),
                receipt_hash=receipt,
            )

        except HTTPSandboxSecurityError as exc:
            return self._blocked(**result_fields, reason=str(exc))
        except requests.Timeout:
            return self._blocked(**result_fields, reason=f"Request timeout ({self._timeout}s)")
        except requests.ConnectionError as exc:
            return self._blocked(**result_fields, reason=f"Connection error: {exc}")
        except requests.RequestException as exc:
            return self._blocked(**result_fields, reason=f"Request failed: {exc}")
        except Exception as exc:
            logger.exception("Unexpected error in HTTP sandbox: %s", url)
            return HTTPSandboxResult(
                status="error",
                operation=result_fields["operation"],
                url=url,
                success=False,
                error=f"Unexpected error: {exc}",
                decision="deny",
                reason=f"Unexpected error: {exc}",
            )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve_and_validate(self, hostname: str) -> str:
        """Resolve hostname to IP and validate against blocklist.

        Handles IPv6 literals (strips brackets before resolution).
        Checks ALL resolved IPs — if ANY is blocked, the request fails.

        Args:
            hostname: Hostname or IP literal to resolve.

        Returns:
            First safe resolved IP address string.

        Raises:
            HTTPSandboxSecurityError: If any resolved IP is blocked.
        """
        # Strip IPv6 brackets if present (e.g., [::1] -> ::1)
        clean_host = hostname
        if clean_host.startswith("[") and clean_host.endswith("]"):
            clean_host = clean_host[1:-1]

        # If already an IP literal, validate directly (no DNS needed)
        try:
            ip_obj = ipaddress.ip_address(clean_host)
            if self._is_blocked_ip(ip_obj):
                raise HTTPSandboxSecurityError(
                    f"SSRF: IP literal {clean_host} is in blocked range"
                )
            return clean_host
        except ValueError:
            pass  # Not an IP literal, proceed to DNS

        # DNS resolution
        try:
            addr_infos = socket.getaddrinfo(clean_host, None)
        except socket.gaierror as exc:
            raise HTTPSandboxSecurityError(f"DNS resolution failed for {hostname}: {exc}")

        if not addr_infos:
            raise HTTPSandboxSecurityError(f"DNS resolution returned no results for {hostname}")

        # Check ALL resolved IPs — fail if ANY is blocked
        first_ip: Optional[str] = None
        for info in addr_infos:
            family, _, _, _, sockaddr = info
            ip_str = sockaddr[0]
            try:
                ip_obj = ipaddress.ip_address(ip_str)
            except ValueError:
                continue

            if self._is_blocked_ip(ip_obj):
                blocked_net = self._find_blocking_network(ip_obj)
                raise HTTPSandboxSecurityError(
                    f"SSRF: {hostname} resolved to {ip_str} which is in "
                    f"blocked range {blocked_net or '(unknown)'}"
                )

            if first_ip is None:
                first_ip = ip_str

        if first_ip is None:
            raise HTTPSandboxSecurityError(f"No valid IPs resolved for {hostname}")

        return first_ip

    def _is_blocked_ip(self, ip_obj: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
        """Check if IP address is in any blocked network.

        Args:
            ip_obj: Parsed IP address.

        Returns:
            True if IP is in a blocked range.
        """
        for network in self._blocked_networks:
            if ip_obj in network:
                # Exception: loopback allowed for testing if configured
                if self._allow_loopback and ip_obj.is_loopback:
                    return False
                return True
        return False

    def _find_blocking_network(
        self, ip_obj: ipaddress.IPv4Address | ipaddress.IPv6Address
    ) -> Optional[str]:
        """Find which network blocks this IP (for error messages)."""
        for network in self._blocked_networks:
            if ip_obj in network:
                return str(network)
        return None

    def _read_capped(self, response) -> bytes:
        """Read response body with strict byte cap.

        Streams the response and stops immediately when max_bytes is exceeded.
        This prevents memory exhaustion attacks via large/chunked responses.

        Args:
            response: requests.Response with stream=True.

        Returns:
            Body bytes (<= max_bytes).

        Raises:
            HTTPSandboxSecurityError: If response exceeds max_bytes.
        """
        # Quick check: Content-Length header (but don't trust it alone)
        content_length = response.headers.get("Content-Length")
        if content_length:
            try:
                if int(content_length) > self._max_bytes:
                    response.close()
                    raise HTTPSandboxSecurityError(
                        f"Response Content-Length ({content_length}) exceeds "
                        f"limit ({self._max_bytes} bytes)"
                    )
            except ValueError:
                pass  # Invalid Content-Length, ignore and use streaming check

        # Stream and count bytes
        chunks: List[bytes] = []
        total = 0
        for chunk in response.iter_content(chunk_size=8192):
            total += len(chunk)
            if total > self._max_bytes:
                response.close()
                raise HTTPSandboxSecurityError(
                    f"Response body exceeded {self._max_bytes} bytes limit "
                    f"(read {total} bytes before abort)"
                )
            chunks.append(chunk)

        return b"".join(chunks)

    @staticmethod
    def _blocked(
        operation: str,
        url: str,
        hostname: Optional[str] = None,
        resolved_ip: Optional[str] = None,
        status_code: Optional[int] = None,
        reason: str = "Blocked",
    ) -> HTTPSandboxResult:
        """Create a blocked result."""
        logger.info("HTTP blocked: %s %s — %s", operation, url, reason)
        return HTTPSandboxResult(
            status="blocked",
            operation=operation,
            url=url,
            hostname=hostname,
            resolved_ip=resolved_ip,
            success=False,
            decision="deny",
            reason=reason,
            status_code=status_code,
        )

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def allowed_domains(self) -> Set[str]:
        return set(self._allowed_domains)

    @property
    def stats(self) -> Dict[str, Any]:
        return {
            "allowed_domains": len(self._allowed_domains),
            "allow_loopback": self._allow_loopback,
            "max_response_bytes": self._max_bytes,
            "timeout_seconds": self._timeout,
            "allowed_methods": sorted(self._allowed_methods),
            "blocked_networks": len(self._blocked_networks),
        }

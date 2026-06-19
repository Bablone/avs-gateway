"""
Unit tests for avs_gateway.tools.http_sandbox.

All tests are deterministic — no actual network calls.
DNS is mocked via socket.getaddrinfo.
HTTP is mocked via requests.request.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

import ipaddress
import socket
from unittest.mock import MagicMock, patch

import pytest
import requests

from avs_gateway.tools.http_sandbox import HTTPSandbox, HTTPSandboxResult, HTTPSandboxSecurityError


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sandbox() -> HTTPSandbox:
    """Default sandbox: example.com allowed, loopback blocked."""
    return HTTPSandbox(allowed_domains={"example.com"})


@pytest.fixture
def sandbox_loopback() -> HTTPSandbox:
    """Sandbox with loopback enabled for testing redirect/size scenarios."""
    return HTTPSandbox(
        allowed_domains={"localhost", "127.0.0.1"},
        allow_loopback=True,
    )


@pytest.fixture
def mock_response():
    """Create a mock requests.Response."""
    def _make(status_code=200, content=b'{"status":"ok"}', headers=None):
        r = MagicMock()
        r.status_code = status_code
        r.headers = headers or {"Content-Type": "application/json"}
        r.iter_content.return_value = [content[i:i+1024] for i in range(0, len(content), 1024)]
        return r
    return _make


# ---------------------------------------------------------------------------
# Layer 1: Method validation
# ---------------------------------------------------------------------------

class TestMethodValidation:
    def test_get_allowed(self, sandbox):
        """GET is allowed by default."""
        with patch("avs_gateway.tools.http_sandbox.requests.request") as mock_req, \
             patch("avs_gateway.tools.http_sandbox.socket.getaddrinfo", return_value=[
                 (2, 1, 6, "", ("93.184.216.34", 0))
             ]):
            mock_req.return_value = MagicMock(status_code=200, headers={})
            mock_req.return_value.iter_content.return_value = [b"ok"]
            result = sandbox.get("https://example.com/")
            assert result.status == "success"
            assert result.decision == "allow"

    def test_post_blocked(self, sandbox):
        """POST is blocked by default."""
        result = sandbox.post("https://example.com/api")
        assert result.status == "blocked"
        assert "POST not allowed" in result.reason

    def test_put_blocked(self, sandbox):
        """PUT is blocked."""
        result = sandbox._execute("PUT", "https://example.com/resource")
        assert result.status == "blocked"
        assert "PUT not allowed" in result.reason

    def test_delete_blocked(self, sandbox):
        """DELETE is blocked."""
        result = sandbox._execute("DELETE", "https://example.com/resource")
        assert result.status == "blocked"

    def test_custom_method_allowed(self):
        """Sandbox can be configured to allow non-GET methods."""
        sb = HTTPSandbox(allowed_domains={"example.com"}, allowed_methods={"GET", "POST"})
        with patch("avs_gateway.tools.http_sandbox.requests.request") as mock_req, \
             patch("avs_gateway.tools.http_sandbox.socket.getaddrinfo", return_value=[
                 (2, 1, 6, "", ("93.184.216.34", 0))
             ]):
            mock_req.return_value = MagicMock(status_code=201, headers={})
            mock_req.return_value.iter_content.return_value = [b"created"]
            result = sb.post("https://example.com/api")
            assert result.status == "success"


# ---------------------------------------------------------------------------
# Layer 2: Scheme validation
# ---------------------------------------------------------------------------

class TestSchemeValidation:
    def test_ftp_blocked(self, sandbox):
        """FTP scheme is blocked."""
        result = sandbox.get("ftp://example.com/file")
        assert result.status == "blocked"
        assert "Scheme 'ftp' not allowed" in result.reason

    def test_file_blocked(self, sandbox):
        """file:// scheme is blocked."""
        result = sandbox.get("file:///etc/passwd")
        assert result.status == "blocked"
        assert "file" in result.reason.lower()

    def test_gopher_blocked(self, sandbox):
        """gopher:// scheme is blocked."""
        result = sandbox.get("gopher://example.com/")
        assert result.status == "blocked"

    def test_https_allowed(self, sandbox):
        """https:// is allowed."""
        with patch("avs_gateway.tools.http_sandbox.requests.request") as mock_req, \
             patch("avs_gateway.tools.http_sandbox.socket.getaddrinfo", return_value=[
                 (2, 1, 6, "", ("93.184.216.34", 0))
             ]):
            mock_req.return_value = MagicMock(status_code=200, headers={})
            mock_req.return_value.iter_content.return_value = [b"ok"]
            result = sandbox.get("https://example.com/")
            assert result.status == "success"


# ---------------------------------------------------------------------------
# Layer 3: Credential rejection
# ---------------------------------------------------------------------------

class TestCredentialRejection:
    def test_embedded_username_blocked(self, sandbox):
        """URL with embedded username is blocked."""
        result = sandbox.get("https://admin:secret@example.com/")
        assert result.status == "blocked"
        assert "embedded credentials" in result.reason

    def test_embedded_password_only_blocked(self, sandbox):
        """URL with password (no username) is blocked."""
        result = sandbox.get("https://:secret@example.com/")
        assert result.status == "blocked"
        assert "embedded credentials" in result.reason


# ---------------------------------------------------------------------------
# Layer 4: Domain allowlist
# ---------------------------------------------------------------------------

class TestDomainAllowlist:
    def test_allowlisted_domain_passes(self, sandbox):
        """Allowlisted domain passes to DNS check."""
        with patch("avs_gateway.tools.http_sandbox.socket.getaddrinfo", return_value=[
            (2, 1, 6, "", ("93.184.216.34", 0))
        ]):
            with patch("avs_gateway.tools.http_sandbox.requests.request") as mock_req:
                mock_req.return_value = MagicMock(status_code=200, headers={})
                mock_req.return_value.iter_content.return_value = [b"ok"]
                result = sandbox.get("https://example.com/")
                assert result.status == "success"

    def test_non_allowlisted_blocked(self, sandbox):
        """Non-allowlisted domain is blocked."""
        result = sandbox.get("https://evil.com/exfil")
        assert result.status == "blocked"
        assert "evil.com" in result.reason
        assert "not in allowlist" in result.reason

    def test_subdomain_not_inherited(self, sandbox):
        """Subdomains are NOT automatically allowlisted."""
        result = sandbox.get("https://subdomain.example.com/")
        assert result.status == "blocked"

    def test_empty_allowlist_blocks_all(self):
        """Sandbox with empty allowlist blocks everything."""
        sb = HTTPSandbox(allowed_domains=set())
        result = sb.get("https://anywhere.com/")
        assert result.status == "blocked"

    def test_case_insensitive_domains(self):
        """Domain matching is case-insensitive."""
        sb = HTTPSandbox(allowed_domains={"EXAMPLE.COM"})
        with patch("avs_gateway.tools.http_sandbox.socket.getaddrinfo", return_value=[
            (2, 1, 6, "", ("93.184.216.34", 0))
        ]):
            with patch("avs_gateway.tools.http_sandbox.requests.request") as mock_req:
                mock_req.return_value = MagicMock(status_code=200, headers={})
                mock_req.return_value.iter_content.return_value = [b"ok"]
                result = sb.get("https://example.com/")
                assert result.status == "success"


# ---------------------------------------------------------------------------
# Layer 5: SSRF / IP blocklist
# ---------------------------------------------------------------------------

class TestSSRFProtection:
    def test_loopback_blocked_by_default(self, sandbox):
        """127.0.0.1 is blocked without allow_loopback."""
        result = sandbox.get("https://127.0.0.1/admin")
        # Should be blocked at domain allowlist stage (127.0.0.1 not in allowed_domains)
        # OR at IP stage. Either way: blocked.
        assert result.status == "blocked"

    def test_ipv4_private_class_a_blocked(self, sandbox):
        """10.0.0.0/8 is blocked."""
        sb = HTTPSandbox(allowed_domains={"internal.example.com"})
        with patch("avs_gateway.tools.http_sandbox.socket.getaddrinfo", return_value=[
            (2, 1, 6, "", ("10.0.0.5", 0))
        ]):
            result = sb.get("https://internal.example.com/")
            assert result.status == "blocked"
            assert "10.0.0.5" in result.reason

    def test_ipv4_private_class_b_blocked(self, sandbox):
        """172.16.0.0/12 is blocked."""
        sb = HTTPSandbox(allowed_domains={"internal.example.com"})
        with patch("avs_gateway.tools.http_sandbox.socket.getaddrinfo", return_value=[
            (2, 1, 6, "", ("172.20.0.1", 0))
        ]):
            result = sb.get("https://internal.example.com/")
            assert result.status == "blocked"

    def test_ipv4_private_class_c_blocked(self, sandbox):
        """192.168.0.0/16 is blocked."""
        sb = HTTPSandbox(allowed_domains={"internal.example.com"})
        with patch("avs_gateway.tools.http_sandbox.socket.getaddrinfo", return_value=[
            (2, 1, 6, "", ("192.168.1.100", 0))
        ]):
            result = sb.get("https://internal.example.com/")
            assert result.status == "blocked"

    def test_aws_metadata_endpoint_blocked(self, sandbox):
        """169.254.169.254 is blocked (link-local range catches it)."""
        sb = HTTPSandbox(allowed_domains={"169.254.169.254"})
        result = sb.get("https://169.254.169.254/latest/meta-data/")
        assert result.status == "blocked"
        assert "SSRF" in result.reason and "169.254" in result.reason

    def test_ipv6_loopback_blocked(self, sandbox):
        """[::1] is blocked (link-local range catches it)."""
        sb = HTTPSandbox(allowed_domains={"::1"})  # urlparse strips brackets
        result = sb.get("https://[::1]/admin")
        assert result.status == "blocked"
        assert "SSRF" in result.reason

    def test_ipv4_literal_blocked(self, sandbox):
        """Direct IP literal 192.168.x.x is blocked."""
        sb = HTTPSandbox(allowed_domains={"192.168.1.1"})
        result = sb.get("https://192.168.1.1/router")
        assert result.status == "blocked"
        assert "SSRF" in result.reason

    def test_public_ip_allowed(self, sandbox):
        """Public IP (93.184.216.34 = example.com) is allowed."""
        with patch("avs_gateway.tools.http_sandbox.socket.getaddrinfo", return_value=[
            (2, 1, 6, "", ("93.184.216.34", 0))
        ]):
            with patch("avs_gateway.tools.http_sandbox.requests.request") as mock_req:
                mock_req.return_value = MagicMock(status_code=200, headers={})
                mock_req.return_value.iter_content.return_value = [b"ok"]
                result = sandbox.get("https://example.com/")
                assert result.status == "success"
                assert result.resolved_ip == "93.184.216.34"

    def test_loopback_enabled_allows_localhost(self, sandbox_loopback):
        """With allow_loopback=True, 127.0.0.1 resolves and passes."""
        with patch("avs_gateway.tools.http_sandbox.socket.getaddrinfo", return_value=[
            (2, 1, 6, "", ("127.0.0.1", 0))
        ]):
            with patch("avs_gateway.tools.http_sandbox.requests.request") as mock_req:
                mock_req.return_value = MagicMock(status_code=200, headers={})
                mock_req.return_value.iter_content.return_value = [b"ok"]
                result = sandbox_loopback.get("https://127.0.0.1:8080/test")
                assert result.status == "success"
                assert result.resolved_ip == "127.0.0.1"

    def test_multiple_ips_one_blocked(self, sandbox):
        """If ANY resolved IP is blocked, request fails."""
        sb = HTTPSandbox(allowed_domains={"dual.example.com"})
        with patch("avs_gateway.tools.http_sandbox.socket.getaddrinfo", return_value=[
            (2, 1, 6, "", ("10.0.0.1", 0)),      # blocked (private)
            (2, 1, 6, "", ("93.184.216.34", 0)),  # safe (public)
        ]):
            result = sb.get("https://dual.example.com/")
            assert result.status == "blocked"
            assert "10.0.0.1" in result.reason

    def test_dns_failure_blocked(self, sandbox):
        """DNS resolution failure is treated as a block."""
        with patch("avs_gateway.tools.http_sandbox.socket.getaddrinfo", side_effect=socket.gaierror("NXDOMAIN")):
            result = sandbox.get("https://example.com/")
            assert result.status == "blocked"
            assert "DNS" in result.reason


# ---------------------------------------------------------------------------
# Layer 6: Header credential stripping
# ---------------------------------------------------------------------------

class TestHeaderStripping:
    def test_auth_header_stripped(self, sandbox):
        """Authorization header is stripped before request."""
        with patch("avs_gateway.tools.http_sandbox.socket.getaddrinfo", return_value=[
            (2, 1, 6, "", ("93.184.216.34", 0))
        ]):
            with patch("avs_gateway.tools.http_sandbox.requests.request") as mock_req:
                mock_req.return_value = MagicMock(status_code=200, headers={})
                mock_req.return_value.iter_content.return_value = [b"ok"]
                sandbox.get("https://example.com/", headers={
                    "Authorization": "Bearer SECRET_TOKEN",
                    "Accept": "application/json",
                })
                call_kwargs = mock_req.call_args[1]
                passed_headers = call_kwargs.get("headers", {})
                assert "Authorization" not in passed_headers
                assert "Accept" in passed_headers  # non-credential header preserved

    def test_api_key_header_stripped(self, sandbox):
        """X-Api-Key header is stripped."""
        with patch("avs_gateway.tools.http_sandbox.socket.getaddrinfo", return_value=[
            (2, 1, 6, "", ("93.184.216.34", 0))
        ]):
            with patch("avs_gateway.tools.http_sandbox.requests.request") as mock_req:
                mock_req.return_value = MagicMock(status_code=200, headers={})
                mock_req.return_value.iter_content.return_value = [b"ok"]
                sandbox.get("https://example.com/", headers={
                    "X-API-Key": "super_secret",
                    "User-Agent": "AVS-Test",
                })
                call_kwargs = mock_req.call_args[1]
                passed_headers = call_kwargs.get("headers", {})
                assert "X-API-Key" not in passed_headers
                assert "X-API-Key".lower() not in {k.lower() for k in passed_headers}
                assert "User-Agent" in passed_headers

    def test_cookie_header_stripped(self, sandbox):
        """Cookie header is stripped."""
        with patch("avs_gateway.tools.http_sandbox.socket.getaddrinfo", return_value=[
            (2, 1, 6, "", ("93.184.216.34", 0))
        ]):
            with patch("avs_gateway.tools.http_sandbox.requests.request") as mock_req:
                mock_req.return_value = MagicMock(status_code=200, headers={})
                mock_req.return_value.iter_content.return_value = [b"ok"]
                sandbox.get("https://example.com/", headers={
                    "Cookie": "session=ADMIN",
                })
                call_kwargs = mock_req.call_args[1]
                passed_headers = call_kwargs.get("headers", {})
                assert "Cookie" not in passed_headers


# ---------------------------------------------------------------------------
# Layer 7-10: Redirect blocking, size cap, timeout
# ---------------------------------------------------------------------------

class TestResponseHandling:
    def test_redirect_301_blocked(self, sandbox_loopback):
        """HTTP 301 redirect response is blocked."""
        with patch("avs_gateway.tools.http_sandbox.socket.getaddrinfo", return_value=[
            (2, 1, 6, "", ("127.0.0.1", 0))
        ]):
            with patch("avs_gateway.tools.http_sandbox.requests.request") as mock_req:
                mock_req.return_value = MagicMock(status_code=301, headers={"Location": "http://evil.com"})
                result = sandbox_loopback.get("https://127.0.0.1:9999/redirect")
                assert result.status == "blocked"
                assert "redirect" in result.reason.lower()
                assert result.status_code == 301

    def test_redirect_302_blocked(self, sandbox_loopback):
        """HTTP 302 redirect response is blocked."""
        with patch("avs_gateway.tools.http_sandbox.socket.getaddrinfo", return_value=[
            (2, 1, 6, "", ("127.0.0.1", 0))
        ]):
            with patch("avs_gateway.tools.http_sandbox.requests.request") as mock_req:
                mock_req.return_value = MagicMock(status_code=302, headers={})
                result = sandbox_loopback.get("https://127.0.0.1:9999/redirect")
                assert result.status == "blocked"
                assert "302" in result.reason or "redirect" in result.reason.lower()

    def test_content_length_over_cap_blocked(self, sandbox_loopback):
        """Response with Content-Length > max is blocked."""
        with patch("avs_gateway.tools.http_sandbox.socket.getaddrinfo", return_value=[
            (2, 1, 6, "", ("127.0.0.1", 0))
        ]):
            with patch("avs_gateway.tools.http_sandbox.requests.request") as mock_req:
                mock_resp = MagicMock()
                mock_resp.status_code = 200
                mock_resp.headers = {"Content-Length": "999999999"}
                mock_resp.iter_content.return_value = []
                mock_req.return_value = mock_resp
                result = sandbox_loopback.get("https://127.0.0.1:9999/huge")
                assert result.status == "blocked"
                assert "Content-Length" in result.reason

    def test_streaming_size_cap(self, sandbox_loopback):
        """Response that exceeds cap mid-stream is blocked."""
        with patch("avs_gateway.tools.http_sandbox.socket.getaddrinfo", return_value=[
            (2, 1, 6, "", ("127.0.0.1", 0))
        ]):
            with patch("avs_gateway.tools.http_sandbox.requests.request") as mock_req:
                mock_resp = MagicMock()
                mock_resp.status_code = 200
                mock_resp.headers = {}  # No Content-Length
                # Simulate 150KB response in chunks
                chunks = [b"x" * 8192] * 20  # 20 * 8KB = 160KB
                mock_resp.iter_content.return_value = chunks
                mock_req.return_value = mock_resp
                result = sandbox_loopback.get("https://127.0.0.1:9999/stream")
                assert result.status == "blocked"
                assert "exceeded" in result.reason.lower()

    def test_timeout_blocked(self, sandbox):
        """Request timeout results in blocked status."""
        with patch("avs_gateway.tools.http_sandbox.socket.getaddrinfo", return_value=[
            (2, 1, 6, "", ("93.184.216.34", 0))
        ]):
            with patch("avs_gateway.tools.http_sandbox.requests.request", side_effect=requests.Timeout):
                result = sandbox.get("https://example.com/slow")
                assert result.status == "blocked"
                assert "timeout" in result.reason.lower()

    def test_connection_error_blocked(self, sandbox):
        """Connection error results in blocked status."""
        with patch("avs_gateway.tools.http_sandbox.socket.getaddrinfo", return_value=[
            (2, 1, 6, "", ("93.184.216.34", 0))
        ]):
            with patch("avs_gateway.tools.http_sandbox.requests.request", side_effect=requests.ConnectionError("refused")):
                result = sandbox.get("https://example.com/")
                assert result.status == "blocked"
                assert "Connection" in result.reason


# ---------------------------------------------------------------------------
# Result structure
# ---------------------------------------------------------------------------

class TestResultStructure:
    def test_success_result_has_all_fields(self, sandbox):
        """Successful result contains all expected fields."""
        with patch("avs_gateway.tools.http_sandbox.socket.getaddrinfo", return_value=[
            (2, 1, 6, "", ("93.184.216.34", 0))
        ]):
            with patch("avs_gateway.tools.http_sandbox.requests.request") as mock_req:
                mock_req.return_value = MagicMock(status_code=200, headers={})
                mock_req.return_value.iter_content.return_value = [b"hello world"]
                result = sandbox.get("https://example.com/")
                assert result.status == "success"
                assert result.decision == "allow"
                assert result.url == "https://example.com/"
                assert result.hostname == "example.com"
                assert result.resolved_ip == "93.184.216.34"
                assert result.status_code == 200
                assert result.body_preview == "hello world"
                assert result.bytes_read == 11
                assert result.receipt_hash is not None
                assert len(result.receipt_hash) == 64  # SHA-256 hex

    def test_blocked_result_has_reason(self, sandbox):
        """Blocked result always has a human-readable reason."""
        result = sandbox.get("https://evil.com/")
        assert result.status == "blocked"
        assert result.decision == "deny"
        assert result.reason
        assert len(result.reason) > 0

    def test_to_dict_serializable(self, sandbox):
        """to_dict() returns a serializable dict."""
        result = sandbox.get("https://evil.com/")
        d = result.to_dict()
        assert isinstance(d, dict)
        assert d["url"] == "https://evil.com/"
        assert d["status"] == "blocked"


# ---------------------------------------------------------------------------
# Config loading
# ---------------------------------------------------------------------------

class TestConfigLoading:
    def test_from_config_loads_yaml(self, tmp_path):
        """from_config loads policies from YAML."""
        config_file = tmp_path / "network.yaml"
        config_file.write_text("""
network:
  allowed_domains:
    - test.com
  allow_loopback_for_testing: true
  max_response_bytes: 50000
  timeout_seconds: 3
  allowed_methods:
    - GET
    - POST
""")
        sb = HTTPSandbox.from_config(str(config_file))
        assert sb.allowed_domains == {"test.com"}
        assert sb.stats["allow_loopback"] is True
        assert sb.stats["max_response_bytes"] == 50000
        assert sb.stats["timeout_seconds"] == 3
        assert sb.stats["allowed_methods"] == ["GET", "POST"]

    def test_from_config_missing_file(self, tmp_path):
        """from_config raises FileNotFoundError for missing file."""
        with pytest.raises(FileNotFoundError):
            HTTPSandbox.from_config(str(tmp_path / "nonexistent.yaml"))


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------

class TestStats:
    def test_stats_structure(self, sandbox):
        """stats() returns configuration summary."""
        s = sandbox.stats
        assert s["allowed_domains"] == 1
        assert s["allow_loopback"] is False
        assert s["max_response_bytes"] == 102_400
        assert s["timeout_seconds"] == 5
        assert s["allowed_methods"] == ["GET"]
        assert s["blocked_networks"] > 20  # many default ranges

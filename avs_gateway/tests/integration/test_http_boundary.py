"""
Integration tests: HTTPSandbox + local mock HTTP server.

Proves the full chain with real HTTP:
    HTTPSandbox -> socket.getaddrinfo -> actual HTTP request -> mock server

Uses Python's built-in http.server (no external dependencies).
"""

import sys
import os
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from avs_gateway.tools.http_sandbox import HTTPSandbox


# ---------------------------------------------------------------------------
# Local mock HTTP server
# ---------------------------------------------------------------------------

class MockHandler(BaseHTTPRequestHandler):
    """HTTP handler for integration testing."""

    # Large response body (>100KB) for size-cap test
    LARGE_BODY = b"X" * 200_000  # 200 KB

    def do_GET(self):
        if self.path == "/safe":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status":"ok","data":[1,2,3]}')

        elif self.path == "/redirect":
            self.send_response(301)
            self.send_header("Location", "http://192.168.1.1/admin")
            self.end_headers()

        elif self.path == "/oversized":
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(self.LARGE_BODY)

        elif self.path == "/slow":
            # Intentionally slow (but under test timeout)
            time.sleep(0.1)
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'{"delayed":true}')

        elif self.path == "/echo-headers":
            self.send_response(200)
            self.end_headers()
            # Echo back received headers (minus Host which http.server adds)
            headers = {k: v for k, v in self.headers.items() if k.lower() != "host"}
            import json
            self.wfile.write(json.dumps(headers).encode())

        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'{"error":"not found"}')

    def do_POST(self):
        self.send_response(201)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"created":true}')

    def log_message(self, fmt, *args):
        pass  # Suppress server logs during tests


@pytest.fixture(scope="module")
def mock_server():
    """Start a local HTTP server for integration testing."""
    server = HTTPServer(("127.0.0.1", 0), MockHandler)  # port 0 = auto-assign
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    time.sleep(0.2)  # Let server start
    yield {"host": "127.0.0.1", "port": port, "base_url": f"http://127.0.0.1:{port}"}
    server.shutdown()


@pytest.fixture
def loopback_sandbox(mock_server):
    """Sandbox with loopback enabled to reach the mock server."""
    return HTTPSandbox(
        allowed_domains={"localhost", "127.0.0.1"},
        allow_loopback=True,
        max_response_bytes=102_400,
        timeout_seconds=5,
    )


@pytest.fixture
def strict_sandbox(mock_server):
    """Strict sandbox (loopback disabled) — should block local requests."""
    return HTTPSandbox(
        allowed_domains={"127.0.0.1"},
        allow_loopback=False,
    )


# ---------------------------------------------------------------------------
# Integration tests
# ---------------------------------------------------------------------------

class TestIntegrationAllow:
    def test_safe_get(self, loopback_sandbox, mock_server):
        """Allowed GET to local server succeeds."""
        url = f"{mock_server['base_url']}/safe"
        result = loopback_sandbox.get(url)
        assert result.status == "success"
        assert result.success is True
        assert result.status_code == 200
        assert result.decision == "allow"
        assert '"status":"ok"' in result.body_preview
        assert result.resolved_ip == "127.0.0.1"
        assert result.bytes_read > 0

    def test_resolved_ip_in_result(self, loopback_sandbox, mock_server):
        """Result includes the resolved IP address."""
        url = f"{mock_server['base_url']}/safe"
        result = loopback_sandbox.get(url)
        assert result.resolved_ip == "127.0.0.1"

    def test_receipt_hash_present(self, loopback_sandbox, mock_server):
        """Successful request has a receipt hash."""
        url = f"{mock_server['base_url']}/safe"
        result = loopback_sandbox.get(url)
        assert result.receipt_hash is not None
        assert len(result.receipt_hash) == 64


class TestIntegrationBlock:
    def test_post_blocked(self, loopback_sandbox, mock_server):
        """POST to local server is blocked (method restriction)."""
        url = f"{mock_server['base_url']}/safe"
        result = loopback_sandbox.post(url)
        assert result.status == "blocked"
        assert "POST not allowed" in result.reason
        assert result.success is False

    def test_strict_blocks_loopback(self, strict_sandbox, mock_server):
        """Strict sandbox (loopback=False) blocks 127.0.0.1."""
        url = f"{mock_server['base_url']}/safe"
        result = strict_sandbox.get(url)
        assert result.status == "blocked"
        # Could be blocked at domain allowlist (127.0.0.1 IS in allowed_domains here)
        # or at IP check (loopback disabled) — either way, blocked.
        assert result.success is False


class TestIntegrationRedirect:
    def test_redirect_blocked(self, loopback_sandbox, mock_server):
        """301 redirect response is blocked, not followed."""
        url = f"{mock_server['base_url']}/redirect"
        result = loopback_sandbox.get(url)
        assert result.status == "blocked"
        assert "redirect" in result.reason.lower()
        assert result.status_code == 301


class TestIntegrationSizeCap:
    def test_oversized_response_blocked(self, loopback_sandbox, mock_server):
        """Response >100KB is blocked mid-stream."""
        url = f"{mock_server['base_url']}/oversized"
        result = loopback_sandbox.get(url)
        assert result.status == "blocked"
        assert "exceeded" in result.reason.lower() or "limit" in result.reason.lower()
        assert result.success is False


class TestIntegrationHeaders:
    def test_credential_headers_stripped(self, loopback_sandbox, mock_server):
        """Credential headers are stripped before reaching server."""
        url = f"{mock_server['base_url']}/echo-headers"
        result = loopback_sandbox.get(url, headers={
            "Authorization": "Bearer SECRET",
            "X-API-Key": "super_secret",
            "Accept": "application/json",
            "User-Agent": "AVS-Test/1.0",
        })
        assert result.status == "success"
        import json
        echoed = json.loads(result.body_preview)
        assert "Authorization" not in echoed
        assert "X-API-Key" not in echoed
        assert "Accept" in echoed  # non-credential preserved


class TestIntegrationSlow:
    def test_slow_response_succeeds(self, loopback_sandbox, mock_server):
        """Slow response within timeout succeeds."""
        url = f"{mock_server['base_url']}/slow"
        result = loopback_sandbox.get(url)
        assert result.status == "success"
        assert result.status_code == 200

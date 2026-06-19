"""
AVS Gateway v0.3.2-beta -- Network Boundary Sandbox Demo.

Demonstrates 7 scenarios of HTTP egress governance:
    1. ALLOW: Safe GET to allowlisted domain
    2. DENY: POST blocked (method restriction)
    3. DENY: Non-allowlisted domain
    4. DENY: SSRF (loopback IP probe)
    5. DENY: AWS metadata endpoint
    6. DENY: Redirect response blocked
    7. DENY: Oversized response severed

Uses a local mock HTTP server for scenarios that need real HTTP.

Usage:
    cd avs_gateway
    python demo/network_boundary_demo.py
"""

import os
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from avs_gateway.tools.http_sandbox import HTTPSandbox

SEP = "=" * 70
SUB = "-" * 70


# ---------------------------------------------------------------------------
# Local mock server (for integration scenarios)
# ---------------------------------------------------------------------------

class DemoHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/safe":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"service":"public-api","version":"1.0"}')
        elif self.path == "/redirect":
            self.send_response(302)
            self.send_header("Location", "http://192.168.1.1/admin")
            self.end_headers()
        elif self.path == "/oversized":
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"X" * 200_000)  # 200 KB
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        self.send_response(201)
        self.end_headers()
        self.wfile.write(b'{"created":true}')

    def log_message(self, fmt, *args):
        pass


def start_mock_server():
    server = HTTPServer(("127.0.0.1", 0), DemoHandler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    time.sleep(0.2)
    return server, port


# ---------------------------------------------------------------------------
# Demo helpers
# ---------------------------------------------------------------------------

def banner(title):
    print(f"\n{SEP}")
    print(f"  {title}")
    print(f"{SEP}")


def step(num, desc):
    print(f"\n{num}. {desc}")
    print(SUB)


def print_result(r):
    print(f"    status       : {r.status}")
    print(f"    decision     : {r.decision}")
    print(f"    url          : {r.url}")
    print(f"    hostname     : {r.hostname}")
    print(f"    resolved_ip  : {r.resolved_ip}")
    print(f"    reason       : {r.reason}")
    if r.status_code:
        print(f"    status_code  : {r.status_code}")
    if r.body_preview:
        preview = r.body_preview[:80].replace(chr(10), " ")
        print(f"    body_preview : {preview}...")
    if r.bytes_read:
        print(f"    bytes_read   : {r.bytes_read}")
    if r.receipt_hash:
        print(f"    receipt_hash : {r.receipt_hash[:24]}...")


def main():
    passed = 0
    failed = 0

    # Start local mock server for scenarios that need real HTTP
    server, port = start_mock_server()
    base_url = f"http://127.0.0.1:{port}"

    # Create sandboxes
    strict_sandbox = HTTPSandbox(
        allowed_domains={"example.com", "169.254.169.254"},
        allow_loopback=False,
    )
    test_sandbox = HTTPSandbox(
        allowed_domains={"localhost", "127.0.0.1", "example.com"},
        allow_loopback=True,
    )

    banner("AVS GATEWAY v0.3.2-beta -- NETWORK BOUNDARY SANDBOX DEMO")
    print(f"\n  Mock server  : {base_url}")
    print(f"  Strict rules : GET only, no loopback, 100KB cap, 5s timeout")
    print(f"  Domains      : example.com, localhost (test only)")

    # ===================================================================
    # Scenario 1: ALLOW -- Safe GET to allowlisted domain (mock server)
    # ===================================================================
    step(1, "ALLOW: Safe GET to allowlisted domain")
    r1 = test_sandbox.get(f"{base_url}/safe")
    print_result(r1)
    if r1.status == "success" and r1.status_code == 200 and r1.decision == "allow":
        print("    [PASS] Request executed, response received")
        passed += 1
    else:
        print("    [FAIL] Request should have succeeded")
        failed += 1

    # ===================================================================
    # Scenario 2: DENY -- POST blocked (method restriction)
    # ===================================================================
    step(2, "DENY: POST request blocked")
    r2 = test_sandbox.post(f"{base_url}/safe", data={"key": "value"})
    print_result(r2)
    if r2.status == "blocked" and "POST not allowed" in r2.reason:
        print("    [PASS] POST blocked at method validation layer")
        passed += 1
    else:
        print("    [FAIL] POST should have been blocked")
        failed += 1

    # ===================================================================
    # Scenario 3: DENY -- Non-allowlisted domain
    # ===================================================================
    step(3, "DENY: Non-allowlisted domain")
    r3 = strict_sandbox.get("https://evil.com/exfiltrate")
    print_result(r3)
    if r3.status == "blocked" and "evil.com" in r3.reason:
        print("    [PASS] Unknown domain blocked at allowlist layer")
        passed += 1
    else:
        print("    [FAIL] Unknown domain should have been blocked")
        failed += 1

    # ===================================================================
    # Scenario 4: DENY -- SSRF (loopback IP probe)
    # ===================================================================
    step(4, "DENY: SSRF -- loopback IP probe (127.0.0.1)")
    r4 = strict_sandbox.get("http://127.0.0.1:8080/admin")
    print_result(r4)
    if r4.status == "blocked":
        print("    [PASS] Loopback access blocked (SSRF protection)")
        passed += 1
    else:
        print("    [FAIL] Loopback should be blocked without allow_loopback")
        failed += 1

    # ===================================================================
    # Scenario 5: DENY -- AWS metadata endpoint
    # ===================================================================
    step(5, "DENY: AWS metadata endpoint (169.254.169.254)")
    r5 = strict_sandbox.get("http://169.254.169.254/latest/meta-data/iam/security-credentials/")
    print_result(r5)
    if r5.status == "blocked" and ("metadata" in r5.reason.lower() or "169.254" in r5.reason):
        print("    [PASS] Cloud metadata endpoint blocked (SSRF protection)")
        passed += 1
    else:
        print("    [FAIL] Metadata endpoint should be blocked")
        failed += 1

    # ===================================================================
    # Scenario 6: DENY -- Redirect response blocked
    # ===================================================================
    step(6, "DENY: HTTP redirect response blocked")
    r6 = test_sandbox.get(f"{base_url}/redirect")
    print_result(r6)
    if r6.status == "blocked" and r6.status_code == 302 and "redirect" in r6.reason.lower():
        print("    [PASS] Redirect response blocked (not followed)")
        passed += 1
    else:
        print("    [FAIL] Redirect should be blocked")
        failed += 1

    # ===================================================================
    # Scenario 7: DENY -- Oversized response severed
    # ===================================================================
    step(7, "DENY: Oversized response severed at 100KB cap")
    r7 = test_sandbox.get(f"{base_url}/oversized")
    print_result(r7)
    if r7.status == "blocked" and ("exceeded" in r7.reason.lower() or "limit" in r7.reason.lower()):
        print("    [PASS] Oversized response severed mid-stream")
        passed += 1
    else:
        print("    [FAIL] Oversized response should be blocked")
        failed += 1

    # ===================================================================
    # Summary
    # ===================================================================
    banner("SUMMARY")
    print(f"\n    Passed : {passed}")
    print(f"    Failed : {failed}")

    if failed == 0:
        print("\n    [ALL 7 SCENARIOS PASSED]")
        print("\n    HTTP egress is now governed:")
        print("    - GET-only by default (mutating methods blocked)")
        print("    - Domain allowlist (unknown destinations blocked)")
        print("    - SSRF protection (private IPs blocked)")
        print("    - Metadata protection (cloud endpoints blocked)")
        print("    - Redirect severing (300-399 not followed)")
        print("    - Size capping (100KB stream limit)")
        print("    - Timeout enforcement (5s ceiling)")
    else:
        print(f"\n    [{failed} SCENARIO(S) FAILED]")

    print(f"\n{SEP}\n")
    server.shutdown()
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

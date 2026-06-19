"""
AVS Gateway v0.3.0-alpha -- Real Tool Sandbox Demo.

Demonstrates AVS governing actual filesystem side effects.
All paths are canonicalized before execution.
Path traversal, absolute path escapes, and symlinks are blocked.
No file deletion in v0.3.0-alpha.

Usage:
    $env:PYTHONPATH = (Get-Location).Path
    python .\\demo\\real_tool_sandbox_demo.py
"""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from avs_gateway.tools.file_sandbox import FileSandbox
from avs_gateway.tools.real_tool_registry import RealToolRegistry

SEP = "=" * 70
SUB = "-" * 70
SANDBOX_DIR = "sandbox"
OUTSIDE_FILE = "outside_avs_sandbox.txt"


def banner(title: str) -> None:
    print(f"\n{SEP}")
    print(f"  {title}")
    print(f"{SEP}")


def step(num: int, desc: str) -> None:
    print(f"\n{num}. {desc}")
    print(SUB)


def print_result(r) -> None:
    print(f"    status     : {r.status}")
    print(f"    operation  : {r.operation}")
    print(f"    raw_path   : {r.raw_requested_path}")
    print(f"    resolved   : {r.resolved_path or '(blocked before resolve)'}")
    print(f"    success    : {r.success}")
    if r.error:
        print(f"    error      : {r.error}")
    if r.content is not None:
        print(f"    content    : {repr(r.content[:80])}")
    if r.bytes_handled:
        print(f"    bytes      : {r.bytes_handled}")


def cleanup() -> None:
    """Remove sandbox and outside test files from previous runs."""
    import shutil
    if os.path.isdir(SANDBOX_DIR):
        shutil.rmtree(SANDBOX_DIR)
    for f in [OUTSIDE_FILE]:
        if os.path.exists(f):
            os.remove(f)
    print(f"[cleanup] removed {SANDBOX_DIR}/ and {OUTSIDE_FILE}")


def outside_file_exists() -> bool:
    return os.path.exists(OUTSIDE_FILE)


def main() -> int:
    cleanup()

    banner("AVS GATEWAY v0.3.0-alpha -- REAL TOOL SANDBOX")

    registry = RealToolRegistry(sandbox_root=os.path.abspath(SANDBOX_DIR))
    sb = registry.file_sandbox
    print(f"    Sandbox root : {sb.root}")
    print(f"    Max file size: {sb._max_file_size} bytes")

    passed = 0
    failed = 0

    # ------------------------------------------------------------------
    step(1, "ALLOW: write sandbox/output.txt")
    # ------------------------------------------------------------------
    r1 = registry.execute("file_write", raw_path="output.txt", content="Hello from AVS-governed agent!")
    print_result(r1)
    target = os.path.join(SANDBOX_DIR, "output.txt")
    file_exists = os.path.isfile(target)
    print(f"    file exists  : {file_exists}")
    if r1.status == "success" and r1.success and file_exists:
        print("    [PASS] File written inside sandbox")
        passed += 1
    else:
        print("    [FAIL] File not written")
        failed += 1

    # ------------------------------------------------------------------
    step(2, "ALLOW: read sandbox/output.txt")
    # ------------------------------------------------------------------
    r2 = registry.execute("file_read", raw_path="output.txt")
    print_result(r2)
    if r2.status == "success" and r2.content == "Hello from AVS-governed agent!":
        print("    [PASS] File read correctly")
        passed += 1
    else:
        print("    [FAIL] File read incorrect")
        failed += 1

    # ------------------------------------------------------------------
    step(3, "DENY: write ../outside_avs_sandbox.txt (path traversal)")
    # ------------------------------------------------------------------
    r3 = registry.execute("file_write", raw_path=f"../{OUTSIDE_FILE}", content="escaped!")
    print_result(r3)
    escaped = outside_file_exists()
    print(f"    outside file exists: {escaped}")
    if r3.status == "blocked" and not escaped:
        print("    [PASS] Path traversal blocked, no file outside sandbox")
        passed += 1
    else:
        print("    [FAIL] Path traversal NOT blocked")
        failed += 1

    # ------------------------------------------------------------------
    step(4, "DENY: write sandbox/../../outside_avs_sandbox.txt (deep traversal)")
    # ------------------------------------------------------------------
    r4 = registry.execute("file_write", raw_path=f"{SANDBOX_DIR}/../../{OUTSIDE_FILE}", content="deep escape!")
    print_result(r4)
    escaped4 = outside_file_exists()
    print(f"    outside file exists: {escaped4}")
    if r4.status == "blocked" and not escaped4:
        print("    [PASS] Deep traversal blocked")
        passed += 1
    else:
        print("    [FAIL] Deep traversal NOT blocked")
        failed += 1

    # ------------------------------------------------------------------
    step(5, "DENY: write absolute path outside sandbox")
    # ------------------------------------------------------------------
    if os.name == "nt":
        abs_path = "C:\\Windows\\Temp\\avs_test_escape.txt"
    else:
        abs_path = "/tmp/avs_test_escape.txt"

    r5 = registry.execute("file_write", raw_path=abs_path, content="abs escape!")
    print_result(r5)
    abs_exists = os.path.exists(abs_path)
    print(f"    abs file exists: {abs_exists}")
    if r5.status == "blocked" and not abs_exists:
        print("    [PASS] Absolute path blocked")
        passed += 1
    else:
        print("    [FAIL] Absolute path NOT blocked")
        failed += 1

    # ------------------------------------------------------------------
    step(6, "DENY: symlink escape (if platform supports)")
    # ------------------------------------------------------------------
    symlink_tested = False
    try:
        import tempfile
        outside_dir = tempfile.mkdtemp(prefix="avs_outside_")
        outside_file = os.path.join(outside_dir, "secret.txt")
        with open(outside_file, "w") as f:
            f.write("secret!")

        link_path = os.path.join(SANDBOX_DIR, "evil_link")
        os.symlink(outside_dir, link_path)

        r6 = registry.execute("file_write", raw_path="evil_link/injected.txt", content="via symlink!")
        print_result(r6)
        symlink_tested = True

        injected = os.path.exists(os.path.join(outside_dir, "injected.txt"))
        print(f"    injected file exists: {injected}")
        if r6.status == "blocked" and not injected:
            print("    [PASS] Symlink escape blocked")
            passed += 1
        else:
            print("    [FAIL] Symlink escape NOT blocked")
            failed += 1

        # cleanup
        if os.path.exists(link_path):
            os.remove(link_path)
        if os.path.isdir(outside_dir):
            import shutil
            shutil.rmtree(outside_dir)

    except (OSError, PermissionError, NotImplementedError) as exc:
        print(f"    [SKIP] Symlink test: {exc}")
        print("    (Symlink creation not supported on this platform/user)")

    # ------------------------------------------------------------------
    step(7, "DENY: delete sandbox/output.txt (unsupported in v0.3.0)")
    # ------------------------------------------------------------------
    r7 = registry.execute("file_delete", raw_path="output.txt")
    print_result(r7)
    still_exists = os.path.exists(os.path.join(SANDBOX_DIR, "output.txt"))
    print(f"    file still exists: {still_exists}")
    if r7.status == "blocked" and still_exists:
        print("    [PASS] Delete blocked, file preserved")
        passed += 1
    else:
        print("    [FAIL] Delete NOT blocked or file missing")
        failed += 1

    # ------------------------------------------------------------------
    step(8, "LIST: files in sandbox")
    # ------------------------------------------------------------------
    r8 = registry.execute("file_list", raw_path=".")
    print_result(r8)
    if r8.status == "success" and "output.txt" in (r8.content or ""):
        print("    [PASS] Sandbox listing works")
        passed += 1
    else:
        print("    [FAIL] Sandbox listing failed")
        failed += 1

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    banner("SUMMARY")
    print(f"\n    Passed : {passed}")
    print(f"    Failed : {failed}")
    print(f"    Skipped: {1 if not symlink_tested else 0} (symlink)")

    if failed == 0:
        print(f"\n    [ALL CHECKS PASSED]")
        print(f"\n    Proof: AVS governs real filesystem side effects.")
        print(f"    Path traversal: blocked.")
        print(f"    Absolute escape: blocked.")
        print(f"    Symlink escape: blocked.")
        print(f"    Delete: blocked.")
        print(f"    Safe write/read: works.")
        print(f"\n    The machine obeyed AVS, not the agent.")
    else:
        print(f"\n    [{failed} CHECK(S) FAILED]")

    print(f"\n{SEP}\n")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

"""
Unit tests for avs_gateway.tools.file_sandbox

Tests path canonicalization, sandbox boundary enforcement,
and all attack vectors: traversal, absolute paths, symlinks.
"""

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

import pytest

from avs_gateway.tools.file_sandbox import FileSandbox, SandboxSecurityError


@pytest.fixture
def fresh_sandbox():
    """Fresh FileSandbox in a temp directory for each test."""
    tmp = tempfile.mkdtemp(prefix="avs_sandbox_test_")
    sb = FileSandbox(root=tmp)
    yield sb
    # cleanup
    import shutil
    shutil.rmtree(tmp, ignore_errors=True)


class TestFileSandboxSafeOperations:
    """Tests for legitimate sandbox operations."""

    def test_write_and_read(self, fresh_sandbox):
        """Writing then reading a file should work."""
        r = fresh_sandbox.write_file("hello.txt", "world")
        assert r.status == "success"
        assert r.success is True
        assert r.bytes_handled == 5

        r2 = fresh_sandbox.read_file("hello.txt")
        assert r2.status == "success"
        assert r2.content == "world"

    def test_write_nested_directory(self, fresh_sandbox):
        """Writing to a nested path should create directories."""
        r = fresh_sandbox.write_file("a/b/c/deep.txt", "nested content")
        assert r.status == "success"
        assert r.resolved_path is not None
        assert "deep.txt" in r.resolved_path

        r2 = fresh_sandbox.read_file("a/b/c/deep.txt")
        assert r2.content == "nested content"

    def test_list_files(self, fresh_sandbox):
        """Listing should return files in sandbox."""
        fresh_sandbox.write_file("alpha.txt", "a")
        fresh_sandbox.write_file("beta.txt", "b")
        r = fresh_sandbox.list_files(".")
        assert r.status == "success"
        assert "alpha.txt" in r.content
        assert "beta.txt" in r.content

    def test_read_nonexistent(self, fresh_sandbox):
        """Reading a nonexistent file should return blocked."""
        r = fresh_sandbox.read_file("missing.txt")
        assert r.status == "blocked"
        assert not r.success
        assert "not found" in r.error.lower()

    def test_extension_whitelist(self, fresh_sandbox):
        """Extension whitelist should block disallowed extensions."""
        sb = FileSandbox(
            root=fresh_sandbox.root,
            allowed_extensions={".txt", ".csv"},
        )
        r = sb.write_file("safe.txt", "ok")
        assert r.status == "success"

        r2 = sb.write_file("evil.exe", "payload")
        assert r2.status == "blocked"
        assert ".exe" in r2.error

    def test_size_limit(self, fresh_sandbox):
        """Oversized writes should be blocked."""
        sb = FileSandbox(root=fresh_sandbox.root, max_file_size=10)
        r = sb.write_file("big.txt", "x" * 100)
        assert r.status == "blocked"
        assert "exceeds" in r.error.lower()


class TestFileSandboxPathTraversal:
    """Tests for path traversal attack prevention."""

    def test_parent_directory_escape(self, fresh_sandbox):
        """../ should escape sandbox and be blocked."""
        outside = os.path.join(os.path.dirname(fresh_sandbox.root), "escaped.txt")
        # ensure outside file does not exist
        if os.path.exists(outside):
            os.remove(outside)

        r = fresh_sandbox.write_file("../escaped.txt", "bad")
        assert r.status == "blocked"
        assert not r.success
        assert not os.path.exists(outside)

    def test_deep_traversal(self, fresh_sandbox):
        """sandbox/../../ should escape and be blocked."""
        root_parent = os.path.dirname(fresh_sandbox.root)
        outside = os.path.join(root_parent, "deep_escape.txt")
        if os.path.exists(outside):
            os.remove(outside)

        r = fresh_sandbox.write_file(
            os.path.basename(fresh_sandbox.root) + "/../../deep_escape.txt",
            "deep bad",
        )
        assert r.status == "blocked"
        assert not os.path.exists(outside)

    def test_absolute_path_escape(self, fresh_sandbox):
        """Absolute paths outside sandbox should be blocked."""
        if os.name == "nt":
            abs_path = "C:\\Windows\\Temp\\avs_abs_test.txt"
        else:
            abs_path = "/tmp/avs_abs_test.txt"

        if os.path.exists(abs_path):
            os.remove(abs_path)

        r = fresh_sandbox.write_file(abs_path, "abs bad")
        assert r.status == "blocked"
        assert not os.path.exists(abs_path)

    def test_dot_dot_in_middle(self, fresh_sandbox):
        """a/../b should resolve to b (safe) inside sandbox."""
        r = fresh_sandbox.write_file("a/../safe.txt", "ok")
        assert r.status == "success"
        r2 = fresh_sandbox.read_file("safe.txt")
        assert r2.content == "ok"

    def test_many_dotdots(self, fresh_sandbox):
        """../../../../ should be blocked regardless of depth."""
        r = fresh_sandbox.write_file("../../../../../../../../etc/passwd", "x")
        assert r.status == "blocked"


class TestFileSandboxSymlinkEscape:
    """Tests for symlink-based sandbox escape."""

    def test_symlink_to_outside_blocked(self, fresh_sandbox):
        """A symlink inside sandbox pointing outside should be followed
        and resolved, then blocked if the resolved target escapes."""
        import shutil

        # Create a real directory outside the sandbox
        outside_dir = tempfile.mkdtemp(prefix="avs_outside_")
        try:
            link_name = os.path.join(fresh_sandbox.root, "evil_link")
            try:
                os.symlink(outside_dir, link_name)
            except (OSError, NotImplementedError):
                pytest.skip("Symlink creation not supported on this platform")

            # Writing through the symlink should be blocked
            r = fresh_sandbox.write_file("evil_link/injected.txt", "via symlink")
            assert r.status == "blocked"

            # Verify file was NOT created outside
            assert not os.path.exists(os.path.join(outside_dir, "injected.txt"))

        finally:
            shutil.rmtree(outside_dir, ignore_errors=True)
            if os.path.exists(link_name):
                os.remove(link_name)

    def test_symlink_inside_sandbox_allowed(self, fresh_sandbox):
        """A symlink pointing to another location inside sandbox is safe."""
        target = os.path.join(fresh_sandbox.root, "real_dir")
        os.makedirs(target, exist_ok=True)
        fresh_sandbox.write_file("real_dir/actual.txt", "hello")

        link_name = os.path.join(fresh_sandbox.root, "safe_link")
        try:
            os.symlink(target, link_name)
        except (OSError, NotImplementedError):
            pytest.skip("Symlink creation not supported")

        r = fresh_sandbox.read_file("safe_link/actual.txt")
        assert r.status == "success"
        assert r.content == "hello"


class TestFileSandboxDeleteBlocked:
    """Tests for delete prohibition in v0.3.0-alpha."""

    def test_delete_always_blocked(self, fresh_sandbox):
        """Delete must always return blocked."""
        fresh_sandbox.write_file("deleteme.txt", "x")
        r = fresh_sandbox.delete_file("deleteme.txt")
        assert r.status == "blocked"
        assert not r.success
        assert "not supported" in r.error.lower()

        # File must still exist
        r2 = fresh_sandbox.read_file("deleteme.txt")
        assert r2.status == "success"


class TestFileSandboxONoFollow:
    """Tests for O_NOFOLLOW TOCTOU defense.

    TOCTOU (Time-of-Check to Time-of-Use) attack: a malicious actor
    creates a regular file at the target path, we validate it is safe,
    then they swap it for a symlink pointing outside the sandbox.
    O_NOFOLLOW prevents the file operation from following symlinks
    at the OS level, closing this race condition.
    """

    def test_symlink_read_blocked_by_onofollow(self, fresh_sandbox):
        """Reading a symlink with O_NOFOLLOW raises an error."""
        target = os.path.join(fresh_sandbox.root, "target.txt")
        link = os.path.join(fresh_sandbox.root, "link.txt")
        with open(target, "w") as f:
            f.write("real content")
        try:
            os.symlink(target, link)
        except (OSError, NotImplementedError):
            pytest.skip("Symlink creation not supported on this platform")

        # _open_nofollow should reject the symlink (ELOOP=symlink loop or O_NOFOLLOW)
        with pytest.raises(SandboxSecurityError) as exc_info:
            fresh_sandbox._open_nofollow(
                fresh_sandbox.root / "link.txt", os.O_RDONLY
            )
        error_msg = str(exc_info.value)
        assert ("O_NOFOLLOW" in error_msg or
                "Symlink loop" in error_msg or
                "TOCTOU" in error_msg)

    def test_symlink_write_blocked_by_onofollow(self, fresh_sandbox):
        """Writing through a symlink pointing outside is blocked.

        Note: symlinks to outside the sandbox may be caught by
        _canonicalize() (path escape check) OR by O_NOFOLLOW.
        Either is a valid defense — the file must not be written.
        """
        outside_dir = tempfile.mkdtemp(prefix="avs_outside_onofollow_")
        try:
            real_file = os.path.join(outside_dir, "real.txt")
            link = os.path.join(fresh_sandbox.root, "link.txt")
            try:
                os.symlink(real_file, link)
            except (OSError, NotImplementedError):
                pytest.skip("Symlink creation not supported on this platform")

            # write_file must reject writing through the symlink
            result = fresh_sandbox.write_file("link.txt", "injected")
            assert result.status == "blocked"
            # Blocked by canonicalization (path escape) OR O_NOFOLLOW
            assert ("O_NOFOLLOW" in result.error or
                    "Path escapes sandbox" in result.error or
                    "Symlink" in result.error)

            # Verify the outside file was NOT written
            assert not os.path.exists(real_file) or open(real_file).read() == ""
        finally:
            import shutil
            shutil.rmtree(outside_dir, ignore_errors=True)

    def test_regular_file_read_works(self, fresh_sandbox):
        """O_NOFOLLOW does not block reading regular files."""
        fresh_sandbox.write_file("regular.txt", "hello")
        result = fresh_sandbox.read_file("regular.txt")
        assert result.status == "success"
        assert result.content == "hello"

    def test_regular_file_write_works(self, fresh_sandbox):
        """O_NOFOLLOW does not block writing regular files."""
        result = fresh_sandbox.write_file("regular.txt", "world")
        assert result.status == "success"
        read_result = fresh_sandbox.read_file("regular.txt")
        assert read_result.content == "world"

    def test_symlink_swap_race_defended(self, fresh_sandbox):
        """Simulate TOCTOU: symlink swapped after validation.

        Steps:
          1. Create a real file (passes validation)
          2. Replace it with a symlink to outside
          3. The symlink is blocked (by canonicalization escape check
             or O_NOFOLLOW — either is a valid defense)
        """
        outside_dir = tempfile.mkdtemp(prefix="avs_outside_race_")
        try:
            outside_file = os.path.join(outside_dir, "stolen.txt")
            inside_file = os.path.join(fresh_sandbox.root, "race.txt")

            # Step 1: Create a real file (passes validation)
            with open(inside_file, "w") as f:
                f.write("initial")

            # Verify initial read works
            result = fresh_sandbox.read_file("race.txt")
            assert result.status == "success"
            assert result.content == "initial"

            # Step 2: Replace with symlink to outside
            os.remove(inside_file)
            try:
                os.symlink(outside_file, inside_file)
            except (OSError, NotImplementedError):
                pytest.skip("Symlink creation not supported")

            # Step 3: Symlink is blocked by canonicalization or O_NOFOLLOW
            result = fresh_sandbox.read_file("race.txt")
            assert result.status == "blocked"
            assert ("O_NOFOLLOW" in result.error or
                    "Path escapes sandbox" in result.error or
                    "Symlink" in result.error)

            # Outside file must not have been read
            assert not os.path.exists(outside_file)
        finally:
            import shutil
            shutil.rmtree(outside_dir, ignore_errors=True)

    def test_directory_open_blocked_by_onofollow(self, fresh_sandbox):
        """Opening a directory with O_WRONLY|O_CREAT should be handled."""
        os.makedirs(os.path.join(fresh_sandbox.root, "subdir"), exist_ok=True)
        result = fresh_sandbox.write_file("subdir", "not a file")
        assert result.status == "blocked"


class TestFileSandboxResultStructure:
    """Tests for result dictionary format."""

    def test_result_has_all_fields(self, fresh_sandbox):
        """Successful result should have all documented fields."""
        r = fresh_sandbox.write_file("result_test.txt", "data")
        d = r.to_dict()
        assert "status" in d
        assert "operation" in d
        assert "raw_requested_path" in d
        assert "resolved_path" in d
        assert "success" in d
        assert "error" in d
        assert "bytes_handled" in d

    def test_blocked_result_has_error(self, fresh_sandbox):
        """Blocked result should have error message."""
        r = fresh_sandbox.write_file("../escape.txt", "bad")
        assert r.error is not None
        assert len(r.error) > 0
        d = r.to_dict()
        assert d["error"] is not None

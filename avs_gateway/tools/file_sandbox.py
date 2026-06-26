"""
file_sandbox.py -- Real file sandbox for AVS Gateway v0.3.0-alpha.

Provides read, write, and list operations within a strict sandbox boundary.
Every path is canonicalized before execution to prevent:

    - Path traversal (../../etc/passwd)
    - Absolute path escapes (C:\\Windows\\System32, /etc/passwd)
    - Symlink escapes (sandbox/link -> /tmp)

No file deletion in v0.3.0-alpha (safety constraint).
All blocked operations return structured error responses with raw_path
and resolved_path for audit/timeline evidence.
"""

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger("avs_gateway.tools.file_sandbox")


class SandboxSecurityError(Exception):
    """Raised when a sandbox security boundary is violated."""
    pass


@dataclass(frozen=True)
class SandboxResult:
    """Structured result from a sandbox file operation."""
    status: str           # "success" or "blocked"
    operation: str        # "read", "write", "list"
    raw_requested_path: str
    resolved_path: Optional[str]
    success: bool
    error: Optional[str] = None
    content: Optional[str] = None      # for reads
    bytes_handled: int = 0
    receipt_hash: Optional[str] = None  # set by caller

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "operation": self.operation,
            "raw_requested_path": self.raw_requested_path,
            "resolved_path": self.resolved_path,
            "success": self.success,
            "error": self.error,
            "bytes_handled": self.bytes_handled,
        }


class FileSandbox:
    """Secure file operations within a canonical sandbox boundary.

    Usage:
        sandbox = FileSandbox(root=Path("./sandbox"))
        result = sandbox.write_file("output.txt", "hello")
        result = sandbox.read_file("output.txt")
        blocked = sandbox.write_file("../../outside.txt", "evil")
        # blocked.status == "blocked", blocked.error explains why
    """

    DEFAULT_MAX_SIZE = 1_000_000  # 1 MB
    DEFAULT_EXTENSIONS: Set[str] = set()  # empty = no restriction

    def __init__(
        self,
        root,
        max_file_size: int = DEFAULT_MAX_SIZE,
        allowed_extensions: Optional[Set[str]] = None,
    ) -> None:
        if isinstance(root, str):
            root = Path(root)
        self._root = root.resolve()
        self._max_file_size = max_file_size
        self._allowed_extensions = allowed_extensions or self.DEFAULT_EXTENSIONS

        # Create sandbox directory if missing
        self._root.mkdir(parents=True, exist_ok=True)

        logger.info(
            "FileSandbox initialized: root=%s max_size=%d ext=%s",
            self._root, self._max_file_size, self._allowed_extensions,
        )

    # ------------------------------------------------------------------
    # Core: path canonicalization (the non-negotiable moat)
    # ------------------------------------------------------------------

    def _canonicalize(self, raw_path: str) -> Path:
        """Canonicalize a requested path against the sandbox boundary.

        Steps:
            1. Join raw path with sandbox root (handles relative paths)
            2. Resolve to absolute, following symlinks, removing ..
            3. Verify resolved path is inside sandbox root via relative_to

        Returns:
            Canonical Path inside sandbox.

        Raises:
            SandboxSecurityError: If path escapes the sandbox boundary.
        """
        # Step 1: join with sandbox root
        if os.path.isabs(raw_path):
            # Absolute paths: resolve them directly, then check boundary
            target = Path(raw_path)
        else:
            target = self._root / raw_path

        # Step 2: resolve to canonical (follows symlinks, removes ..)
        try:
            canonical = target.resolve()
        except (OSError, RuntimeError) as exc:
            raise SandboxSecurityError(f"Cannot resolve path: {exc}")

        # Step 3: boundary check using relative_to (NOT naive startswith)
        try:
            canonical.relative_to(self._root)
        except ValueError:
            raise SandboxSecurityError(
                f"Path escapes sandbox: raw='{raw_path}' resolved='{canonical}'"
            )

        return canonical

    def _check_extension(self, path: Path) -> None:
        """Check file extension against whitelist (if configured)."""
        if not self._allowed_extensions:
            return
        if path.suffix not in self._allowed_extensions:
            allowed = ", ".join(sorted(self._allowed_extensions))
            raise SandboxSecurityError(
                f"Extension '{path.suffix}' not allowed. Allowed: {allowed}"
            )

    def _check_size(self, size: int) -> None:
        """Check content size against max_file_size."""
        if size > self._max_file_size:
            raise SandboxSecurityError(
                f"Size {size} exceeds limit {self._max_file_size}"
            )

    def _open_nofollow(self, path: Path, flags: int) -> int:
        """Open a file without following symlinks.

        Uses O_NOFOLLOW where available and performs an explicit symlink
        check for platforms such as Windows where O_NOFOLLOW may not exist.
        This prevents TOCTOU-style symlink access from being silently allowed.
        """
        try:
            if path.is_symlink():
                raise SandboxSecurityError(
                    f"Symlink access blocked (TOCTOU defense): {path}"
                )
        except SandboxSecurityError:
            raise
        except OSError as exc:
            raise SandboxSecurityError(
                f"Cannot inspect path for symlink status: {path}: {exc}"
            )

        nofollow_flag = getattr(os, "O_NOFOLLOW", 0)
        try:
            fd = os.open(str(path), flags | nofollow_flag)
            return fd
        except OSError as exc:
            if exc.errno == 40:
                raise SandboxSecurityError(
                    f"Symlink loop detected (TOCTOU defense): {path}"
                )
            raise SandboxSecurityError(
                f"Cannot open file (O_NOFOLLOW): {path}: {exc}"
            )

    # ------------------------------------------------------------------
    # Public: read / write / list
    # ------------------------------------------------------------------

    def write_file(self, raw_path: str, content: str) -> SandboxResult:
        """Write content to a file inside the sandbox.

        Args:
            raw_path: Requested path (may contain .., symlinks, etc.)
            content: String content to write.

        Returns:
            SandboxResult with status "success" or "blocked".
        """
        try:
            canonical = self._canonicalize(raw_path)
            self._check_extension(canonical)
            content_bytes = content.encode("utf-8")
            self._check_size(len(content_bytes))

            # Ensure parent directories exist
            canonical.parent.mkdir(parents=True, exist_ok=True)

            # Write using O_NOFOLLOW to prevent TOCTOU symlink attacks
            fd = self._open_nofollow(
                canonical, os.O_WRONLY | os.O_CREAT | os.O_TRUNC
            )
            try:
                bytes_written = os.write(fd, content_bytes)
                if bytes_written != len(content_bytes):
                    raise SandboxSecurityError(
                        f"Partial write: {bytes_written}/{len(content_bytes)} bytes"
                    )
            finally:
                os.close(fd)

            return SandboxResult(
                status="success",
                operation="write",
                raw_requested_path=raw_path,
                resolved_path=str(canonical),
                success=True,
                bytes_handled=len(content_bytes),
            )

        except SandboxSecurityError as exc:
            return SandboxResult(
                status="blocked",
                operation="write",
                raw_requested_path=raw_path,
                resolved_path=None,
                success=False,
                error=str(exc),
            )

    def read_file(self, raw_path: str) -> SandboxResult:
        """Read content from a file inside the sandbox.

        Args:
            raw_path: Requested path.

        Returns:
            SandboxResult with content field set on success.
        """
        try:
            canonical = self._canonicalize(raw_path)
            self._check_extension(canonical)

            if not canonical.exists():
                return SandboxResult(
                    status="blocked",
                    operation="read",
                    raw_requested_path=raw_path,
                    resolved_path=str(canonical),
                    success=False,
                    error=f"File not found: {raw_path}",
                )

            if not canonical.is_file():
                return SandboxResult(
                    status="blocked",
                    operation="read",
                    raw_requested_path=raw_path,
                    resolved_path=str(canonical),
                    success=False,
                    error=f"Not a file: {raw_path}",
                )

            self._check_size(canonical.stat().st_size)

            # Read using O_NOFOLLOW to prevent TOCTOU symlink attacks
            fd = self._open_nofollow(canonical, os.O_RDONLY)
            try:
                content_bytes = os.read(fd, self._max_file_size)
                content = content_bytes.decode("utf-8", errors="replace")
            finally:
                os.close(fd)

            return SandboxResult(
                status="success",
                operation="read",
                raw_requested_path=raw_path,
                resolved_path=str(canonical),
                success=True,
                content=content,
                bytes_handled=len(content.encode("utf-8")),
            )

        except SandboxSecurityError as exc:
            return SandboxResult(
                status="blocked",
                operation="read",
                raw_requested_path=raw_path,
                resolved_path=None,
                success=False,
                error=str(exc),
            )

    def list_files(self, raw_path: str = ".") -> SandboxResult:
        """List files in a sandbox directory.

        Args:
            raw_path: Directory path (default: sandbox root).

        Returns:
            SandboxResult with content = newline-separated file list.
        """
        try:
            canonical = self._canonicalize(raw_path)

            if not canonical.exists():
                return SandboxResult(
                    status="blocked",
                    operation="list",
                    raw_requested_path=raw_path,
                    resolved_path=str(canonical),
                    success=False,
                    error=f"Directory not found: {raw_path}",
                )

            if not canonical.is_dir():
                return SandboxResult(
                    status="blocked",
                    operation="list",
                    raw_requested_path=raw_path,
                    resolved_path=str(canonical),
                    success=False,
                    error=f"Not a directory: {raw_path}",
                )

            names = sorted(
                str(p.relative_to(self._root))
                for p in canonical.iterdir()
            )
            return SandboxResult(
                status="success",
                operation="list",
                raw_requested_path=raw_path,
                resolved_path=str(canonical),
                success=True,
                content="\n".join(names) if names else "(empty)",
            )

        except SandboxSecurityError as exc:
            return SandboxResult(
                status="blocked",
                operation="list",
                raw_requested_path=raw_path,
                resolved_path=None,
                success=False,
                error=str(exc),
            )

    def delete_file(self, raw_path: str) -> SandboxResult:
        """File deletion -- NOT SUPPORTED in v0.3.0-alpha.

        Always returns blocked with a clear explanation.
        """
        return SandboxResult(
            status="blocked",
            operation="delete",
            raw_requested_path=raw_path,
            resolved_path=None,
            success=False,
            error="File deletion not supported in v0.3.0-alpha (safety constraint)",
        )

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def root(self) -> Path:
        """Return the canonical sandbox root path."""
        return self._root

    def get_stats(self) -> Dict[str, Any]:
        """Return sandbox statistics."""
        file_count = sum(1 for _ in self._root.rglob("*") if _.is_file())
        dir_count = sum(1 for _ in self._root.rglob("*") if _.is_dir())
        return {
            "root": str(self._root),
            "max_file_size": self._max_file_size,
            "allowed_extensions": sorted(self._allowed_extensions) if self._allowed_extensions else None,
            "file_count": file_count,
            "directory_count": dir_count,
        }


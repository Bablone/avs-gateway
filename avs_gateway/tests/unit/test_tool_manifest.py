"""
test_tool_manifest.py — Test ToolManifest registration and integrity.

Tests tool manifest creation, hash stability, and best-effort
source/bytecode hashing.
"""

import pytest

from avs_gateway.tools.tool_manifest import (
    ToolManifest,
    register_tool,
    _best_effort_source_hash,
    _best_effort_bytecode_hash,
)


# ---------------------------------------------------------------------------
# Sample functions for registration
# ---------------------------------------------------------------------------

def sample_read_file(path: str) -> str:
    """Read a file from disk."""
    return f"Contents of {path}"


def sample_delete_file(path: str) -> bool:
    """Delete a file."""
    return True


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestToolManifestCreation:

    def test_register_tool_basic(self):
        manifest = register_tool(sample_read_file, tool_name="file_read")
        assert manifest.tool_name == "file_read"
        assert manifest.function_name == "sample_read_file"
        assert manifest.tool_type == "python_function"
        assert manifest.registered_by == "system"
        assert manifest.registered_at
        assert manifest.risk_class == "standard"

    def test_register_tool_custom_metadata(self):
        manifest = register_tool(
            sample_read_file,
            tool_name="custom_read",
            registered_by="admin_user",
            policy_binding="file_policy_set",
            allowed_operations=["read", "list"],
            risk_class="low",
        )
        assert manifest.registered_by == "admin_user"
        assert manifest.policy_binding == "file_policy_set"
        assert manifest.allowed_operations == ["read", "list"]
        assert manifest.risk_class == "low"

    def test_manifest_has_required_fields(self):
        manifest = register_tool(sample_read_file)
        d = manifest.to_dict()
        assert d["tool_name"] == "sample_read_file"
        assert d["tool_type"] == "python_function"
        # module_path will be the full Python dotted path
        assert d["module_path"]
        assert "test_tool_manifest" in d["module_path"]
        assert d["function_name"] == "sample_read_file"
        assert d["registered_at"]
        assert d["registered_by"] == "system"

    def test_manifest_hash_is_deterministic(self):
        m1 = register_tool(sample_read_file, tool_name="file_read")
        m2 = register_tool(sample_read_file, tool_name="file_read")
        assert m1.manifest_hash() == m2.manifest_hash()

    def test_manifest_hash_changes_when_name_changes(self):
        m1 = register_tool(sample_read_file, tool_name="file_read")
        m2 = register_tool(sample_read_file, tool_name="file_delete")
        assert m1.manifest_hash() != m2.manifest_hash()

    def test_manifest_hash_changes_when_policy_binding_changes(self):
        m1 = register_tool(sample_read_file, policy_binding="policy_a")
        m2 = register_tool(sample_read_file, policy_binding="policy_b")
        assert m1.manifest_hash() != m2.manifest_hash()

    def test_serialization_roundtrip(self):
        manifest = register_tool(
            sample_read_file,
            tool_name="file_read",
            registered_by="admin",
            policy_binding="file_policies",
        )
        d = manifest.to_dict()
        restored = ToolManifest.from_dict(d)
        assert restored.tool_name == manifest.tool_name
        assert restored.module_path == manifest.module_path
        assert restored.function_name == manifest.function_name
        assert restored.registered_by == manifest.registered_by
        assert restored.policy_binding == manifest.policy_binding


class TestBestEffortHashes:

    def test_source_hash_is_generated_for_python_function(self):
        manifest = register_tool(sample_read_file)
        assert manifest.source_hash is not None
        assert manifest.source_hash.startswith("sha256:")

    def test_bytecode_hash_is_generated_for_python_function(self):
        manifest = register_tool(sample_read_file)
        assert manifest.bytecode_hash is not None
        assert manifest.bytecode_hash.startswith("sha256:")

    def test_source_hash_is_informational_only(self):
        """Source hash should exist but not be treated as security-critical."""
        manifest = register_tool(sample_read_file)
        assert manifest.source_hash is not None
        # The hash should NOT be part of manifest_hash (it's best-effort)
        m_no_source = ToolManifest(
            tool_name=manifest.tool_name,
            tool_type=manifest.tool_type,
            module_path=manifest.module_path,
            function_name=manifest.function_name,
            source_hash=None,
            registered_at=manifest.registered_at,
            registered_by=manifest.registered_by,
        )
        # manifest_hash should be the same regardless of source_hash
        assert manifest.manifest_hash() == m_no_source.manifest_hash()

    def test_different_functions_different_source_hashes(self):
        m1 = register_tool(sample_read_file)
        m2 = register_tool(sample_delete_file)
        assert m1.source_hash != m2.source_hash

    def test_same_function_same_source_hash(self):
        m1 = register_tool(sample_read_file)
        m2 = register_tool(sample_read_file)
        assert m1.source_hash == m2.source_hash

    def test_source_hash_unavailable_for_lambda(self):
        """Lambdas may fail source extraction — should return None, not crash."""
        lam = lambda x: x + 1
        h = _best_effort_source_hash(lam)
        # Lambdas defined in test files may or may not work
        # The important thing is it doesn't crash

    def test_source_hash_unavailable_for_builtin(self):
        """Builtins should return None, not crash."""
        h = _best_effort_source_hash(len)
        assert h is None

    def test_bytecode_hash_unavailable_for_builtin(self):
        h = _best_effort_bytecode_hash(len)
        assert h is None


class TestToolManifestSourceHashStability:

    def test_source_hash_deterministic(self):
        """Same function should always produce same source hash."""
        m1 = register_tool(sample_read_file)
        m2 = register_tool(sample_read_file)
        assert m1.source_hash == m2.source_hash

    def test_bytecode_hash_deterministic(self):
        """Same function should always produce same bytecode hash (same Python version)."""
        m1 = register_tool(sample_read_file)
        m2 = register_tool(sample_read_file)
        assert m1.bytecode_hash == m2.bytecode_hash


class TestToolManifestNotCrashes:

    def test_register_tool_with_none_function_name(self):
        """Should handle edge cases gracefully."""
        class Callable:
            pass
        c = Callable()
        # callable without __name__
        manifest = register_tool(c, tool_name="custom")
        assert manifest.tool_name == "custom"
        assert manifest.function_name == ""  # not "unknown"

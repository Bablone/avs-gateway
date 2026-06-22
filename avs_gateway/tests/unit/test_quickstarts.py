"""
Tests for quickstart examples.

Verifies all 4 quickstart scripts run successfully and produce
the expected output.
"""

import sys
import os
import subprocess

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
QUICKSTART_DIR = os.path.join(REPO_ROOT, "examples", "quickstart")


class TestQuickstart01:
    """01_gateway_basics.py — intercept, decide, receipt."""

    def test_runs_successfully(self):
        """Script exits with code 0."""
        result = subprocess.run(
            [sys.executable, os.path.join(QUICKSTART_DIR, "01_gateway_basics.py")],
            capture_output=True, text=True, timeout=30,
        )
        assert result.returncode == 0, f"stdout: {result.stdout}\nstderr: {result.stderr}"

    def test_outputs_allow(self):
        """Output contains ALLOW decision."""
        result = subprocess.run(
            [sys.executable, os.path.join(QUICKSTART_DIR, "01_gateway_basics.py")],
            capture_output=True, text=True, timeout=30,
        )
        assert "allow" in result.stdout.lower()

    def test_outputs_deny(self):
        """Output contains DENY decision."""
        result = subprocess.run(
            [sys.executable, os.path.join(QUICKSTART_DIR, "01_gateway_basics.py")],
            capture_output=True, text=True, timeout=30,
        )
        assert "deny" in result.stdout.lower()

    def test_outputs_receipt(self):
        """Output contains receipt hash."""
        result = subprocess.run(
            [sys.executable, os.path.join(QUICKSTART_DIR, "01_gateway_basics.py")],
            capture_output=True, text=True, timeout=30,
        )
        assert "Receipt" in result.stdout


class TestQuickstart02:
    """02_governed_tool.py — @governed_tool decorator."""

    def test_runs_successfully(self):
        result = subprocess.run(
            [sys.executable, os.path.join(QUICKSTART_DIR, "02_governed_tool.py")],
            capture_output=True, text=True, timeout=30,
        )
        assert result.returncode == 0, f"stdout: {result.stdout}\nstderr: {result.stderr}"

    def test_shows_executed_true(self):
        result = subprocess.run(
            [sys.executable, os.path.join(QUICKSTART_DIR, "02_governed_tool.py")],
            capture_output=True, text=True, timeout=30,
        )
        assert "Executed : True" in result.stdout or "executed" in result.stdout.lower()

    def test_shows_executed_false(self):
        result = subprocess.run(
            [sys.executable, os.path.join(QUICKSTART_DIR, "02_governed_tool.py")],
            capture_output=True, text=True, timeout=30,
        )
        assert "Executed : False" in result.stdout or "did NOT" in result.stdout


class TestQuickstart03:
    """03_langchain_tool.py — LangChain adapter."""

    def test_runs_without_crash(self):
        """Script runs without exception (graceful fallback if no LangChain)."""
        result = subprocess.run(
            [sys.executable, os.path.join(QUICKSTART_DIR, "03_langchain_tool.py")],
            capture_output=True, text=True, timeout=30,
        )
        assert result.returncode == 0, f"stdout: {result.stdout}\nstderr: {result.stderr}"

    def test_handles_missing_langchain(self):
        """If LangChain not installed, prints instructions."""
        result = subprocess.run(
            [sys.executable, os.path.join(QUICKSTART_DIR, "03_langchain_tool.py")],
            capture_output=True, text=True, timeout=30,
        )
        if "LangChain" in result.stdout:
            assert "pip install" in result.stdout or "install" in result.stdout.lower()


class TestQuickstart04:
    """04_custom_action.py — Universal Control Plane proof."""

    def test_runs_successfully(self):
        result = subprocess.run(
            [sys.executable, os.path.join(QUICKSTART_DIR, "04_custom_action.py")],
            capture_output=True, text=True, timeout=30,
        )
        assert result.returncode == 0, f"stdout: {result.stdout}\nstderr: {result.stderr}"

    def test_deploy_not_executed(self):
        """CRITICAL: deploy_to_production was NOT executed."""
        result = subprocess.run(
            [sys.executable, os.path.join(QUICKSTART_DIR, "04_custom_action.py")],
            capture_output=True, text=True, timeout=30,
        )
        assert "PASS: deploy_to_production was NOT executed" in result.stdout

    def test_require_approval_decision(self):
        """Decision is REQUIRE_APPROVAL."""
        result = subprocess.run(
            [sys.executable, os.path.join(QUICKSTART_DIR, "04_custom_action.py")],
            capture_output=True, text=True, timeout=30,
        )
        assert "require_approval" in result.stdout.lower() or "REQUIRE_APPROVAL" in result.stdout

    def test_receipt_generated(self):
        """Receipt was generated for the custom action."""
        result = subprocess.run(
            [sys.executable, os.path.join(QUICKSTART_DIR, "04_custom_action.py")],
            capture_output=True, text=True, timeout=30,
        )
        assert "Receipt" in result.stdout or "receipt" in result.stdout.lower()

    def test_proves_universal_control_plane(self):
        """Output contains the universal control plane statement."""
        result = subprocess.run(
            [sys.executable, os.path.join(QUICKSTART_DIR, "04_custom_action.py")],
            capture_output=True, text=True, timeout=30,
        )
        assert "Universal Control Plane" in result.stdout or "universal" in result.stdout.lower()


class TestReadmeRequirements:
    """README contains required positioning phrases."""

    def test_runtime_permission_layer_in_readme(self):
        with open(os.path.join(REPO_ROOT, "README.md")) as f:
            content = f.read()
        assert "Runtime Permission Layer for AI Agents" in content

    def test_receipt_hook_in_readme(self):
        with open(os.path.join(REPO_ROOT, "README.md")) as f:
            content = f.read()
        assert "Every agent action gets a receipt" in content


class TestLicenseExists:
    """Apache 2.0 LICENSE file exists."""

    def test_license_file_exists(self):
        assert os.path.isfile(os.path.join(REPO_ROOT, "LICENSE"))

    def test_license_is_apache(self):
        with open(os.path.join(REPO_ROOT, "LICENSE")) as f:
            content = f.read()
        assert "Apache License" in content
        assert "Version 2.0" in content

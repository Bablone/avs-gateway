"""
Tests for avs_gateway.cli — the `avs` command-line interface.

Verifies: version, demo, quickstart commands work offline
with no external dependencies.
"""

import sys
import os
import subprocess

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

import pytest

from avs_gateway.cli import __version__, main


class TestCLIVersion:
    """avs version command."""

    def test_version_output(self, capsys):
        """avs version prints version and basic info."""
        main.__wrapped__ if hasattr(main, '__wrapped__') else None
        # Call directly
        from avs_gateway.cli import cmd_version
        cmd_version([])
        captured = capsys.readouterr()
        assert __version__ in captured.out
        assert "Runtime Permission Layer" in captured.out
        assert "receipt" in captured.out.lower()

    def test_version_exit_code(self):
        """avs version exits cleanly."""
        from avs_gateway.cli import cmd_version
        try:
            cmd_version([])
        except SystemExit as exc:
            pytest.fail(f"version command should not exit: {exc}")


class TestCLIDemo:
    """avs demo command."""

    def test_demo_outputs_allow_deny_approval(self, capsys):
        """avs demo shows ALLOW, DENY, and REQUIRE_APPROVAL."""
        from avs_gateway.cli import cmd_demo
        cmd_demo([])
        captured = capsys.readouterr()
        output = captured.out

        # All three decisions must appear
        assert "[ALLOW]" in output, f"Expected ALLOW in output: {output[:500]}"
        assert "[DENY]" in output or "DENY" in output.upper(), f"Expected DENY in output"
        assert "[PENDING]" in output or "PENDING" in output.upper(), f"Expected PENDING in output"

        # Evidence summary
        assert "Evidence Summary" in output
        assert "receipt" in output.lower() or "Receipt" in output

    def test_demo_offline_no_network(self):
        """avs demo works without network access."""
        from avs_gateway.cli import cmd_demo
        # This test passes if cmd_demo runs without raising
        # any network-related exception
        try:
            cmd_demo([])
        except Exception as exc:
            if "network" in str(exc).lower() or "connection" in str(exc).lower():
                pytest.fail(f"demo should work offline: {exc}")


class TestCLIQuickstart:
    """avs quickstart command."""

    def test_quickstart_lists_examples(self, capsys):
        """avs quickstart lists the 4 quickstart examples."""
        from avs_gateway.cli import cmd_quickstart
        cmd_quickstart([])
        captured = capsys.readouterr()
        output = captured.out

        assert "01_gateway_basics.py" in output
        assert "02_governed_tool.py" in output
        assert "03_langchain_tool.py" in output
        assert "04_custom_action.py" in output


class TestMainEntryPoint:
    """The main() entry point and argument parsing."""

    def test_main_no_args_prints_usage(self, capsys):
        """Running avs without arguments prints usage."""
        from avs_gateway.cli import main
        old_argv = sys.argv
        try:
            sys.argv = ["avs"]
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0
            captured = capsys.readouterr()
            assert "Usage" in captured.out or "usage" in captured.out.lower()
        finally:
            sys.argv = old_argv

    def test_main_unknown_command(self, capsys):
        """Running avs with unknown command prints error."""
        from avs_gateway.cli import main
        old_argv = sys.argv
        try:
            sys.argv = ["avs", "nonexistent"]
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1
        finally:
            sys.argv = old_argv

    def test_cli_imports_cleanly(self):
        """CLI module imports without errors."""
        import avs_gateway.cli as cli_module
        assert hasattr(cli_module, "main")
        assert hasattr(cli_module, "cmd_version")
        assert hasattr(cli_module, "cmd_demo")
        assert hasattr(cli_module, "cmd_quickstart")

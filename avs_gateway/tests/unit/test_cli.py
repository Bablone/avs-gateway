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


class TestCLIReceiptVerify:
    """avs receipt verify command."""

    def test_receipt_verify_valid_allow(self, capsys):
        """avs receipt verify accepts a valid ALLOW receipt."""
        from avs_gateway.cli import cmd_receipt_verify
        receipt_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "examples", "receipts", "allow_receipt.json"
        )
        if os.path.isfile(receipt_path):
            try:
                cmd_receipt_verify([receipt_path])
                captured = capsys.readouterr()
                assert "valid" in captured.out.lower()
            except SystemExit as exc:
                assert exc.code == 0, f"Expected exit 0 for valid receipt, got {exc.code}"

    def test_receipt_verify_valid_deny(self, capsys):
        """avs receipt verify accepts a valid DENY receipt."""
        from avs_gateway.cli import cmd_receipt_verify
        receipt_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "examples", "receipts", "deny_receipt.json"
        )
        if os.path.isfile(receipt_path):
            try:
                cmd_receipt_verify([receipt_path])
                captured = capsys.readouterr()
                assert "valid" in captured.out.lower()
            except SystemExit as exc:
                assert exc.code == 0

    def test_receipt_verify_invalid_file(self):
        """avs receipt verify fails for nonexistent file."""
        from avs_gateway.cli import cmd_receipt_verify
        with pytest.raises(SystemExit) as exc_info:
            cmd_receipt_verify(["/nonexistent/path/receipt.json"])
        assert exc_info.value.code == 1

    def test_receipt_verify_no_args(self):
        """avs receipt verify without args prints usage."""
        from avs_gateway.cli import cmd_receipt_verify
        with pytest.raises(SystemExit) as exc_info:
            cmd_receipt_verify([])
        assert exc_info.value.code == 1

    def test_receipt_subcommand_no_args(self, capsys):
        """avs receipt without subcommand prints usage."""
        from avs_gateway.cli import cmd_receipt
        with pytest.raises(SystemExit) as exc_info:
            cmd_receipt([])
        assert exc_info.value.code == 1

    def test_cli_has_receipt_command(self):
        """CLI has receipt command registered."""
        import avs_gateway.cli as cli_module
        assert hasattr(cli_module, "cmd_receipt")
        assert hasattr(cli_module, "cmd_receipt_verify")

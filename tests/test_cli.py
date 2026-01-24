"""Tests for the CLI module.

This module tests:
- CLI commands: run, batch, validate, init
- Help text display
- Exit codes
- Dry-run mode
"""

import os
import tempfile
from pathlib import Path

import pytest
from click.testing import CliRunner

from ontoralph.cli import EXIT_FAILURE, EXIT_SUCCESS, main


@pytest.fixture
def runner() -> CliRunner:
    """Create a CLI test runner."""
    return CliRunner()


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test outputs."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


class TestMainCommand:
    """Tests for the main command group."""

    def test_help_shows_usage(self, runner: CliRunner) -> None:
        """Test that --help shows usage information (AC6.5)."""
        result = runner.invoke(main, ["--help"])

        assert result.exit_code == 0
        assert "OntoRalph" in result.output
        assert "Quick Start" in result.output
        assert "run" in result.output
        assert "batch" in result.output
        assert "validate" in result.output
        assert "init" in result.output

    def test_version_shows_version(self, runner: CliRunner) -> None:
        """Test that --version shows version."""
        result = runner.invoke(main, ["--version"])

        assert result.exit_code == 0
        assert "OntoRalph version" in result.output

    def test_no_command_shows_banner(self, runner: CliRunner) -> None:
        """Test that running without command shows banner."""
        result = runner.invoke(main, [])

        # Should show help, not fail
        assert result.exit_code == 0


class TestRunCommand:
    """Tests for the run command."""

    def test_run_help(self, runner: CliRunner) -> None:
        """Test run command help (AC6.5)."""
        result = runner.invoke(main, ["run", "--help"])

        assert result.exit_code == 0
        assert "--iri" in result.output
        assert "--label" in result.output
        assert "--parent" in result.output
        assert "--ice" in result.output
        assert "--dry-run" in result.output

    def test_run_requires_iri(self, runner: CliRunner) -> None:
        """Test that run requires --iri."""
        result = runner.invoke(
            main, ["run", "--label", "Test", "--parent", "owl:Thing"]
        )

        assert result.exit_code != 0
        assert "Missing option '--iri'" in result.output

    def test_run_dry_run(self, runner: CliRunner) -> None:
        """Test --dry-run produces no API calls (AC6.4)."""
        result = runner.invoke(
            main,
            [
                "run",
                "--iri",
                ":TestClass",
                "--label",
                "Test Class",
                "--parent",
                "owl:Thing",
                "--dry-run",
            ],
        )

        assert result.exit_code == EXIT_SUCCESS
        assert "Dry run mode" in result.output
        assert "Would process class" in result.output
        assert ":TestClass" in result.output

    def test_run_dry_run_with_siblings(self, runner: CliRunner) -> None:
        """Test dry-run shows siblings correctly."""
        result = runner.invoke(
            main,
            [
                "run",
                "--iri",
                ":TestClass",
                "--label",
                "Test Class",
                "--parent",
                "cco:ICE",
                "--siblings",
                ":Sibling1,:Sibling2",
                "--ice",
                "--dry-run",
            ],
        )

        assert result.exit_code == EXIT_SUCCESS
        assert ":Sibling1" in result.output
        assert ":Sibling2" in result.output

    def test_run_with_mock_provider(self, runner: CliRunner, temp_dir: Path) -> None:
        """Test run command processes single class end-to-end (AC6.1)."""
        output_file = temp_dir / "output.ttl"

        result = runner.invoke(
            main,
            [
                "run",
                "--iri",
                ":TestClass",
                "--label",
                "Test Class",
                "--parent",
                "cco:InformationContentEntity",
                "--ice",
                "--provider",
                "mock",
                "--output",
                str(output_file),
                "--format",
                "turtle",
            ],
        )

        # Command should complete (may pass or fail based on checklist)
        assert result.exit_code in [EXIT_SUCCESS, EXIT_FAILURE]
        # Output file should be created regardless
        assert output_file.exists()

        # Output should be valid Turtle
        content = output_file.read_text()
        assert "owl:Class" in content or "a owl:Class" in content

    def test_run_with_mock_json_format(self, runner: CliRunner) -> None:
        """Test run with JSON output format."""
        result = runner.invoke(
            main,
            [
                "run",
                "--iri",
                ":TestClass",
                "--label",
                "Test Class",
                "--parent",
                "owl:Thing",
                "--provider",
                "mock",
                "--format",
                "json",
            ],
        )

        # Should run (pass or fail)
        assert result.exit_code in [EXIT_SUCCESS, EXIT_FAILURE]
        assert '"class_info"' in result.output
        assert '"final_definition"' in result.output

    def test_run_with_mock_markdown_format(self, runner: CliRunner) -> None:
        """Test run with Markdown output format."""
        result = runner.invoke(
            main,
            [
                "run",
                "--iri",
                ":TestClass",
                "--label",
                "Test Class",
                "--parent",
                "owl:Thing",
                "--provider",
                "mock",
                "--format",
                "markdown",
            ],
        )

        # Should run (pass or fail)
        assert result.exit_code in [EXIT_SUCCESS, EXIT_FAILURE]
        assert "# Ralph Loop Report" in result.output

    def test_run_quiet_mode(self, runner: CliRunner) -> None:
        """Test run with --quiet flag."""
        result = runner.invoke(
            main,
            [
                "run",
                "--iri",
                ":TestClass",
                "--label",
                "Test Class",
                "--parent",
                "owl:Thing",
                "--provider",
                "mock",
                "--quiet",
            ],
        )

        # Should complete without crashing
        assert result.exit_code in [EXIT_SUCCESS, EXIT_FAILURE]
        # Should not have the summary table
        assert "Result Summary" not in result.output

    def test_run_without_api_key_fails(self, runner: CliRunner) -> None:
        """Test that run fails without API key for non-mock providers."""
        # Ensure no API key is set
        env = os.environ.copy()
        env.pop("ANTHROPIC_API_KEY", None)

        result = runner.invoke(
            main,
            [
                "run",
                "--iri",
                ":TestClass",
                "--label",
                "Test Class",
                "--parent",
                "owl:Thing",
                "--provider",
                "claude",
            ],
            env=env,
        )

        assert result.exit_code != EXIT_SUCCESS
        assert "ANTHROPIC_API_KEY" in result.output


class TestBatchCommand:
    """Tests for the batch command."""

    def test_batch_help(self, runner: CliRunner) -> None:
        """Test batch command help (AC6.5)."""
        result = runner.invoke(main, ["batch", "--help"])

        assert result.exit_code == 0
        assert "INPUT_FILE" in result.output
        assert "--output" in result.output
        assert "--continue-on-error" in result.output

    def test_batch_requires_input_file(self, runner: CliRunner) -> None:
        """Test that batch requires input file."""
        result = runner.invoke(main, ["batch"])

        assert result.exit_code != 0
        assert "Missing argument 'INPUT_FILE'" in result.output

    def test_batch_invalid_file(self, runner: CliRunner) -> None:
        """Test batch with non-existent file."""
        result = runner.invoke(main, ["batch", "nonexistent.yaml"])

        assert result.exit_code != 0

    def test_batch_with_yaml_file(self, runner: CliRunner, temp_dir: Path) -> None:
        """Test batch processes classes from YAML (AC6.2)."""
        # Create input YAML
        input_file = temp_dir / "classes.yaml"
        input_file.write_text("""\
classes:
  - iri: ":Class1"
    label: "Class 1"
    parent: "owl:Thing"
    is_ice: false

  - iri: ":Class2"
    label: "Class 2"
    parent: "owl:Thing"
    is_ice: false
""")

        output_dir = temp_dir / "results"

        result = runner.invoke(
            main,
            [
                "batch",
                str(input_file),
                "--output",
                str(output_dir),
                "--provider",
                "mock",
                "--format",
                "turtle",
            ],
        )

        # Should complete (success, partial, or failure)
        assert result.exit_code in [EXIT_SUCCESS, EXIT_FAILURE, 2]

        # Check output files created
        assert output_dir.exists()
        assert (output_dir / "SUMMARY.md").exists()

    def test_batch_invalid_yaml(self, runner: CliRunner, temp_dir: Path) -> None:
        """Test batch with invalid YAML."""
        input_file = temp_dir / "invalid.yaml"
        input_file.write_text("not: valid: yaml: {{")

        result = runner.invoke(main, ["batch", str(input_file)])

        assert result.exit_code != EXIT_SUCCESS
        assert "Failed to load YAML" in result.output

    def test_batch_missing_classes_key(self, runner: CliRunner, temp_dir: Path) -> None:
        """Test batch with YAML missing 'classes' key."""
        input_file = temp_dir / "missing.yaml"
        input_file.write_text("other_key: value")

        result = runner.invoke(main, ["batch", str(input_file)])

        assert result.exit_code != EXIT_SUCCESS
        assert "must contain a 'classes' key" in result.output


class TestValidateCommand:
    """Tests for the validate command."""

    def test_validate_help(self, runner: CliRunner) -> None:
        """Test validate command help (AC6.5)."""
        result = runner.invoke(main, ["validate", "--help"])

        assert result.exit_code == 0
        assert "DEFINITION" in result.output
        assert "--term" in result.output
        assert "--ice" in result.output

    def test_validate_passing_definition(self, runner: CliRunner) -> None:
        """Test validate with passing definition."""
        result = runner.invoke(
            main,
            [
                "validate",
                "An ICE that denotes an occurrent as specified in formal discourse.",
                "--ice",
            ],
        )

        # Check output contains status info
        assert "PASS" in result.output or "FAIL" in result.output
        assert "Result:" in result.output

    def test_validate_failing_definition(self, runner: CliRunner) -> None:
        """Test validate with failing definition."""
        result = runner.invoke(
            main,
            [
                "validate",
                "An ICE that represents something extracted from text.",
                "--ice",
            ],
        )

        # Should fail due to red flags
        assert result.exit_code == EXIT_FAILURE
        assert "FAIL" in result.output

    def test_validate_quiet_mode(self, runner: CliRunner) -> None:
        """Test validate with --quiet outputs only pass/fail."""
        result = runner.invoke(
            main,
            [
                "validate",
                "An ICE that denotes something.",
                "--ice",
                "--quiet",
            ],
        )

        # Output should be minimal
        output = result.output.strip()
        assert output in ["PASS", "FAIL"]

    def test_validate_verbose_mode(self, runner: CliRunner) -> None:
        """Test validate with --verbose shows all checks."""
        result = runner.invoke(
            main,
            [
                "validate",
                "An ICE that denotes something.",
                "--ice",
                "--verbose",
            ],
        )

        assert result.exit_code in [EXIT_SUCCESS, EXIT_FAILURE]
        # Should show checklist table
        assert "Checklist Results" in result.output
        # Check for actual check codes (column header may be truncated by Rich)
        assert "C1" in result.output or "I1" in result.output or "R1" in result.output

    def test_validate_with_term(self, runner: CliRunner) -> None:
        """Test validate with --term for circularity check."""
        result = runner.invoke(
            main,
            [
                "validate",
                "A verb phrase is a phrase containing a verb.",
                "--term",
                "Verb Phrase",
                "--no-ice",
            ],
        )

        # Should fail circularity check
        assert result.exit_code == EXIT_FAILURE


class TestInitCommand:
    """Tests for the init command."""

    def test_init_help(self, runner: CliRunner) -> None:
        """Test init command help (AC6.5)."""
        result = runner.invoke(main, ["init", "--help"])

        assert result.exit_code == 0
        assert "--output" in result.output
        assert "--force" in result.output

    def test_init_creates_files(self, runner: CliRunner, temp_dir: Path) -> None:
        """Test init creates config files."""
        result = runner.invoke(
            main,
            [
                "init",
                "--output",
                str(temp_dir),
            ],
        )

        assert result.exit_code == 0
        assert "Created files" in result.output

        # Check files exist
        assert (temp_dir / "ontoralph.yaml").exists()
        assert (temp_dir / "classes.yaml").exists()

        # Check content
        config = (temp_dir / "ontoralph.yaml").read_text()
        assert "provider: claude" in config

        classes = (temp_dir / "classes.yaml").read_text()
        assert "classes:" in classes

    def test_init_skips_existing(self, runner: CliRunner, temp_dir: Path) -> None:
        """Test init skips existing files without --force."""
        # Create existing file
        (temp_dir / "ontoralph.yaml").write_text("existing content")

        result = runner.invoke(
            main,
            [
                "init",
                "--output",
                str(temp_dir),
            ],
        )

        assert result.exit_code == 0
        assert "Skipping" in result.output

        # Content should be preserved
        assert (temp_dir / "ontoralph.yaml").read_text() == "existing content"

    def test_init_force_overwrites(self, runner: CliRunner, temp_dir: Path) -> None:
        """Test init --force overwrites existing files."""
        # Create existing file
        (temp_dir / "ontoralph.yaml").write_text("existing content")

        result = runner.invoke(
            main,
            [
                "init",
                "--output",
                str(temp_dir),
                "--force",
            ],
        )

        assert result.exit_code == 0
        assert "Created files" in result.output

        # Content should be overwritten
        assert (temp_dir / "ontoralph.yaml").read_text() != "existing content"


class TestExitCodes:
    """Tests for CLI exit codes."""

    def test_exit_success_on_pass(self, runner: CliRunner) -> None:
        """Test exit code 0 on success (AC6.6)."""
        # Use a definition that should pass all checks
        result = runner.invoke(
            main,
            [
                "validate",
                "An ICE that denotes a concept as formally specified in discourse.",
                "--ice",
                "--quiet",
            ],
        )

        # This definition should pass
        assert result.exit_code == EXIT_SUCCESS

    def test_exit_failure_on_fail(self, runner: CliRunner) -> None:
        """Test exit code 1 on failure (AC6.6)."""
        result = runner.invoke(
            main,
            [
                "validate",
                "An ICE that represents something extracted.",
                "--ice",
                "--quiet",
            ],
        )

        assert result.exit_code == EXIT_FAILURE


class TestIntegration:
    """Integration tests combining multiple CLI features."""

    def test_full_workflow_mock(self, runner: CliRunner, temp_dir: Path) -> None:
        """Test full workflow with mock provider."""
        # 1. Init project
        result = runner.invoke(main, ["init", "--output", str(temp_dir)])
        assert result.exit_code == 0

        # 2. Run single class (may pass or fail based on checklist)
        result = runner.invoke(
            main,
            [
                "run",
                "--iri",
                ":TestClass",
                "--label",
                "Test Class",
                "--parent",
                "owl:Thing",
                "--provider",
                "mock",
                "--output",
                str(temp_dir / "test.ttl"),
            ],
        )
        assert result.exit_code in [EXIT_SUCCESS, EXIT_FAILURE]
        assert (temp_dir / "test.ttl").exists()

        # 3. Batch process
        classes_file = temp_dir / "classes.yaml"
        result = runner.invoke(
            main,
            [
                "batch",
                str(classes_file),
                "--output",
                str(temp_dir / "batch_results"),
                "--provider",
                "mock",
            ],
        )
        # May have partial success
        assert result.exit_code in [EXIT_SUCCESS, EXIT_FAILURE, 2]

    def test_verbose_shows_progress(self, runner: CliRunner) -> None:
        """Test verbose mode shows iteration progress."""
        result = runner.invoke(
            main,
            [
                "run",
                "--iri",
                ":TestClass",
                "--label",
                "Test Class",
                "--parent",
                "owl:Thing",
                "--provider",
                "mock",
                "--verbose",
            ],
        )

        assert result.exit_code in [EXIT_SUCCESS, EXIT_FAILURE]
        # Verbose output should include more details
        assert "IRI:" in result.output or "Result Summary" in result.output


class TestProviderSelection:
    """Tests for provider selection and API key handling."""

    def test_unknown_provider_fails(self, runner: CliRunner) -> None:
        """Test that unknown provider raises error."""
        result = runner.invoke(
            main,
            [
                "run",
                "--iri",
                ":TestClass",
                "--label",
                "Test Class",
                "--parent",
                "owl:Thing",
                "--provider",
                "invalid_provider",
            ],
        )

        assert result.exit_code != 0
        # Click validates the provider choice
        assert "invalid_provider" in result.output
        assert "is not one of" in result.output

    def test_claude_without_api_key(self, runner: CliRunner) -> None:
        """Test claude provider without API key fails gracefully."""
        # Ensure API key is not set
        env = os.environ.copy()
        env.pop("ANTHROPIC_API_KEY", None)

        result = runner.invoke(
            main,
            [
                "run",
                "--iri",
                ":TestClass",
                "--label",
                "Test Class",
                "--parent",
                "owl:Thing",
                "--provider",
                "claude",
            ],
            env=env,
        )

        assert result.exit_code != 0
        assert "ANTHROPIC_API_KEY" in result.output

    def test_openai_without_api_key(self, runner: CliRunner) -> None:
        """Test openai provider without API key fails gracefully."""
        # Ensure API key is not set
        env = os.environ.copy()
        env.pop("OPENAI_API_KEY", None)

        result = runner.invoke(
            main,
            [
                "run",
                "--iri",
                ":TestClass",
                "--label",
                "Test Class",
                "--parent",
                "owl:Thing",
                "--provider",
                "openai",
            ],
            env=env,
        )

        assert result.exit_code != 0
        assert "OPENAI_API_KEY" in result.output


class TestOutputFormats:
    """Tests for different output format options."""

    def test_run_with_json_format(self, runner: CliRunner, temp_dir: Path) -> None:
        """Test JSON output format."""
        output_file = temp_dir / "result.json"

        result = runner.invoke(
            main,
            [
                "run",
                "--iri",
                ":TestClass",
                "--label",
                "Test Class",
                "--parent",
                "owl:Thing",
                "--provider",
                "mock",
                "--format",
                "json",
                "--output",
                str(output_file),
            ],
        )

        assert result.exit_code in [EXIT_SUCCESS, EXIT_FAILURE]
        assert output_file.exists()
        content = output_file.read_text()
        assert "{" in content  # JSON-like

    def test_run_with_markdown_format(self, runner: CliRunner, temp_dir: Path) -> None:
        """Test Markdown output format."""
        output_file = temp_dir / "result.md"

        result = runner.invoke(
            main,
            [
                "run",
                "--iri",
                ":TestClass",
                "--label",
                "Test Class",
                "--parent",
                "owl:Thing",
                "--provider",
                "mock",
                "--format",
                "markdown",
                "--output",
                str(output_file),
            ],
        )

        assert result.exit_code in [EXIT_SUCCESS, EXIT_FAILURE]
        assert output_file.exists()
        content = output_file.read_text()
        assert "#" in content  # Markdown headers

    def test_run_with_turtle_format(self, runner: CliRunner, temp_dir: Path) -> None:
        """Test Turtle output format."""
        output_file = temp_dir / "result.ttl"

        result = runner.invoke(
            main,
            [
                "run",
                "--iri",
                ":TestClass",
                "--label",
                "Test Class",
                "--parent",
                "owl:Thing",
                "--provider",
                "mock",
                "--format",
                "turtle",
                "--output",
                str(output_file),
            ],
        )

        assert result.exit_code in [EXIT_SUCCESS, EXIT_FAILURE]
        assert output_file.exists()
        content = output_file.read_text()
        assert "@prefix" in content or "TestClass" in content

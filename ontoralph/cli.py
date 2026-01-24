"""Command-line interface for OntoRalph.

This module provides the main CLI entry point for OntoRalph,
implementing commands for single-class and batch processing.
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import Any

import click
import yaml
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.table import Table
from rich.text import Text

from ontoralph import __version__
from ontoralph.core.checklist import ChecklistEvaluator
from ontoralph.core.loop import LoopConfig, LoopHooks, RalphLoop
from ontoralph.core.models import CheckResult, ClassInfo, LoopResult, VerifyStatus
from ontoralph.llm import ClaudeProvider, MockProvider, OpenAIProvider
from ontoralph.output import ReportGenerator, TurtleGenerator

console = Console()
error_console = Console(stderr=True)

# Exit codes
EXIT_SUCCESS = 0
EXIT_FAILURE = 1
EXIT_PARTIAL = 2


def print_banner() -> None:
    """Print the OntoRalph banner."""
    banner = Text()
    banner.append("OntoRalph", style="bold cyan")
    banner.append(" v" + __version__, style="dim")
    banner.append("\n")
    banner.append(
        "Iterative definition refinement for BFO/CCO ontologies", style="italic"
    )

    console.print(Panel(banner, border_style="cyan", padding=(0, 2)))


def get_llm_provider(provider: str, model: str | None = None) -> Any:
    """Get the appropriate LLM provider.

    Args:
        provider: Provider name ('claude', 'openai', 'mock').
        model: Optional model override.

    Returns:
        LLM provider instance.

    Raises:
        click.ClickException: If provider is invalid or API key missing.
    """
    if provider == "mock":
        return MockProvider()

    if provider == "claude":
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise click.ClickException(
                "ANTHROPIC_API_KEY environment variable not set. "
                "Set it or use --provider mock for testing."
            )
        return ClaudeProvider(api_key=api_key, model=model)

    if provider == "openai":
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise click.ClickException(
                "OPENAI_API_KEY environment variable not set. "
                "Set it or use --provider mock for testing."
            )
        return OpenAIProvider(api_key=api_key, model=model)

    raise click.ClickException(f"Unknown provider: {provider}")


def create_progress_hooks(progress: Progress, task_id: Any, verbose: bool) -> LoopHooks:
    """Create loop hooks for progress display.

    Args:
        progress: Rich progress instance.
        task_id: Progress task ID.
        verbose: Whether to show verbose output.

    Returns:
        LoopHooks instance.
    """

    def on_iteration_start(iteration: int, _state: Any) -> None:
        progress.update(task_id, description=f"[cyan]Iteration {iteration}[/cyan]")

    def on_generate(definition: str) -> None:
        if verbose:
            console.print(f"  [dim]Generated:[/dim] {definition[:80]}...")

    def on_critique(_status: VerifyStatus, results: list[CheckResult]) -> None:
        failed = [r for r in results if not r.passed]
        if verbose and failed:
            console.print(f"  [dim]Issues found:[/dim] {len(failed)}")

    def on_verify(status: VerifyStatus, _results: list[CheckResult]) -> None:
        if status == VerifyStatus.PASS:
            progress.update(task_id, description="[green]Passed[/green]")
        elif status == VerifyStatus.FAIL:
            progress.update(task_id, description="[red]Failed[/red]")
        else:
            progress.update(task_id, description="[yellow]Iterating[/yellow]")

    return LoopHooks(
        on_iteration_start=on_iteration_start,
        on_generate=on_generate,
        on_verify=on_verify,
    )


def output_result(
    result: LoopResult,
    format: str,
    output_path: str | None,
    quiet: bool = False,
) -> None:
    """Output the loop result in the specified format.

    Args:
        result: The loop result.
        format: Output format ('turtle', 'markdown', 'json').
        output_path: Output file path, or None for stdout.
        quiet: If True, suppress info messages.
    """
    if format == "turtle":
        turtle_gen = TurtleGenerator()
        content = turtle_gen.generate_from_result(result)
    elif format == "markdown":
        report_gen = ReportGenerator()
        content = report_gen.generate_markdown(result)
    elif format == "json":
        json_gen = ReportGenerator()
        content = json_gen.generate_json(result)
    else:
        raise click.ClickException(f"Unknown format: {format}")

    if output_path:
        Path(output_path).write_text(content, encoding="utf-8")
        if not quiet:
            console.print(f"[green]Output written to:[/green] {output_path}")
    else:
        console.print(content)


def print_result_summary(result: LoopResult) -> None:
    """Print a summary table of the result.

    Args:
        result: The loop result.
    """
    table = Table(title="Result Summary", show_header=True)
    table.add_column("Property", style="cyan")
    table.add_column("Value")

    status_style = "green" if result.converged else "red"
    table.add_row(
        "Status", f"[{status_style}]{result.status.value.upper()}[/{status_style}]"
    )
    table.add_row("Iterations", str(result.total_iterations))
    table.add_row("Duration", f"{result.duration_seconds:.2f}s")
    table.add_row("Final Definition", result.final_definition)

    console.print(table)


@click.group(invoke_without_command=True)
@click.option("--version", "-V", is_flag=True, help="Show version and exit.")
@click.pass_context
def main(ctx: click.Context, version: bool) -> None:
    """OntoRalph: Iterative definition refinement for BFO/CCO ontologies.

    Implements the Ralph Loop technique: Generate -> Critique -> Refine -> Verify
    until rigorous quality standards are met.

    \b
    Quick Start:
      ontoralph run --iri ":MyClass" --parent "cco:ICE" --label "My Class"
      ontoralph batch classes.yaml --output results/
      ontoralph validate "An ICE that represents something"

    \b
    Documentation:
      https://ontoralph.github.io/ontoralph
    """
    if version:
        console.print(f"OntoRalph version {__version__}")
        ctx.exit(0)

    if ctx.invoked_subcommand is None:
        print_banner()
        console.print()
        console.print(ctx.get_help())


@main.command()
@click.option(
    "--iri",
    required=True,
    help="The IRI of the class, e.g., ':VerbPhrase'",
)
@click.option(
    "--label",
    required=True,
    help="Human-readable label, e.g., 'Verb Phrase'",
)
@click.option(
    "--parent",
    required=True,
    help="Parent class IRI, e.g., 'cco:InformationContentEntity'",
)
@click.option(
    "--siblings",
    default="",
    help="Comma-separated sibling IRIs, e.g., ':NounPhrase,:DiscourseReferent'",
)
@click.option(
    "--ice/--no-ice",
    default=False,
    help="Whether this is an Information Content Entity",
)
@click.option(
    "--definition",
    default=None,
    help="Current definition to improve (optional)",
)
@click.option(
    "--max-iterations",
    default=5,
    type=click.IntRange(1, 10),
    help="Maximum iterations before giving up",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    help="Output file path (default: stdout)",
)
@click.option(
    "--format",
    "-f",
    type=click.Choice(["turtle", "markdown", "json"]),
    default="turtle",
    help="Output format",
)
@click.option(
    "--provider",
    "-p",
    type=click.Choice(["claude", "openai", "mock"]),
    default="claude",
    help="LLM provider to use",
)
@click.option(
    "--model",
    "-m",
    default=None,
    help="Model to use (provider-specific)",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Show detailed progress",
)
@click.option(
    "--quiet",
    "-q",
    is_flag=True,
    help="Suppress non-essential output",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would happen without making API calls",
)
def run(
    iri: str,
    label: str,
    parent: str,
    siblings: str,
    ice: bool,
    definition: str | None,
    max_iterations: int,
    output: str | None,
    format: str,
    provider: str,
    model: str | None,
    verbose: bool,
    quiet: bool,
    dry_run: bool,
) -> None:
    """Process a single class through the Ralph Loop.

    \b
    Example:
      ontoralph run \\
        --iri ":VerbPhrase" \\
        --label "Verb Phrase" \\
        --parent "cco:InformationContentEntity" \\
        --siblings ":NounPhrase,:DiscourseReferent" \\
        --ice \\
        --definition "An ICE representing a verb phrase."
    """
    # Parse siblings
    sibling_list = [s.strip() for s in siblings.split(",") if s.strip()]

    # Create ClassInfo
    class_info = ClassInfo(
        iri=iri,
        label=label,
        parent_class=parent,
        sibling_classes=sibling_list,
        is_ice=ice,
        current_definition=definition,
    )

    if verbose and not quiet:
        console.print(f"[dim]IRI:[/dim] {iri}")
        console.print(f"[dim]Label:[/dim] {label}")
        console.print(f"[dim]Parent:[/dim] {parent}")
        console.print(f"[dim]Siblings:[/dim] {sibling_list}")
        console.print(f"[dim]Is ICE:[/dim] {ice}")
        console.print(f"[dim]Provider:[/dim] {provider}")
        console.print(f"[dim]Max iterations:[/dim] {max_iterations}")
        console.print()

    if dry_run:
        console.print("[yellow]Dry run mode - no API calls will be made[/yellow]")
        console.print()
        console.print("Would process class with the following configuration:")
        console.print(f"  IRI: {iri}")
        console.print(f"  Label: {label}")
        console.print(f"  Parent: {parent}")
        console.print(f"  Siblings: {sibling_list}")
        console.print(f"  Is ICE: {ice}")
        console.print(f"  Current definition: {definition or '(none)'}")
        console.print(f"  Provider: {provider}")
        console.print(f"  Max iterations: {max_iterations}")
        console.print(f"  Output format: {format}")
        sys.exit(EXIT_SUCCESS)

    # Get LLM provider
    llm = get_llm_provider(provider, model)

    # Create loop config
    config = LoopConfig(max_iterations=max_iterations)

    # Run the loop
    async def run_loop() -> LoopResult:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            TimeElapsedColumn(),
            console=console,
            transient=not verbose,
        ) as progress:
            task_id = progress.add_task(
                f"[cyan]Processing {label}...[/cyan]",
                total=None,
            )

            hooks = create_progress_hooks(progress, task_id, verbose)
            loop = RalphLoop(llm=llm, config=config, hooks=hooks)

            return await loop.run(class_info)

    try:
        result = asyncio.run(run_loop())

        if not quiet:
            print_result_summary(result)
            console.print()

        output_result(result, format, output, quiet)

        sys.exit(EXIT_SUCCESS if result.converged else EXIT_FAILURE)

    except Exception as e:
        error_console.print(f"[red]Error:[/red] {e}")
        if verbose:
            import traceback

            error_console.print(traceback.format_exc())
        sys.exit(EXIT_FAILURE)


@main.command()
@click.argument("input_file", type=click.Path(exists=True))
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    default="./results",
    help="Output directory for results",
)
@click.option(
    "--format",
    "-f",
    type=click.Choice(["turtle", "markdown", "json"]),
    default="turtle",
    help="Output format",
)
@click.option(
    "--provider",
    "-p",
    type=click.Choice(["claude", "openai", "mock"]),
    default="claude",
    help="LLM provider to use",
)
@click.option(
    "--model",
    "-m",
    default=None,
    help="Model to use (provider-specific)",
)
@click.option(
    "--max-iterations",
    default=5,
    type=click.IntRange(1, 10),
    help="Maximum iterations per class",
)
@click.option(
    "--continue-on-error",
    is_flag=True,
    help="Continue processing if a class fails",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Show detailed progress",
)
@click.option(
    "--quiet",
    "-q",
    is_flag=True,
    help="Suppress non-essential output",
)
@click.option(
    "--validate-output",
    is_flag=True,
    help="Validate output against BFO/CCO patterns",
)
@click.option(
    "--order-by-dependency",
    is_flag=True,
    help="Process classes in dependency order (parents first)",
)
@click.option(
    "--check-siblings",
    is_flag=True,
    help="Check sibling exclusivity after processing",
)
def batch(
    input_file: str,
    output: str,
    format: str,
    provider: str,
    model: str | None,
    max_iterations: int,
    continue_on_error: bool,
    verbose: bool,
    quiet: bool,
    validate_output: bool,
    order_by_dependency: bool,
    check_siblings: bool,
) -> None:
    """Process multiple classes from a YAML file.

    \b
    Example:
      ontoralph batch classes.yaml --output results/

    \b
    Input file format (YAML):
      classes:
        - iri: ":VerbPhrase"
          label: "Verb Phrase"
          parent: "cco:InformationContentEntity"
          siblings: [":NounPhrase", ":DiscourseReferent"]
          is_ice: true
          definition: "An ICE representing a verb phrase."
    """
    # Load YAML file
    try:
        with open(input_file, encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except Exception as e:
        raise click.ClickException(f"Failed to load YAML file: {e}") from e

    if "classes" not in data:
        raise click.ClickException("YAML file must contain a 'classes' key")

    classes_data = data["classes"]
    if not isinstance(classes_data, list):
        raise click.ClickException("'classes' must be a list")

    # Parse class info
    classes: list[ClassInfo] = []
    for i, item in enumerate(classes_data):
        try:
            classes.append(
                ClassInfo(
                    iri=item["iri"],
                    label=item["label"],
                    parent_class=item.get(
                        "parent", item.get("parent_class", "owl:Thing")
                    ),
                    sibling_classes=item.get(
                        "siblings", item.get("sibling_classes", [])
                    ),
                    is_ice=item.get("is_ice", False),
                    current_definition=item.get(
                        "definition", item.get("current_definition")
                    ),
                )
            )
        except Exception as e:
            raise click.ClickException(f"Invalid class at index {i}: {e}") from e

    # Order by dependency if requested
    if order_by_dependency:
        from ontoralph.batch import order_by_dependency as do_order

        try:
            classes = do_order(classes)
            if not quiet:
                console.print("[dim]Classes ordered by dependency[/dim]")
        except ValueError as e:
            raise click.ClickException(f"Dependency ordering failed: {e}") from e

    if not quiet:
        console.print(f"[dim]Input file:[/dim] {input_file}")
        console.print(f"[dim]Output directory:[/dim] {output}")
        console.print(f"[dim]Classes to process:[/dim] {len(classes)}")
        console.print()

    # Create output directory
    output_dir = Path(output)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Get LLM provider
    llm = get_llm_provider(provider, model)
    config = LoopConfig(max_iterations=max_iterations)

    # Process classes
    results: list[LoopResult] = []
    failed_count = 0

    async def process_class(
        class_info: ClassInfo, progress: Progress, task_id: Any
    ) -> LoopResult | None:
        hooks = create_progress_hooks(progress, task_id, verbose)
        loop = RalphLoop(llm=llm, config=config, hooks=hooks)
        return await loop.run(class_info)

    async def run_batch() -> None:
        nonlocal failed_count

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            for class_info in classes:
                task_id = progress.add_task(
                    f"[cyan]Processing {class_info.label}...[/cyan]",
                    total=None,
                )

                try:
                    result = await process_class(class_info, progress, task_id)
                    if result:
                        results.append(result)
                        progress.update(
                            task_id,
                            description=f"[green]{class_info.label}: PASS[/green]"
                            if result.converged
                            else f"[red]{class_info.label}: FAIL[/red]",
                        )
                        if not result.converged:
                            failed_count += 1
                except Exception as e:
                    failed_count += 1
                    progress.update(
                        task_id,
                        description=f"[red]{class_info.label}: ERROR - {e}[/red]",
                    )
                    if not continue_on_error:
                        raise

    try:
        asyncio.run(run_batch())
    except Exception as e:
        error_console.print(f"[red]Error:[/red] {e}")
        if verbose:
            import traceback

            error_console.print(traceback.format_exc())

    # Write individual results
    ext = {"turtle": ".ttl", "markdown": ".md", "json": ".json"}[format]

    for result in results:
        # Create safe filename from IRI
        safe_name = result.class_info.iri.replace(":", "_").replace("/", "_")
        output_path = output_dir / f"{safe_name}{ext}"
        output_result(result, format, str(output_path), quiet=True)

    # Write summary report
    from ontoralph.output import BatchReportGenerator

    batch_gen = BatchReportGenerator()
    summary = batch_gen.generate_summary_markdown(results)
    (output_dir / "SUMMARY.md").write_text(summary, encoding="utf-8")

    # Check sibling exclusivity if requested
    sibling_issues: list[Any] = []
    if check_siblings and results:
        from ontoralph.batch import SiblingExclusivityChecker

        checker = SiblingExclusivityChecker()
        sibling_issues = checker.check_from_results(results)

        if sibling_issues and not quiet:
            console.print()
            console.print("[yellow]Sibling Exclusivity Issues:[/yellow]")
            for issue in sibling_issues:
                console.print(f"  • {issue.message}")

    # Validate output if requested
    validation_issues: list[Any] = []
    if validate_output and results:
        from rdflib import Graph

        from ontoralph.batch import BatchIntegrityChecker, TurtleValidator
        from ontoralph.output import TurtleGenerator

        # Generate combined graph
        gen = TurtleGenerator()
        combined_turtle = gen.generate_batch(
            [(r.class_info, r.final_definition) for r in results]
        )

        graph = Graph()
        graph.parse(data=combined_turtle, format="turtle")

        # Run validators
        turtle_validator = TurtleValidator()
        validation_issues = turtle_validator.validate(graph)

        integrity_checker = BatchIntegrityChecker()
        dup_labels, punning, ns_issues = integrity_checker.check_all(graph)

        if not quiet and (validation_issues or dup_labels or punning):
            console.print()
            console.print("[yellow]Output Validation Issues:[/yellow]")

            for val_issue in validation_issues:
                severity_color = (
                    "red" if val_issue.severity.value == "violation" else "yellow"
                )
                console.print(
                    f"  [{severity_color}]{val_issue.severity.value.upper()}[/{severity_color}] {val_issue.message}"
                )

            for dup_issue in dup_labels:
                console.print(f"  [yellow]WARNING[/yellow] {dup_issue.message}")

            for pun_issue in punning:
                console.print(f"  [red]VIOLATION[/red] {pun_issue.message}")

    # Print summary
    if not quiet:
        console.print()
        table = Table(title="Batch Results", show_header=True)
        table.add_column("Metric", style="cyan")
        table.add_column("Value")

        passed = len(results) - failed_count
        table.add_row("Total Classes", str(len(classes)))
        table.add_row("Processed", str(len(results)))
        table.add_row("Passed", f"[green]{passed}[/green]")
        table.add_row("Failed", f"[red]{failed_count}[/red]")
        if check_siblings:
            table.add_row(
                "Sibling Issues",
                f"[yellow]{len(sibling_issues)}[/yellow]"
                if sibling_issues
                else "[green]0[/green]",
            )
        if validate_output:
            table.add_row(
                "Validation Issues",
                f"[yellow]{len(validation_issues)}[/yellow]"
                if validation_issues
                else "[green]0[/green]",
            )
        table.add_row("Output Directory", str(output_dir))

        console.print(table)

    # Exit code
    if failed_count == 0:
        sys.exit(EXIT_SUCCESS)
    elif failed_count < len(classes):
        sys.exit(EXIT_PARTIAL)
    else:
        sys.exit(EXIT_FAILURE)


@main.command()
@click.argument("definition")
@click.option(
    "--term",
    default=None,
    help="The term being defined (for circularity check)",
)
@click.option(
    "--ice/--no-ice",
    default=True,
    help="Whether this is an ICE definition",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Show detailed check results",
)
@click.option(
    "--quiet",
    "-q",
    is_flag=True,
    help="Only output pass/fail status",
)
def validate(
    definition: str,
    term: str | None,
    ice: bool,
    verbose: bool,
    quiet: bool,
) -> None:
    """Validate a definition against the checklist without refinement.

    \b
    Example:
      ontoralph validate "An ICE that is about an occurrent as introduced in discourse"
      ontoralph validate "An ICE that represents something" --term "Verb Phrase"

    \b
    Exit codes:
      0 - Definition passes all checks
      1 - Definition fails one or more checks
    """
    # Run checklist evaluation
    evaluator = ChecklistEvaluator()
    results = evaluator.evaluate(
        definition=definition,
        term=term or "Unknown",
        is_ice=ice,
        parent_class="owl:Thing",
    )
    status = evaluator.determine_status(results, ice)

    failed = [r for r in results if not r.passed]
    passed = [r for r in results if r.passed]

    if quiet:
        # Just output pass/fail
        console.print("PASS" if status == VerifyStatus.PASS else "FAIL")
        sys.exit(EXIT_SUCCESS if status == VerifyStatus.PASS else EXIT_FAILURE)

    # Print results table
    if verbose:
        table = Table(title="Checklist Results", show_header=True)
        table.add_column("Code", style="cyan", width=6)
        table.add_column("Check", width=30)
        table.add_column("Status", width=8)
        table.add_column("Evidence", width=40)

        for result in results:
            status_str = "[green]PASS[/green]" if result.passed else "[red]FAIL[/red]"
            table.add_row(
                result.code,
                result.name,
                status_str,
                result.evidence[:40] + "..."
                if len(result.evidence) > 40
                else result.evidence,
            )

        console.print(table)
    else:
        # Just show failed checks
        if failed:
            console.print("[red]Failed checks:[/red]")
            for result in failed:
                console.print(
                    f"  [{result.severity.value}] {result.code} {result.name}"
                )
                console.print(f"    {result.evidence}")
        else:
            console.print("[green]All checks passed![/green]")

    console.print()
    console.print(f"[bold]Result:[/bold] {status.value.upper()}")
    console.print(f"  Passed: {len(passed)}, Failed: {len(failed)}")

    sys.exit(EXIT_SUCCESS if status == VerifyStatus.PASS else EXIT_FAILURE)


@main.command()
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    default=".",
    help="Directory to create files in",
)
@click.option(
    "--force",
    is_flag=True,
    help="Overwrite existing files",
)
def init(output: str, force: bool) -> None:
    """Initialize a new OntoRalph project with sample files.

    Creates:
      - ontoralph.yaml (configuration)
      - classes.yaml (sample batch input)
    """
    output_dir = Path(output)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Sample configuration file
    config_content = """\
# OntoRalph Configuration
# See documentation for all options

llm:
  # LLM provider: claude, openai, or mock
  provider: claude
  # Model to use (optional, uses provider default if not specified)
  # model: claude-sonnet-4-20250514

loop:
  # Maximum iterations before giving up
  max_iterations: 5
  # Stop immediately if red flags are found
  fail_fast_on_red_flags: true
  # Use hybrid checking (automated + LLM)
  use_hybrid_checking: true

output:
  # Default output format: turtle, markdown, or json
  format: turtle
  # Include comments in Turtle output
  include_comments: true

# Custom checklist rules (optional)
# checklist:
#   custom_rules:
#     - name: "No jargon"
#       pattern: "\\\\b(NLP|ML|AI)\\\\b"
#       message: "Avoid technical jargon in definitions"
#       severity: quality
"""

    # Sample classes file
    classes_content = """\
# OntoRalph Batch Input
# Define classes to process through the Ralph Loop

classes:
  - iri: ":VerbPhrase"
    label: "Verb Phrase"
    parent: "cco:InformationContentEntity"
    siblings:
      - ":NounPhrase"
      - ":DiscourseReferent"
    is_ice: true
    definition: "An ICE representing a verb phrase."

  - iri: ":NounPhrase"
    label: "Noun Phrase"
    parent: "cco:InformationContentEntity"
    siblings:
      - ":VerbPhrase"
      - ":DiscourseReferent"
    is_ice: true
    definition: "An ICE representing a noun phrase."

  - iri: ":EventDescription"
    label: "Event Description"
    parent: "cco:InformationContentEntity"
    siblings:
      - ":ActionDescription"
      - ":StateDescription"
    is_ice: true
    # No initial definition - will be generated from scratch
"""

    config_path = output_dir / "ontoralph.yaml"
    classes_path = output_dir / "classes.yaml"

    files_created = []

    # Write config file
    if config_path.exists() and not force:
        console.print(
            f"[yellow]Skipping {config_path} (already exists, use --force to overwrite)[/yellow]"
        )
    else:
        config_path.write_text(config_content, encoding="utf-8")
        files_created.append(config_path)

    # Write classes file
    if classes_path.exists() and not force:
        console.print(
            f"[yellow]Skipping {classes_path} (already exists, use --force to overwrite)[/yellow]"
        )
    else:
        classes_path.write_text(classes_content, encoding="utf-8")
        files_created.append(classes_path)

    if files_created:
        console.print("[green]Created files:[/green]")
        for path in files_created:
            console.print(f"  {path}")

        console.print()
        console.print("[dim]Next steps:[/dim]")
        console.print("  1. Set your API key: export ANTHROPIC_API_KEY=your-key")
        console.print(
            "  2. Run a single class: ontoralph run --iri ':VerbPhrase' --label 'Verb Phrase' --parent 'cco:ICE' --ice"
        )
        console.print("  3. Or run batch: ontoralph batch classes.yaml")
    else:
        console.print("[yellow]No files created (all already exist)[/yellow]")


if __name__ == "__main__":
    main()

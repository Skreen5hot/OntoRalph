"""Command-line interface for OntoRalph.

This module provides the main CLI entry point for OntoRalph,
implementing commands for single-class and batch processing.
"""

import click
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from ontoralph import __version__

console = Console()


def print_banner() -> None:
    """Print the OntoRalph banner."""
    banner = Text()
    banner.append("OntoRalph", style="bold cyan")
    banner.append(" v" + __version__, style="dim")
    banner.append("\n")
    banner.append("Iterative definition refinement for BFO/CCO ontologies", style="italic")

    console.print(Panel(banner, border_style="cyan", padding=(0, 2)))


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
    "--verbose",
    "-v",
    is_flag=True,
    help="Show detailed progress",
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
    verbose: bool,
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

    if verbose:
        console.print(f"[dim]IRI:[/dim] {iri}")
        console.print(f"[dim]Label:[/dim] {label}")
        console.print(f"[dim]Parent:[/dim] {parent}")
        console.print(f"[dim]Siblings:[/dim] {sibling_list}")
        console.print(f"[dim]Is ICE:[/dim] {ice}")
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
        console.print(f"  Max iterations: {max_iterations}")
        console.print(f"  Output format: {format}")
        return

    # Placeholder for actual implementation
    console.print(
        "[yellow]Ralph Loop execution will be implemented in Phase 4[/yellow]"
    )


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
def batch(
    input_file: str,
    output: str,
    format: str,
    continue_on_error: bool,
    verbose: bool,
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
    console.print(f"[dim]Input file:[/dim] {input_file}")
    console.print(f"[dim]Output directory:[/dim] {output}")
    console.print(f"[dim]Format:[/dim] {format}")
    console.print()

    # Placeholder for actual implementation
    console.print(
        "[yellow]Batch processing will be implemented in Phase 6[/yellow]"
    )


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
def validate(
    definition: str,
    term: str | None,
    ice: bool,
    verbose: bool,
) -> None:
    """Validate a definition against the checklist without refinement.

    \b
    Example:
      ontoralph validate "An ICE that is about an occurrent as introduced in discourse"
    """
    console.print(f"[dim]Definition:[/dim] {definition}")
    console.print(f"[dim]Is ICE:[/dim] {ice}")
    if term:
        console.print(f"[dim]Term:[/dim] {term}")
    console.print()

    # Placeholder for actual implementation
    console.print(
        "[yellow]Validation will be implemented in Phase 2[/yellow]"
    )


@main.command()
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    default=".",
    help="Directory to create files in",
)
def init(output: str) -> None:
    """Initialize a new OntoRalph project with sample files.

    Creates:
      - ontoralph.yaml (configuration)
      - classes.yaml (sample batch input)
    """
    console.print(f"[dim]Output directory:[/dim] {output}")
    console.print()

    # Placeholder for actual implementation
    console.print(
        "[yellow]Project initialization will be implemented in Phase 8[/yellow]"
    )


if __name__ == "__main__":
    main()

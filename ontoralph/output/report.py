"""Report generation for OntoRalph.

This module generates human-readable reports of the Ralph Loop execution
in Markdown, HTML, and JSON formats.
"""

import json
from typing import Any

from ontoralph.core.models import (
    CheckResult,
    LoopIteration,
    LoopResult,
    Severity,
    VerifyStatus,
)
from ontoralph.output.turtle import TurtleDiff


class ReportGenerator:
    """Generates reports of Ralph Loop execution.

    Supports Markdown, HTML, and JSON output formats with
    configurable detail levels.
    """

    # Status indicators
    STATUS_ICONS = {
        VerifyStatus.PASS: "PASS",
        VerifyStatus.FAIL: "FAIL",
        VerifyStatus.ITERATE: "ITERATE",
    }

    CHECK_ICONS = {
        True: "[x]",  # Passed
        False: "[ ]",  # Failed
    }

    SEVERITY_LABELS = {
        Severity.REQUIRED: "Required",
        Severity.ICE_REQUIRED: "ICE Required",
        Severity.QUALITY: "Quality",
        Severity.RED_FLAG: "Red Flag",
    }

    def __init__(
        self,
        include_timestamps: bool = True,
        include_evidence: bool = True,
        show_all_checks: bool = True,
    ) -> None:
        """Initialize the report generator.

        Args:
            include_timestamps: Whether to include timestamps in reports.
            include_evidence: Whether to include evidence for each check.
            show_all_checks: If False, only show failed checks.
        """
        self.include_timestamps = include_timestamps
        self.include_evidence = include_evidence
        self.show_all_checks = show_all_checks
        self._diff = TurtleDiff()

    def generate_markdown(self, result: LoopResult) -> str:
        """Generate a Markdown report of the loop execution.

        Args:
            result: The completed loop result.

        Returns:
            Markdown-formatted report.
        """
        lines = []

        # Header
        lines.append(f"# Ralph Loop Report: {result.class_info.label}")
        lines.append("")

        # Summary section
        lines.append("## Summary")
        lines.append("")
        lines.append(f"- **Class IRI**: `{result.class_info.iri}`")
        lines.append(f"- **Status**: **{self.STATUS_ICONS[result.status]}**")
        lines.append(f"- **Iterations**: {result.total_iterations}")
        lines.append(f"- **Converged**: {'Yes' if result.converged else 'No'}")
        lines.append(f"- **Duration**: {result.duration_seconds:.2f}s")

        if self.include_timestamps:
            lines.append(f"- **Started**: {result.started_at.isoformat()}")
            lines.append(f"- **Completed**: {result.completed_at.isoformat()}")

        lines.append("")

        # Class info
        lines.append("## Class Information")
        lines.append("")
        lines.append(f"- **Parent Class**: `{result.class_info.parent_class}`")
        lines.append(f"- **Is ICE**: {'Yes' if result.class_info.is_ice else 'No'}")

        if result.class_info.sibling_classes:
            siblings = ", ".join(f"`{s}`" for s in result.class_info.sibling_classes)
            lines.append(f"- **Siblings**: {siblings}")

        if result.class_info.current_definition:
            lines.append(
                f"- **Initial Definition**: {result.class_info.current_definition}"
            )

        lines.append("")

        # Final definition
        lines.append("## Final Definition")
        lines.append("")
        lines.append(f"> {result.final_definition}")
        lines.append("")

        # Iteration details
        lines.append("## Iteration History")
        lines.append("")

        for iteration in result.iterations:
            lines.extend(self._format_iteration_markdown(iteration))
            lines.append("")

        # Definition evolution
        if len(result.iterations) > 1:
            lines.append("## Definition Evolution")
            lines.append("")
            lines.extend(self._format_evolution_markdown(result))
            lines.append("")

        return "\n".join(lines)

    def generate_summary(self, result: LoopResult) -> str:
        """Generate a brief summary of the loop result.

        Args:
            result: The completed loop result.

        Returns:
            One-line summary string.
        """
        status = self.STATUS_ICONS[result.status]
        return (
            f"{result.class_info.label}: {status} "
            f"({result.total_iterations} iteration{'s' if result.total_iterations != 1 else ''}, "
            f"{result.duration_seconds:.1f}s)"
        )

    def generate_json(self, result: LoopResult) -> str:
        """Generate a JSON report of the loop execution.

        Args:
            result: The completed loop result.

        Returns:
            JSON-formatted report string.
        """
        data = self._result_to_dict(result)
        return json.dumps(data, indent=2, default=str)

    def generate_html(self, result: LoopResult) -> str:
        """Generate an HTML report of the loop execution.

        Args:
            result: The completed loop result.

        Returns:
            HTML-formatted report string.
        """
        status_class = result.status.value
        status_label = self.STATUS_ICONS[result.status]

        html_parts = [
            "<!DOCTYPE html>",
            "<html>",
            "<head>",
            f"<title>Ralph Loop Report: {result.class_info.label}</title>",
            "<style>",
            self._get_html_styles(),
            "</style>",
            "</head>",
            "<body>",
            f"<h1>Ralph Loop Report: {result.class_info.label}</h1>",
            "",
            "<div class='summary'>",
            "<h2>Summary</h2>",
            f"<p><strong>Class IRI:</strong> <code>{result.class_info.iri}</code></p>",
            f"<p><strong>Status:</strong> <span class='status {status_class}'>{status_label}</span></p>",
            f"<p><strong>Iterations:</strong> {result.total_iterations}</p>",
            f"<p><strong>Converged:</strong> {'Yes' if result.converged else 'No'}</p>",
            f"<p><strong>Duration:</strong> {result.duration_seconds:.2f}s</p>",
            "</div>",
            "",
            "<div class='final-definition'>",
            "<h2>Final Definition</h2>",
            f"<blockquote>{result.final_definition}</blockquote>",
            "</div>",
            "",
            "<div class='iterations'>",
            "<h2>Iteration History</h2>",
        ]

        for iteration in result.iterations:
            html_parts.extend(self._format_iteration_html(iteration))

        html_parts.extend(
            [
                "</div>",
                "</body>",
                "</html>",
            ]
        )

        return "\n".join(html_parts)

    def _format_iteration_markdown(self, iteration: LoopIteration) -> list[str]:
        """Format a single iteration for Markdown output.

        Args:
            iteration: The iteration to format.

        Returns:
            List of Markdown lines.
        """
        lines = []

        status = self.STATUS_ICONS[iteration.verify_status]
        lines.append(f"### Iteration {iteration.iteration_number} - {status}")
        lines.append("")

        if self.include_timestamps:
            lines.append(f"*{iteration.timestamp.isoformat()}*")
            lines.append("")

        # Generated definition
        lines.append("**Generated Definition:**")
        lines.append(f"> {iteration.generated_definition}")
        lines.append("")

        # Refined definition (if different)
        if (
            iteration.refined_definition
            and iteration.refined_definition != iteration.generated_definition
        ):
            lines.append("**Refined Definition:**")
            lines.append(f"> {iteration.refined_definition}")
            lines.append("")

        # Checklist results
        lines.append("**Checklist Results:**")
        lines.append("")

        # Group by severity
        by_severity = self._group_checks_by_severity(iteration.critique_results)

        for severity, checks in by_severity.items():
            if checks:
                lines.append(f"*{self.SEVERITY_LABELS[severity]}:*")
                for check in checks:
                    if self.show_all_checks or not check.passed:
                        icon = self.CHECK_ICONS[check.passed]
                        line = f"- {icon} **{check.code}** {check.name}"
                        if self.include_evidence and check.evidence:
                            line += f": {check.evidence}"
                        lines.append(line)
                lines.append("")

        return lines

    def _format_iteration_html(self, iteration: LoopIteration) -> list[str]:
        """Format a single iteration for HTML output.

        Args:
            iteration: The iteration to format.

        Returns:
            List of HTML lines.
        """
        status_class = iteration.verify_status.value
        status_label = self.STATUS_ICONS[iteration.verify_status]

        lines = [
            f"<div class='iteration {status_class}'>",
            f"<h3>Iteration {iteration.iteration_number} - <span class='status {status_class}'>{status_label}</span></h3>",
        ]

        if self.include_timestamps:
            lines.append(f"<p class='timestamp'>{iteration.timestamp.isoformat()}</p>")

        lines.append("<p><strong>Definition:</strong></p>")
        lines.append(f"<blockquote>{iteration.final_definition}</blockquote>")

        # Checklist table
        lines.append("<table class='checklist'>")
        lines.append(
            "<tr><th>Check</th><th>Name</th><th>Status</th><th>Evidence</th></tr>"
        )

        for check in iteration.critique_results:
            if self.show_all_checks or not check.passed:
                status_icon = "&#x2713;" if check.passed else "&#x2717;"
                status_td = "passed" if check.passed else "failed"
                lines.append(
                    f"<tr class='{status_td}'>"
                    f"<td>{check.code}</td>"
                    f"<td>{check.name}</td>"
                    f"<td class='{status_td}'>{status_icon}</td>"
                    f"<td>{check.evidence}</td>"
                    f"</tr>"
                )

        lines.append("</table>")
        lines.append("</div>")

        return lines

    def _format_evolution_markdown(self, result: LoopResult) -> list[str]:
        """Format definition evolution across iterations.

        Args:
            result: The loop result.

        Returns:
            List of Markdown lines.
        """
        lines = []

        for i in range(len(result.iterations) - 1):
            prev = result.iterations[i]
            curr = result.iterations[i + 1]

            lines.append(
                f"### Iteration {prev.iteration_number} -> {curr.iteration_number}"
            )
            lines.append("")

            diff_text = self._diff.format_diff_text(
                prev.final_definition, curr.generated_definition
            )
            lines.append("```")
            lines.append(diff_text)
            lines.append("```")
            lines.append("")

        return lines

    def _group_checks_by_severity(
        self, checks: list[CheckResult]
    ) -> dict[Severity, list[CheckResult]]:
        """Group check results by severity.

        Args:
            checks: List of check results.

        Returns:
            Dictionary mapping severity to checks.
        """
        result: dict[Severity, list[CheckResult]] = {
            Severity.RED_FLAG: [],
            Severity.REQUIRED: [],
            Severity.ICE_REQUIRED: [],
            Severity.QUALITY: [],
        }

        for check in checks:
            result[check.severity].append(check)

        return result

    def _result_to_dict(self, result: LoopResult) -> dict[str, Any]:
        """Convert a LoopResult to a dictionary for JSON serialization.

        Args:
            result: The loop result.

        Returns:
            Dictionary representation.
        """
        return {
            "class_info": {
                "iri": result.class_info.iri,
                "label": result.class_info.label,
                "parent_class": result.class_info.parent_class,
                "sibling_classes": result.class_info.sibling_classes,
                "is_ice": result.class_info.is_ice,
                "current_definition": result.class_info.current_definition,
            },
            "final_definition": result.final_definition,
            "status": result.status.value,
            "converged": result.converged,
            "total_iterations": result.total_iterations,
            "duration_seconds": result.duration_seconds,
            "started_at": result.started_at.isoformat(),
            "completed_at": result.completed_at.isoformat(),
            "iterations": [
                {
                    "iteration_number": it.iteration_number,
                    "generated_definition": it.generated_definition,
                    "refined_definition": it.refined_definition,
                    "final_definition": it.final_definition,
                    "verify_status": it.verify_status.value,
                    "timestamp": it.timestamp.isoformat(),
                    "critique_results": [
                        {
                            "code": check.code,
                            "name": check.name,
                            "passed": check.passed,
                            "evidence": check.evidence,
                            "severity": check.severity.value,
                        }
                        for check in it.critique_results
                    ],
                }
                for it in result.iterations
            ],
        }

    def _get_html_styles(self) -> str:
        """Get CSS styles for HTML reports.

        Returns:
            CSS style string.
        """
        return """
body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    max-width: 900px;
    margin: 0 auto;
    padding: 20px;
    line-height: 1.6;
}
h1, h2, h3 { color: #333; }
code {
    background: #f4f4f4;
    padding: 2px 6px;
    border-radius: 3px;
}
blockquote {
    border-left: 4px solid #0066cc;
    margin: 10px 0;
    padding: 10px 20px;
    background: #f9f9f9;
}
.status {
    padding: 4px 12px;
    border-radius: 4px;
    font-weight: bold;
}
.status.pass { background: #d4edda; color: #155724; }
.status.fail { background: #f8d7da; color: #721c24; }
.status.iterate { background: #fff3cd; color: #856404; }
.iteration {
    border: 1px solid #ddd;
    border-radius: 8px;
    padding: 15px;
    margin: 15px 0;
}
.iteration.pass { border-left: 4px solid #28a745; }
.iteration.fail { border-left: 4px solid #dc3545; }
.iteration.iterate { border-left: 4px solid #ffc107; }
.checklist {
    width: 100%;
    border-collapse: collapse;
    margin: 10px 0;
}
.checklist th, .checklist td {
    border: 1px solid #ddd;
    padding: 8px;
    text-align: left;
}
.checklist th { background: #f4f4f4; }
.checklist .passed { color: #28a745; }
.checklist .failed { color: #dc3545; }
.timestamp { color: #666; font-size: 0.9em; }
"""


class BatchReportGenerator:
    """Generates consolidated reports for batch processing."""

    def __init__(self, report_generator: ReportGenerator | None = None) -> None:
        """Initialize the batch report generator.

        Args:
            report_generator: ReportGenerator instance to use for individual reports.
        """
        self.report_generator = report_generator or ReportGenerator()

    def generate_summary_markdown(self, results: list[LoopResult]) -> str:
        """Generate a summary report for multiple results.

        Args:
            results: List of loop results.

        Returns:
            Markdown summary report.
        """
        lines = ["# Batch Processing Summary", ""]

        # Statistics
        total = len(results)
        passed = sum(1 for r in results if r.converged)
        failed = total - passed

        lines.append("## Statistics")
        lines.append("")
        lines.append(f"- **Total Classes**: {total}")
        lines.append(f"- **Passed**: {passed} ({100 * passed / total:.1f}%)")
        lines.append(f"- **Failed**: {failed} ({100 * failed / total:.1f}%)")

        total_iterations = sum(r.total_iterations for r in results)
        total_duration = sum(r.duration_seconds for r in results)

        lines.append(f"- **Total Iterations**: {total_iterations}")
        lines.append(f"- **Average Iterations**: {total_iterations / total:.1f}")
        lines.append(f"- **Total Duration**: {total_duration:.1f}s")
        lines.append("")

        # Results
        lines.append("## Results")
        lines.append("")

        for result in results:
            status = "PASS" if result.converged else "FAIL"
            lines.append(
                f"### [{status}] {result.class_info.label} (`{result.class_info.iri}`)"
            )
            lines.append("")

            if result.class_info.current_definition:
                lines.append("**Original Definition:**  ")
                lines.append(f'"{result.class_info.current_definition}"')
                lines.append("")

            lines.append("**Ralph:**  ")
            lines.append(f"> {result.final_definition}")
            lines.append("")

            # Show failed checks for FAIL results
            if not result.converged and result.iterations:
                last = result.iterations[-1]
                failed_checks = [c for c in last.critique_results if not c.passed]
                if failed_checks:
                    lines.append("**Failed Checks:**")
                    for check in failed_checks:
                        lines.append(
                            f"- **{check.code}** {check.name}: {check.evidence}"
                        )
                    lines.append("")

        return "\n".join(lines)

    def generate_json(self, results: list[LoopResult]) -> str:
        """Generate a JSON report for multiple results.

        Args:
            results: List of loop results.

        Returns:
            JSON report string.
        """
        data = {
            "summary": {
                "total": len(results),
                "passed": sum(1 for r in results if r.converged),
                "failed": sum(1 for r in results if not r.converged),
                "total_iterations": sum(r.total_iterations for r in results),
                "total_duration_seconds": sum(r.duration_seconds for r in results),
            },
            "results": [self.report_generator._result_to_dict(r) for r in results],
        }
        return json.dumps(data, indent=2, default=str)

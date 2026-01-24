"""Definition validation endpoints."""

from fastapi import APIRouter, HTTPException, status

from ontoralph.core.checklist import ChecklistEvaluator
from ontoralph.core.models import CheckResult
from ontoralph.web.models import (
    CheckResultResponse,
    ValidateBatchRequest,
    ValidateBatchResponse,
    ValidateComparisonItem,
    ValidateRequest,
    ValidateResponse,
)

router = APIRouter(tags=["validate"])


def check_result_to_response(result: CheckResult) -> CheckResultResponse:
    """Convert a CheckResult to the API response model."""
    return CheckResultResponse(
        code=result.code,
        name=result.name,
        passed=result.passed,
        severity=result.severity.value,
        evidence=result.evidence,
    )


def evaluate_definition(
    definition: str,
    term: str,
    is_ice: bool,
    evaluator: ChecklistEvaluator,
) -> tuple[str, list[CheckResultResponse], int, int]:
    """Evaluate a single definition.

    Returns:
        Tuple of (status, results, passed_count, failed_count)
    """
    results = evaluator.evaluate(
        definition=definition,
        term=term,
        is_ice=is_ice,
        parent_class="owl:Thing",  # Not needed for validation
    )
    status = evaluator.determine_status(results, is_ice=is_ice)

    response_results = [check_result_to_response(r) for r in results]
    passed = sum(1 for r in results if r.passed)
    failed = sum(1 for r in results if not r.passed)

    return status.value, response_results, passed, failed


@router.post("/validate", response_model=ValidateResponse | ValidateBatchResponse)
async def validate_definition(
    request: ValidateRequest | ValidateBatchRequest,
) -> ValidateResponse | ValidateBatchResponse:
    """Validate one or more definitions against the checklist.

    For single definition:
        Provide `definition`, `term`, and `is_ice` fields.

    For batch comparison:
        Provide `definitions` list with multiple items to compare.

    No LLM is used - this is purely checklist-based validation.
    """
    evaluator = ChecklistEvaluator()

    # Check if this is a batch request
    if isinstance(request, ValidateBatchRequest):
        # Batch comparison mode
        comparisons = []

        for item in request.definitions:
            if not item.definition or not item.definition.strip():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Definition for '{item.label}' cannot be empty",
                )

            status_val, results, passed, failed = evaluate_definition(
                definition=item.definition,
                term=item.term,
                is_ice=item.is_ice,
                evaluator=evaluator,
            )

            comparisons.append(
                ValidateComparisonItem(
                    label=item.label,
                    status=status_val,
                    passed_count=passed,
                    failed_count=failed,
                    results=results,
                )
            )

        return ValidateBatchResponse(comparisons=comparisons)

    else:
        # Single definition mode
        if not request.definition or not request.definition.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Definition cannot be empty",
            )

        status_val, results, passed, failed = evaluate_definition(
            definition=request.definition,
            term=request.term,
            is_ice=request.is_ice,
            evaluator=evaluator,
        )

        return ValidateResponse(
            status=status_val,
            results=results,
            passed_count=passed,
            failed_count=failed,
        )

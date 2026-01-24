"""Ralph Loop execution endpoints."""

import asyncio
import contextlib
import json
import logging
from collections.abc import AsyncGenerator
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request, status
from sse_starlette.sse import EventSourceResponse

from ontoralph.core.loop import LoopConfig, LoopHooks, RalphLoop
from ontoralph.core.models import (
    CheckResult,
    ClassInfo,
    LoopIteration,
    LoopResult,
    LoopState,
    VerifyStatus,
)
from ontoralph.llm import ClaudeProvider, MockProvider, OpenAIProvider
from ontoralph.web.models import (
    CheckResultResponse,
    ErrorCode,
    IterationSummary,
    RunRequest,
    RunResponse,
)
from ontoralph.web.routes.validate import check_result_to_response
from ontoralph.web.session_store import get_session_store

router = APIRouter(tags=["run"])
logger = logging.getLogger(__name__)


def get_llm_provider(provider: str, api_key: str | None) -> Any:
    """Create an LLM provider instance.

    Args:
        provider: Provider name ('claude', 'openai', 'mock')
        api_key: API key (not needed for mock)

    Returns:
        LLM provider instance

    Raises:
        HTTPException: If provider is invalid or API key is missing
    """
    if provider == "mock":
        return MockProvider()

    if not api_key or not api_key.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"API key is required for provider '{provider}'",
        )

    if provider == "claude":
        return ClaudeProvider(api_key=api_key)
    elif provider == "openai":
        return OpenAIProvider(api_key=api_key)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid provider: {provider}. Must be 'claude', 'openai', or 'mock'",
        )


def loop_result_to_response(result: LoopResult) -> RunResponse:
    """Convert a LoopResult to the API response model."""
    iterations = []
    for it in result.iterations:
        iterations.append(
            IterationSummary(
                iteration=it.iteration_number,
                definition=it.final_definition,
                status=it.verify_status.value,
                failed_checks=[c.code for c in it.critique_results if not c.passed],
            )
        )

    # Get final checks from last iteration
    final_checks: list[CheckResultResponse] = []
    if result.iterations:
        final_checks = [
            check_result_to_response(c) for c in result.iterations[-1].critique_results
        ]

    return RunResponse(
        status=result.status.value,
        converged=result.converged,
        final_definition=result.final_definition,
        total_iterations=result.total_iterations,
        duration_seconds=result.duration_seconds,
        iterations=iterations,
        final_checks=final_checks,
    )


@router.post("/run", response_model=RunResponse)
async def run_ralph_loop(request: RunRequest) -> RunResponse:
    """Run the Ralph Loop for a single class.

    This is a blocking endpoint that runs the full loop and returns
    the final result. For real-time progress, use /run/stream.

    Args:
        request: Class information and configuration

    Returns:
        Final loop result with definition and check details
    """
    # Create ClassInfo
    class_info = ClassInfo(
        iri=request.iri,
        label=request.label,
        parent_class=request.parent_class,
        sibling_classes=request.sibling_classes,
        is_ice=request.is_ice,
        current_definition=request.current_definition,
    )

    # Get LLM provider
    llm = get_llm_provider(request.provider, request.api_key)

    # Create loop config
    config = LoopConfig(max_iterations=request.max_iterations)

    # Run the loop
    try:
        loop = RalphLoop(llm=llm, config=config)
        result = await loop.run(class_info)
        return loop_result_to_response(result)

    except Exception as e:
        # Map known exceptions to error codes
        error_message = str(e)

        if "rate" in error_message.lower() or "429" in error_message:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "code": ErrorCode.RATE_LIMIT.value,
                    "message": "API rate limit exceeded",
                    "retryable": True,
                    "retry_after": 60,
                },
            ) from None
        elif "timeout" in error_message.lower():
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail={
                    "code": ErrorCode.TIMEOUT.value,
                    "message": "LLM request timed out",
                    "retryable": True,
                },
            ) from None
        elif "api" in error_message.lower() or "key" in error_message.lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": ErrorCode.API_ERROR.value,
                    "message": error_message,
                    "retryable": False,
                },
            ) from None
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "code": ErrorCode.INTERNAL_ERROR.value,
                    "message": f"An error occurred: {error_message}",
                    "retryable": False,
                },
            ) from None


@router.get("/run/stream")
async def run_ralph_loop_stream(
    request: Request,
    token: str = Query(..., description="Session token"),
    iri: str = Query(..., description="Class IRI"),
    label: str = Query(..., description="Class label"),
    parent_class: str = Query(..., description="Parent class IRI"),
    is_ice: bool = Query(False, description="Is ICE class"),
    sibling_classes: str | None = Query(None, description="Comma-separated siblings"),
    current_definition: str | None = Query(None, description="Current definition"),
    max_iterations: int = Query(5, ge=1, le=10, description="Max iterations"),
) -> EventSourceResponse:
    """Run the Ralph Loop with SSE streaming.

    Streams real-time progress events as the loop runs.

    Event types:
    - iteration_start: Starting a new iteration
    - generate: Definition generated
    - critique: Critique phase complete
    - refine: Refinement complete
    - verify: Verification complete
    - complete: Loop finished successfully
    - error: An error occurred

    Args:
        token: Session token from /api/session
        iri: Class IRI
        label: Class label
        parent_class: Parent class IRI
        is_ice: Whether this is an ICE class
        sibling_classes: Comma-separated sibling class IRIs
        current_definition: Existing definition to improve
        max_iterations: Maximum iterations

    Returns:
        EventSourceResponse streaming SSE events
    """
    # Validate session token
    session_store = get_session_store()
    session = session_store.validate_session(token)

    if session is None:
        # Return error event immediately
        async def error_generator() -> AsyncGenerator[dict[str, str], None]:
            yield {
                "event": "error",
                "data": json.dumps(
                    {
                        "code": ErrorCode.INVALID_TOKEN.value,
                        "message": "Invalid or expired session token",
                        "retryable": False,
                    }
                ),
            }

        return EventSourceResponse(error_generator())

    # Parse sibling classes
    siblings: list[str] = []
    if sibling_classes:
        siblings = [s.strip() for s in sibling_classes.split(",") if s.strip()]

    # Create class info
    class_info = ClassInfo(
        iri=iri,
        label=label,
        parent_class=parent_class,
        sibling_classes=siblings,
        is_ice=is_ice,
        current_definition=current_definition,
    )

    # Get LLM provider from session
    llm = get_llm_provider(session.provider, session.api_key)

    # Create the SSE generator
    async def stream_generator() -> AsyncGenerator[dict[str, str], None]:
        # Event queue for hook callbacks
        event_queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        cancelled = False

        def make_hook_sync(coro_func: Any) -> Any:
            """Wrap an async callback for sync hook invocation."""

            def sync_wrapper(*args: Any, **kwargs: Any) -> None:
                # Put event in queue to be processed by async generator
                asyncio.create_task(coro_func(*args, **kwargs))

            return sync_wrapper

        async def on_iteration_start(iteration: int, state: LoopState) -> None:
            await event_queue.put(
                {
                    "event": "iteration_start",
                    "data": {
                        "iteration": iteration,
                        "max_iterations": state.max_iterations,
                    },
                }
            )

        async def on_generate(definition: str) -> None:
            await event_queue.put(
                {
                    "event": "generate",
                    "data": {"definition": definition},
                }
            )

        async def on_critique(results: list[CheckResult]) -> None:
            failed = [r for r in results if not r.passed]
            await event_queue.put(
                {
                    "event": "critique",
                    "data": {
                        "passed_count": len(results) - len(failed),
                        "failed_count": len(failed),
                        "failed_checks": [r.code for r in failed],
                    },
                }
            )

        async def on_refine(definition: str) -> None:
            await event_queue.put(
                {
                    "event": "refine",
                    "data": {"definition": definition},
                }
            )

        async def on_verify(
            verify_status: VerifyStatus, results: list[CheckResult]
        ) -> None:
            failed = [r for r in results if not r.passed]
            await event_queue.put(
                {
                    "event": "verify",
                    "data": {
                        "status": verify_status.value,
                        "passed_count": len(results) - len(failed),
                        "failed_count": len(failed),
                    },
                }
            )

        async def on_iteration_end(iteration: LoopIteration) -> None:
            await event_queue.put(
                {
                    "event": "iteration_end",
                    "data": {
                        "iteration": iteration.iteration_number,
                        "definition": iteration.final_definition,
                        "status": iteration.verify_status.value,
                    },
                }
            )

        # Create hooks with queue-based callbacks
        def _wrap_iteration_start(i: int, s: LoopState) -> None:
            asyncio.get_event_loop().call_soon_threadsafe(
                lambda: asyncio.create_task(on_iteration_start(i, s))
            )

        def _wrap_generate(d: str) -> None:
            asyncio.get_event_loop().call_soon_threadsafe(
                lambda: asyncio.create_task(on_generate(d))
            )

        def _wrap_critique(r: list[CheckResult]) -> None:
            asyncio.get_event_loop().call_soon_threadsafe(
                lambda: asyncio.create_task(on_critique(r))
            )

        def _wrap_refine(d: str) -> None:
            asyncio.get_event_loop().call_soon_threadsafe(
                lambda: asyncio.create_task(on_refine(d))
            )

        def _wrap_verify(s: VerifyStatus, r: list[CheckResult]) -> None:
            asyncio.get_event_loop().call_soon_threadsafe(
                lambda: asyncio.create_task(on_verify(s, r))
            )

        def _wrap_iteration_end(it: LoopIteration) -> None:
            asyncio.get_event_loop().call_soon_threadsafe(
                lambda: asyncio.create_task(on_iteration_end(it))
            )

        hooks = LoopHooks(
            on_iteration_start=_wrap_iteration_start,
            on_generate=_wrap_generate,
            on_critique=_wrap_critique,
            on_refine=_wrap_refine,
            on_verify=_wrap_verify,
            on_iteration_end=_wrap_iteration_end,
        )

        # Create loop config and runner
        config = LoopConfig(max_iterations=max_iterations)
        loop = RalphLoop(llm=llm, config=config, hooks=hooks)

        # Run loop in background task
        loop_task: asyncio.Task[LoopResult | None] = asyncio.create_task(
            run_loop_with_error_handling(loop, class_info, event_queue)
        )

        try:
            # Stream events from queue until complete
            while not loop_task.done() or not event_queue.empty():
                # Check for client disconnect
                if await request.is_disconnected():
                    cancelled = True
                    loop_task.cancel()
                    break

                try:
                    # Get next event with timeout
                    event = await asyncio.wait_for(event_queue.get(), timeout=0.1)
                    yield {
                        "event": event["event"],
                        "data": json.dumps(event["data"]),
                    }

                    # If complete or error, we're done
                    if event["event"] in ("complete", "error"):
                        break

                except TimeoutError:
                    # No event yet, continue checking
                    continue

        except asyncio.CancelledError:
            cancelled = True
        finally:
            if not loop_task.done():
                loop_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await loop_task

        if cancelled:
            yield {
                "event": "error",
                "data": json.dumps(
                    {
                        "code": "CANCELLED",
                        "message": "Request cancelled by client",
                        "retryable": False,
                    }
                ),
            }

    return EventSourceResponse(stream_generator())


async def run_loop_with_error_handling(
    loop: RalphLoop,
    class_info: ClassInfo,
    event_queue: asyncio.Queue[dict[str, Any]],
) -> LoopResult | None:
    """Run the loop and handle errors/completion."""
    try:
        result = await loop.run(class_info)

        # Send complete event
        response = loop_result_to_response(result)
        await event_queue.put(
            {
                "event": "complete",
                "data": response.model_dump(),
            }
        )

        return result

    except asyncio.CancelledError:
        raise
    except Exception as e:
        error_message = str(e)
        error_code = ErrorCode.INTERNAL_ERROR.value
        retryable = False
        retry_after = None

        if "rate" in error_message.lower() or "429" in error_message:
            error_code = ErrorCode.RATE_LIMIT.value
            error_message = "API rate limit exceeded"
            retryable = True
            retry_after = 60
        elif "timeout" in error_message.lower():
            error_code = ErrorCode.TIMEOUT.value
            error_message = "LLM request timed out"
            retryable = True
        elif "api" in error_message.lower() or "key" in error_message.lower():
            error_code = ErrorCode.API_ERROR.value
            retryable = False

        await event_queue.put(
            {
                "event": "error",
                "data": {
                    "code": error_code,
                    "message": error_message,
                    "retryable": retryable,
                    "retry_after": retry_after,
                },
            }
        )

        return None

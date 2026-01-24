"""Session token management endpoints."""

from fastapi import APIRouter, HTTPException, status

from ontoralph.web.models import SessionRequest, SessionResponse
from ontoralph.web.session_store import get_session_store

router = APIRouter(tags=["session"])

VALID_PROVIDERS = {"claude", "openai", "mock"}


@router.post("/session", response_model=SessionResponse)
async def create_session(request: SessionRequest) -> SessionResponse:
    """Exchange an API key for a session token.

    Session tokens are used for SSE endpoints since EventSource
    doesn't support custom headers. Tokens expire after 30 minutes
    of inactivity.

    Args:
        request: Provider and API key

    Returns:
        Session token with expiration time
    """
    # Validate provider
    if request.provider not in VALID_PROVIDERS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid provider: {request.provider}. Must be one of: {', '.join(sorted(VALID_PROVIDERS))}",
        )

    # Validate API key (basic check - not empty)
    if not request.api_key or not request.api_key.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="API key cannot be empty",
        )

    # Create session
    store = get_session_store()
    session = store.create_session(
        provider=request.provider,
        api_key=request.api_key,
    )

    return SessionResponse(
        session_token=session.token,
        expires_at=session.expires_at,
        provider=session.provider,
    )

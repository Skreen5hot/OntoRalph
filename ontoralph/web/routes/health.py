"""Health check endpoint."""

from fastapi import APIRouter

from ontoralph import __version__
from ontoralph.web.models import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Check service health.

    Returns:
        Health status and version information
    """
    return HealthResponse(status="ok", version=__version__)

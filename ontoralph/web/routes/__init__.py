"""API route handlers for OntoRalph Web UI."""

from ontoralph.web.routes.batch import router as batch_router
from ontoralph.web.routes.health import router as health_router
from ontoralph.web.routes.run import router as run_router
from ontoralph.web.routes.session import router as session_router
from ontoralph.web.routes.validate import router as validate_router

__all__ = [
    "batch_router",
    "health_router",
    "session_router",
    "validate_router",
    "run_router",
]

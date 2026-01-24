"""FastAPI server for OntoRalph Web UI.

This module provides the main FastAPI application and server configuration.
"""

import logging
import time
from collections.abc import AsyncGenerator, Awaitable, Callable
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from ontoralph import __version__
from ontoralph.web.routes import (
    batch_router,
    health_router,
    run_router,
    session_router,
    validate_router,
)
from ontoralph.web.session_store import get_session_store

# Configure logging
logger = logging.getLogger("ontoralph.web")

# Static files directory
STATIC_DIR = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler.

    Handles startup and shutdown events.
    """
    # Startup
    logger.info(f"Starting OntoRalph Web UI v{__version__}")

    yield

    # Shutdown
    store = get_session_store()
    cleared = store.clear_all()
    logger.info(f"Shutdown: cleared {cleared} sessions")


def create_app(
    cors_origins: list[str] | None = None,
    debug: bool = False,
) -> FastAPI:
    """Create and configure the FastAPI application.

    Args:
        cors_origins: Allowed CORS origins (default: localhost only)
        debug: Enable debug mode

    Returns:
        Configured FastAPI application
    """
    app = FastAPI(
        title="OntoRalph Web API",
        description="Local API for the OntoRalph definition refinement tool",
        version=__version__,
        lifespan=lifespan,
        debug=debug,
    )

    # Configure CORS
    if cors_origins is None:
        cors_origins = [
            "http://localhost:8765",
            "http://127.0.0.1:8765",
        ]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

    # Add request logging middleware
    @app.middleware("http")
    async def log_requests(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """Log all requests with timing."""
        start_time = time.time()
        response: Response = await call_next(request)
        duration = time.time() - start_time

        logger.info(
            f"{request.method} {request.url.path} "
            f"status={response.status_code} "
            f"duration={duration:.3f}s"
        )
        return response

    # Register API routes with /api prefix
    app.include_router(health_router, prefix="/api")
    app.include_router(session_router, prefix="/api")
    app.include_router(validate_router, prefix="/api")
    app.include_router(run_router, prefix="/api")
    app.include_router(batch_router, prefix="/api")

    # Mount static files if directory exists
    if STATIC_DIR.exists():
        app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

        @app.get("/")
        async def serve_index() -> Response:
            """Serve the main index.html."""
            index_path = STATIC_DIR / "index.html"
            if index_path.exists():
                return FileResponse(index_path)
            return JSONResponse(
                status_code=404,
                content={"message": "Frontend not built. Use /api endpoints."},
            )

        @app.get("/css/{path:path}")
        async def serve_css(path: str) -> Response:
            """Serve CSS files."""
            file_path = STATIC_DIR / "css" / path
            if file_path.exists():
                return FileResponse(file_path, media_type="text/css")
            return JSONResponse(status_code=404, content={"message": "Not found"})

        @app.get("/js/{path:path}")
        async def serve_js(path: str) -> Response:
            """Serve JavaScript files."""
            file_path = STATIC_DIR / "js" / path
            if file_path.exists():
                return FileResponse(file_path, media_type="application/javascript")
            return JSONResponse(status_code=404, content={"message": "Not found"})

    else:
        @app.get("/")
        async def no_frontend() -> JSONResponse:
            """Return message when frontend is not available."""
            return JSONResponse(
                content={
                    "message": "OntoRalph Web API is running",
                    "version": __version__,
                    "docs": "/docs",
                    "api": "/api/health",
                }
            )

    # Global exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(
        _request: Request, exc: Exception
    ) -> JSONResponse:
        """Handle uncaught exceptions."""
        logger.exception(f"Unhandled exception: {exc}")
        return JSONResponse(
            status_code=500,
            content={
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred",
                "retryable": False,
            },
        )

    return app


# Create the default app instance
app = create_app()


def run_server(
    host: str = "127.0.0.1",
    port: int = 8765,
    reload: bool = False,
    log_level: str = "info",
) -> None:
    """Run the development server.

    Args:
        host: Host to bind to
        port: Port to listen on
        reload: Enable auto-reload for development
        log_level: Logging level
    """
    import uvicorn

    uvicorn.run(
        "ontoralph.web.server:app",
        host=host,
        port=port,
        reload=reload,
        log_level=log_level,
    )


if __name__ == "__main__":
    run_server(reload=True)

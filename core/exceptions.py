import logging
import requests
from fastapi import Request
from fastapi.responses import JSONResponse

logger = logging.getLogger("mydylms")
logger.setLevel(logging.INFO)  # INFO by default; set DEBUG in dev


def add_exception_handlers(app):
    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError):
        logger.warning(f"ValueError at {request.url}: {exc}")
        return JSONResponse(status_code=401, content={"detail": str(exc)})

    @app.exception_handler(RuntimeError)
    async def runtime_error_handler(request: Request, exc: RuntimeError):
        logger.error(f"RuntimeError at {request.url}: {exc}", exc_info=True)
        return JSONResponse(status_code=500, content={"detail": str(exc)})

    @app.exception_handler(requests.exceptions.RequestException)
    async def requests_exception_handler(
        request: Request, exc: requests.exceptions.RequestException
    ):
        logger.error(f"External service error at {request.url}: {exc}", exc_info=True)
        return JSONResponse(
            status_code=503,
            content={
                "detail": "Failed to connect to external service",
                "error": str(exc),
            },
        )

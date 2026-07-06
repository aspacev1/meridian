import structlog
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import settings

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer(),
    ]
)
log = structlog.get_logger()

app = FastAPI(title="Meridian API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """RFC 7807 Problem Details, per API.md."""
    titles = {400: "Bad Request", 401: "Unauthorized", 403: "Forbidden", 404: "Not Found"}
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": exc.status_code,
            "title": titles.get(exc.status_code, "Error"),
            "detail": exc.detail,
        },
    )


@app.middleware("http")
async def log_requests(request: Request, call_next):
    response = await call_next(request)
    log.info(
        "request",
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
    )
    return response


app.include_router(api_router)

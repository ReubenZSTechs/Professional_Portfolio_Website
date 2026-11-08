"""FastAPI application. Every route lives under /api/py so it can share a domain with Next.js."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from agent.routes import chat, contact, health
from core.config import get_settings
from core.logging import configure_logging

PREFIX = "/api/py"

configure_logging()
settings = get_settings()

app = FastAPI(
    title="Reuben's portfolio API",
    version="1.0.0",
    docs_url=f"{PREFIX}/docs" if settings.environment != "production" else None,
    openapi_url=f"{PREFIX}/openapi.json" if settings.environment != "production" else None,
)

# Same-origin in production (Next.js and FastAPI share the Vercel domain). CORS only matters
# when calling uvicorn directly from the Next dev server.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Accept"],
)


@app.exception_handler(RequestValidationError)
async def validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
    """Return the first validation message as a plain, user-readable `detail` string."""
    first = exc.errors()[0] if exc.errors() else {}
    message = str(first.get("msg", "Invalid request")).removeprefix("Value error, ")
    field = first.get("loc", [None])[-1]
    if field == "email":
        message = "Please enter a valid email address."
    return JSONResponse(status_code=422, content={"detail": message})


app.include_router(health.router, prefix=PREFIX, tags=["health"])
app.include_router(chat.router, prefix=PREFIX, tags=["chat"])
app.include_router(contact.router, prefix=PREFIX, tags=["contact"])

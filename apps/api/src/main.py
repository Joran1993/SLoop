import logging

import sentry_sdk
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from .config import settings
from .middleware.rate_limit import get_org_id_for_ratelimit
from .routers import alerts, billing, leads, me

if settings.sentry_dsn:
    sentry_sdk.init(dsn=settings.sentry_dsn, traces_sample_rate=0.1)

logging.basicConfig(level=logging.INFO)

limiter = Limiter(key_func=get_org_id_for_ratelimit)

app = FastAPI(
    title="Sloopradar API",
    description="Lead-intelligence voor de Nederlandse sloopsector",
    version="0.1.0",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(leads.router, prefix="/api")
app.include_router(alerts.router, prefix="/api")
app.include_router(me.router, prefix="/api")
app.include_router(billing.router, prefix="/api")


@app.get("/health", tags=["meta"])
async def health():
    return {"status": "ok", "version": "0.1.0"}


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logging.exception("Onbehandelde fout op %s", request.url)
    return JSONResponse(status_code=500, content={"detail": "Interne serverfout"})

"""Main FastAPI application."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .core.config import settings
from .core.rate_limit import RateLimitMiddleware
from .core.logging_config import setup_logging
from .core.middleware import LoggingMiddleware
from .api.v1 import audit, optimize, citations, patterns

# Configure logging
logger = setup_logging()

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Logging middleware (first, to log all requests)
app.add_middleware(LoggingMiddleware)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiting middleware
if not settings.DEBUG:
    app.add_middleware(
        RateLimitMiddleware,
        requests_per_minute=settings.RATE_LIMIT_PER_MINUTE,
    )


# Exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An internal error occurred",
            }
        },
    )


# Health check endpoints
from .core.health import router as health_router

app.include_router(health_router)


# Include routers
app.include_router(audit.router, prefix=settings.API_V1_PREFIX, tags=["audit"])
app.include_router(optimize.router, prefix=settings.API_V1_PREFIX, tags=["optimize"])
app.include_router(citations.router, prefix=settings.API_V1_PREFIX, tags=["citations"])
app.include_router(patterns.router, prefix=settings.API_V1_PREFIX, tags=["patterns"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "AIEO API",
        "version": settings.APP_VERSION,
        "docs": "/docs",
    }

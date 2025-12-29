"""Health check utilities."""
from fastapi import APIRouter
from sqlalchemy import text
from .database import engine

router = APIRouter()


@router.get("/health")
async def health_check():
    """Comprehensive health check."""
    health_status = {
        "status": "healthy",
        "version": "0.1.0",
        "checks": {}
    }
    
    # Check database
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        health_status["checks"]["database"] = "healthy"
    except Exception as e:
        health_status["checks"]["database"] = f"unhealthy: {str(e)}"
        health_status["status"] = "degraded"
    
    # Check Redis (if configured)
    try:
        from .config import settings
        import redis
        if settings.REDIS_URL:
            redis_client = redis.Redis.from_url(settings.REDIS_URL)
            redis_client.ping()
            health_status["checks"]["redis"] = "healthy"
    except Exception:
        health_status["checks"]["redis"] = "unavailable"
    
    return health_status


@router.get("/health/live")
async def liveness_check():
    """Liveness check for Kubernetes."""
    return {"status": "alive"}


@router.get("/health/ready")
async def readiness_check():
    """Readiness check for Kubernetes."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ready"}
    except Exception:
        return {"status": "not_ready"}, 503


"""Celery tasks for citation tracking."""

from celery import Celery
from ..core.config import settings
from ..services.citation_tracker import CitationTracker
from ..core.database import SessionLocal

# Create Celery app
celery_app = Celery(
    "aieo",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)


@celery_app.task(name="probe_engines_for_citations")
def probe_engines_for_citations(
    url: str, prompts: list[str], engines: list[str] = None
):
    """
    Probe AI engines for citations (async task).

    Args:
        url: URL to check citations for
        prompts: List of prompts to test
        engines: List of engines to probe
    """
    tracker = CitationTracker()
    db = SessionLocal()

    try:
        citations = tracker.probe_engines(url, prompts, engines)
        tracker.store_citations(db, citations)
        return {"status": "success", "citations_found": len(citations)}
    except Exception as e:
        return {"status": "error", "error": str(e)}
    finally:
        db.close()


@celery_app.task(name="batch_audit_content")
def batch_audit_content(urls: list[str]):
    """
    Batch audit multiple URLs (async task).

    Args:
        urls: List of URLs to audit
    """
    from ..services.audit_service import AuditService

    service = AuditService()
    results = []

    for url in urls:
        try:
            result = service.audit(url=url)
            results.append(
                {"url": url, "status": "success", "score": result.get("score")}
            )
        except Exception as e:
            results.append({"url": url, "status": "error", "error": str(e)})

    return results

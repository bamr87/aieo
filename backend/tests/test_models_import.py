"""Regression: the models package must import cleanly.

Alembic's ``env.py`` runs ``from app import models`` so the package's
``__init__`` is imported on every migration command. A wrong class name there
(e.g. ``ApiKey`` vs ``APIKey``) raises ImportError and breaks all migrations.
Skipped when SQLAlchemy isn't installed (the lighter CI/headless dependency set).
"""

import importlib
import importlib.util

import pytest

_HAS_DB_DEPS = (
    importlib.util.find_spec("sqlalchemy") is not None
    and importlib.util.find_spec("psycopg2") is not None
)

pytestmark = pytest.mark.skipif(
    not _HAS_DB_DEPS,
    reason="sqlalchemy/psycopg2 not installed (full backend deps required)",
)

EXPECTED_MODELS = [
    "APIKey",
    "Audit",
    "Citation",
    "User",
    "Topic",
    "ResearchBrief",
    "Draft",
    "Rewrite",
    "PublishedArticle",
    "LandingPage",
    "AuditRun",
]


def test_models_package_exports_all_classes():
    models = importlib.import_module("app.models")
    for name in EXPECTED_MODELS:
        assert hasattr(models, name), f"app.models is missing {name}"
    # The class is APIKey, not ApiKey — guards the import typo that breaks Alembic.
    assert models.APIKey.__name__ == "APIKey"


def test_models_all_matches_exports():
    models = importlib.import_module("app.models")
    assert set(models.__all__) == set(EXPECTED_MODELS)

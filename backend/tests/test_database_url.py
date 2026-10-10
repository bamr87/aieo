"""DATABASE_URL driver selection.

SQLAlchemy 2.1 made psycopg 3 the default driver for a bare ``postgresql://``
URL. This project installs psycopg2, so ``Settings`` names the driver itself.
"""

import pytest
from sqlalchemy.engine import make_url

from app.core.config import Settings


def _settings(url: str) -> Settings:
    return Settings(DATABASE_URL=url)


def test_bare_postgres_url_gets_the_psycopg2_driver():
    settings = _settings("postgresql://aieo:testpass@localhost:5432/aieo_test")

    assert settings.DATABASE_URL == (
        "postgresql+psycopg2://aieo:testpass@localhost:5432/aieo_test"
    )


def test_the_resolved_driver_is_importable():
    # The failure this guards against: the default driver was psycopg 3, so
    # importing the DBAPI raised ModuleNotFoundError before any query ran.
    url = make_url(_settings("postgresql://aieo:aieo@localhost/aieo").DATABASE_URL)

    assert url.get_dialect().import_dbapi().__name__ == "psycopg2"


@pytest.mark.parametrize(
    "url",
    [
        "postgresql+psycopg://aieo:aieo@localhost/aieo",
        "postgresql+asyncpg://aieo:aieo@localhost/aieo",
        "sqlite:///./aieo_dev.db",
    ],
)
def test_urls_that_name_a_driver_or_are_not_postgres_are_untouched(url):
    assert _settings(url).DATABASE_URL == url

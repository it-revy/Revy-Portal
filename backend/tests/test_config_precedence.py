import os
import pytest
from app.core.config import Settings

def test_deployment_env_var_takes_precedence_over_dotenv(monkeypatch):
    """
    Verify 12-factor configuration precedence:
    Deployment-supplied environment variables (os.environ) MUST take precedence
    over local .env file values.
    """
    deployment_db_url = "postgresql://prod_cluster_owner:securepass@prod-cluster.neon.tech/proddb?sslmode=require"
    monkeypatch.setenv("DATABASE_URL", deployment_db_url)

    test_settings = Settings()
    assert test_settings.DATABASE_URL == deployment_db_url, (
        f"Deployment environment variable was overridden! Expected {deployment_db_url}, got {test_settings.DATABASE_URL}"
    )

def test_custom_jwt_secret_precedence(monkeypatch):
    """
    Verify deployment-supplied secrets override defaults and .env.
    """
    custom_secret = "deployment_injected_jwt_secret_998877"
    monkeypatch.setenv("JWT_SECRET", custom_secret)

    test_settings = Settings()
    assert test_settings.JWT_SECRET == custom_secret

def test_database_url_protocol_normalization(monkeypatch):
    """
    Verify legacy postgres:// URLs are normalized to postgresql://.
    """
    legacy_url = "postgres://user:pass@host:5432/dbname"
    monkeypatch.setenv("DATABASE_URL", legacy_url)

    test_settings = Settings()
    assert test_settings.DATABASE_URL.startswith("postgresql://")

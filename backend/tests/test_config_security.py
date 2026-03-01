"""Tests for configuration security hardening."""

import pytest


class TestJWTSecretValidation:
    def test_default_secret_raises_in_production(self, monkeypatch):
        """App must refuse to start with default JWT secret in production."""
        monkeypatch.setenv("NILE_JWT_SECRET", "nile-dev-secret-change-me")
        monkeypatch.setenv("NILE_ENV", "production")

        with pytest.raises(RuntimeError, match="Default JWT secret"):
            # Re-import to trigger the module-level check
            import importlib

            import nile.config

            importlib.reload(nile.config)

    def test_default_secret_ok_in_development(self, monkeypatch):
        """Default secret is acceptable in development mode."""
        monkeypatch.setenv("NILE_JWT_SECRET", "nile-dev-secret-change-me")
        monkeypatch.setenv("NILE_ENV", "development")

        import importlib

        import nile.config

        importlib.reload(nile.config)
        assert nile.config.settings.jwt_secret == "nile-dev-secret-change-me"

    def test_custom_secret_ok_in_production(self, monkeypatch):
        """Custom JWT secret works fine in production."""
        monkeypatch.setenv("NILE_JWT_SECRET", "super-secure-random-value-here")
        monkeypatch.setenv("NILE_ENV", "production")

        import importlib

        import nile.config

        importlib.reload(nile.config)
        assert nile.config.settings.jwt_secret == "super-secure-random-value-here"

"""Tests for config module — JWT secret warning."""

from unittest.mock import patch

from nile.config import Settings


class TestSettings:
    def test_default_values(self):
        s = Settings(
            _env_file=None,
            database_url="sqlite+aiosqlite://",
        )
        assert s.chain == "solana"
        assert s.env == "development"
        assert s.solana_network == "devnet"

    def test_custom_values(self):
        s = Settings(
            _env_file=None,
            database_url="sqlite+aiosqlite://",
            chain="solana",
            env="production",
            jwt_secret="super-secret-key-here-long-enough",
        )
        assert s.env == "production"
        assert s.jwt_secret == "super-secret-key-here-long-enough"


class TestJwtWarning:
    def test_default_secret_in_production_warns(self):
        """The config module warns when default JWT secret is used in non-dev."""
        import importlib
        import warnings

        with (
            patch.dict(
                "os.environ",
                {
                    "NILE_JWT_SECRET": "nile-dev-secret-change-me",
                    "NILE_ENV": "production",
                    "NILE_DATABASE_URL": "sqlite+aiosqlite://",
                },
            ),
            warnings.catch_warnings(record=True) as w,
        ):
            warnings.simplefilter("always")
            import nile.config

            importlib.reload(nile.config)

            # Should have produced a warning
            security_warnings = [x for x in w if "SECURITY WARNING" in str(x.message)]
            assert len(security_warnings) >= 1

        # Reload with defaults to restore
        with patch.dict("os.environ", {}, clear=False):
            importlib.reload(nile.config)

"""Tests for auth_handler module - Task 5."""

import os
import pytest
from unittest.mock import patch

from worker.auth_handler import AuthConfig, AuthHandler


class TestAuthConfig:
    """Test AuthConfig dataclass defaults."""

    def test_default_values(self):
        config = AuthConfig()
        assert config.auth_type == "none"
        assert config.auth_config == {}


class TestAuthHandler:
    """Test AuthHandler methods."""

    def setup_method(self):
        self.handler = AuthHandler()

    # --- test_no_auth ---
    def test_no_auth(self):
        """No auth should return empty or extra headers only."""
        config = AuthConfig(auth_type="none", auth_config={})
        headers = self.handler.build_headers(config, {})
        # Should not contain any auth headers
        assert "Authorization" not in headers
        assert "X-API-Key" not in headers

    # --- test_bearer_token ---
    def test_bearer_token(self):
        """Bearer token should produce Authorization header."""
        config = AuthConfig(
            auth_type="bearer",
            auth_config={"token": "my-secret-token"},
        )
        headers = self.handler.build_headers(config, {})
        assert headers["Authorization"] == "Bearer my-secret-token"

    # --- test_bearer_token_with_env_substitution ---
    def test_bearer_token_with_env_substitution(self):
        """Bearer token with ${VAR} should be resolved from env."""
        config = AuthConfig(
            auth_type="bearer",
            auth_config={"token": "${BEARER_TOKEN}"},
        )
        with patch.dict(os.environ, {"BEARER_TOKEN": "env-resolved-token"}):
            headers = self.handler.build_headers(config, {})
        assert headers["Authorization"] == "Bearer env-resolved-token"

    # --- test_bearer_token_missing_env_var ---
    def test_bearer_token_missing_env_var(self):
        """Missing env var should raise ValueError."""
        config = AuthConfig(
            auth_type="bearer",
            auth_config={"token": "${NON_EXISTENT_VAR_XYZ}"},
        )
        # Make sure the env var does not exist
        env = os.environ.copy()
        env.pop("NON_EXISTENT_VAR_XYZ", None)
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(ValueError, match="NON_EXISTENT_VAR_XYZ"):
                self.handler.build_headers(config, {})

    # --- test_api_key_in_header ---
    def test_api_key_in_header(self):
        """API key with in=header should produce X-API-Key header."""
        config = AuthConfig(
            auth_type="api_key",
            auth_config={"key": "my-api-key", "in": "header", "header_name": "X-API-Key"},
        )
        headers = self.handler.build_headers(config, {})
        assert headers["X-API-Key"] == "my-api-key"

    # --- test_api_key_in_query ---
    def test_api_key_in_query(self):
        """API key with in=query should produce query param."""
        config = AuthConfig(
            auth_type="api_key",
            auth_config={"key": "my-api-key", "in": "query", "param_name": "api_key"},
        )
        params = self.handler.build_query_params(config)
        assert params["api_key"] == "my-api-key"

    # --- test_basic_auth ---
    def test_basic_auth(self):
        """Basic auth should produce Authorization: Basic base64 header."""
        import base64

        config = AuthConfig(
            auth_type="basic",
            auth_config={"username": "user", "password": "pass"},
        )
        headers = self.handler.build_headers(config, {})
        expected = base64.b64encode(b"user:pass").decode()
        assert headers["Authorization"] == f"Basic {expected}"

    # --- test_basic_auth_with_env_vars ---
    def test_basic_auth_with_env_vars(self):
        """Basic auth with env var substitution."""
        import base64

        config = AuthConfig(
            auth_type="basic",
            auth_config={"username": "${API_USER}", "password": "${API_PASS}"},
        )
        with patch.dict(os.environ, {"API_USER": "admin", "API_PASS": "secret"}):
            headers = self.handler.build_headers(config, {})
        expected = base64.b64encode(b"admin:secret").decode()
        assert headers["Authorization"] == f"Basic {expected}"

    # --- test_extra_headers_included ---
    def test_extra_headers_included(self):
        """Extra headers should be included in the result."""
        config = AuthConfig(auth_type="none", auth_config={})
        extra = {"X-Custom-Header": "custom-value", "Content-Type": "application/json"}
        headers = self.handler.build_headers(config, extra)
        assert headers["X-Custom-Header"] == "custom-value"
        assert headers["Content-Type"] == "application/json"

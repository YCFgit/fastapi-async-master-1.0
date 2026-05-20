# src/worker/auth_handler.py
"""Authentication handler that builds HTTP auth headers for GenericAPIExecutor."""

import base64
import os
import re
from dataclasses import dataclass, field
from typing import Dict


@dataclass
class AuthConfig:
    """Authentication configuration.

    Attributes:
        auth_type: Type of authentication. One of: none, bearer, api_key, basic.
        auth_config: Auth-specific configuration dict.
    """

    auth_type: str = "none"  # none | bearer | api_key | basic
    auth_config: Dict[str, str] = field(default_factory=dict)


class AuthHandler:
    """Builds HTTP auth headers and query params based on AuthConfig."""

    # Pattern for environment variable substitution: ${VAR_NAME}
    _ENV_VAR_PATTERN = re.compile(r"\$\{([A-Z][A-Z0-9_]*)\}")

    def build_headers(
        self, config: AuthConfig, extra_headers: Dict[str, str]
    ) -> Dict[str, str]:
        """Build HTTP headers including authentication headers.

        Args:
            config: AuthConfig with auth type and credentials.
            extra_headers: Additional headers to include.

        Returns:
            Combined headers dict.
        """
        headers: Dict[str, str] = {}

        if config.auth_type == "bearer":
            token = self._resolve_env_vars(config.auth_config.get("token", ""))
            headers["Authorization"] = f"Bearer {token}"

        elif config.auth_type == "api_key":
            location = config.auth_config.get("in", "header")
            if location == "header":
                header_name = config.auth_config.get("header_name", "X-API-Key")
                key = self._resolve_env_vars(config.auth_config.get("key", ""))
                headers[header_name] = key

        elif config.auth_type == "basic":
            username = self._resolve_env_vars(
                config.auth_config.get("username", "")
            )
            password = self._resolve_env_vars(
                config.auth_config.get("password", "")
            )
            credentials = base64.b64encode(
                f"{username}:{password}".encode()
            ).decode()
            headers["Authorization"] = f"Basic {credentials}"

        # Merge extra headers (extra_headers take precedence)
        headers.update(extra_headers)
        return headers

    def build_query_params(self, config: AuthConfig) -> Dict[str, str]:
        """Build query parameters for API key in query location.

        Args:
            config: AuthConfig with auth type and credentials.

        Returns:
            Query params dict (empty if not api_key in query).
        """
        params: Dict[str, str] = {}

        if config.auth_type == "api_key":
            location = config.auth_config.get("in", "header")
            if location == "query":
                param_name = config.auth_config.get("param_name", "api_key")
                key = self._resolve_env_vars(config.auth_config.get("key", ""))
                params[param_name] = key

        return params

    def _resolve_env_vars(self, value: str) -> str:
        """Replace ${VAR_NAME} patterns with environment variable values.

        VAR_NAME must match [A-Z][A-Z0-9_]*.
        Raises ValueError if referenced env var is not defined.

        Args:
            value: String potentially containing ${VAR_NAME} patterns.

        Returns:
            String with env vars resolved.

        Raises:
            ValueError: If a referenced environment variable is not defined.
        """

        def _replacer(match: re.Match) -> str:
            var_name = match.group(1)
            env_value = os.environ.get(var_name)
            if env_value is None:
                raise ValueError(
                    f"Environment variable '{var_name}' is not defined"
                )
            return env_value

        return self._ENV_VAR_PATTERN.sub(_replacer, value)

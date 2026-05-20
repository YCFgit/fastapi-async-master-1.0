# src/worker/template_renderer.py
"""Jinja2 template renderer with sandbox protection for GenericAPIExecutor."""

import json
from typing import Any, Dict

from jinja2 import TemplateSyntaxError, UndefinedError
from jinja2.sandbox import SandboxedEnvironment
from jinja2 import StrictUndefined


class TemplateRenderError(Exception):
    """Raised when template rendering fails."""
    pass


class TemplateRenderer:
    """Jinja2 template renderer with sandbox protection.

    Uses SandboxedEnvironment to prevent access to private attributes
    and unsafe operations. Uses StrictUndefined to raise errors on
    missing variables.
    """

    def __init__(self, timeout: int = 5):
        """Initialize the renderer.

        Args:
            timeout: Rendering timeout in seconds (reserved for future use).
        """
        self._timeout = timeout
        self._env = SandboxedEnvironment(
            undefined=StrictUndefined,
            # Disable autoescaping for non-HTML templates
            autoescape=False,
        )

    def render(self, template_str: str, data: Dict[str, Any]) -> str:
        """Render a Jinja2 template string with the given data.

        Args:
            template_str: Jinja2 template string.
            data: Template context data.

        Returns:
            Rendered string.

        Raises:
            TemplateRenderError: If rendering fails due to syntax error,
                missing variable, or sandbox violation.
        """
        try:
            template = self._env.from_string(template_str)
            return template.render(**data)
        except (TemplateSyntaxError, UndefinedError) as e:
            raise TemplateRenderError(f"Template render error: {e}") from e
        except SecurityError as e:
            raise TemplateRenderError(
                f"Template sandbox violation: {e}"
            ) from e
        except Exception as e:
            raise TemplateRenderError(f"Template render error: {e}") from e

    def render_json(self, template_str: str, data: Dict[str, Any]) -> Dict:
        """Render a Jinja2 template and parse the result as JSON.

        Args:
            template_str: Jinja2 template string (should produce valid JSON).
            data: Template context data.

        Returns:
            Parsed JSON as dict.

        Raises:
            TemplateRenderError: If rendering or JSON parsing fails.
        """
        rendered = self.render(template_str, data)
        try:
            return json.loads(rendered)
        except json.JSONDecodeError as e:
            raise TemplateRenderError(
                f"Template render result is not valid JSON: {e}"
            ) from e

    def validate_syntax(self, template_str: str) -> bool:
        """Check if a template string has valid Jinja2 syntax.

        Args:
            template_str: Jinja2 template string to validate.

        Returns:
            True if syntax is valid, False otherwise.
        """
        try:
            self._env.parse(template_str)
            return True
        except TemplateSyntaxError:
            return False


# Re-export SecurityError for the except clause
try:
    from jinja2.sandbox import SecurityError
except ImportError:
    # Fallback: SecurityError may not exist in all Jinja2 versions
    SecurityError = Exception

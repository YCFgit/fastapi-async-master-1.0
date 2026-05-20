# src/worker/response_parser.py
"""JSONPath-based response parser for GenericAPIExecutor."""

import json
from typing import Any, Dict, Optional

from jsonpath_ng.ext import parse as jsonpath_parse


class ResponseParseError(Exception):
    """Raised when response parsing fails."""
    pass


class ResponseParser:
    """Extract values from JSON responses using JSONPath expressions.

    Uses jsonpath_ng.ext.parse for full JSONPath support including
    filter expressions, slices, and recursive descent.
    """

    def extract(
        self,
        data: Dict[str, Any],
        jsonpath_expr: str,
        strict: bool = False,
    ) -> Optional[Any]:
        """Extract a value from data using a JSONPath expression.

        Args:
            data: The JSON data to extract from.
            jsonpath_expr: JSONPath expression (e.g., "$.data.field").
            strict: If True, raise ResponseParseError when path not found.

        Returns:
            Extracted value, or None if path not found (non-strict).

        Raises:
            ResponseParseError: If strict=True and path not found,
                or if the JSONPath expression is invalid.
        """
        try:
            expression = jsonpath_parse(jsonpath_expr)
            matches = expression.find(data)

            if not matches:
                if strict:
                    raise ResponseParseError(
                        f"JSONPath '{jsonpath_expr}' not found in response"
                    )
                return None

            # Return single value if one match, list if multiple
            if len(matches) == 1:
                return matches[0].value
            return [m.value for m in matches]

        except ResponseParseError:
            raise
        except Exception as e:
            if strict:
                raise ResponseParseError(
                    f"Failed to extract '{jsonpath_expr}': {e}"
                ) from e
            return None

    def extract_error(
        self, data: Dict[str, Any], jsonpath_expr: str
    ) -> Optional[str]:
        """Extract an error message from response data.

        Args:
            data: The JSON data to extract from.
            jsonpath_expr: JSONPath expression for the error field.

        Returns:
            Error message string, or None if not found.
        """
        result = self.extract(data, jsonpath_expr, strict=False)
        if result is None:
            return None
        return str(result)

    def extract_status(
        self, data: Dict[str, Any], jsonpath_expr: str
    ) -> Optional[Any]:
        """Extract a status field from response data.

        Args:
            data: The JSON data to extract from.
            jsonpath_expr: JSONPath expression for the status field.

        Returns:
            Status value, or None if not found.
        """
        return self.extract(data, jsonpath_expr, strict=False)

    def parse_raw_response(self, raw: str) -> Optional[Dict]:
        """Try to parse a raw string as JSON.

        Args:
            raw: Raw response string.

        Returns:
            Parsed dict, or None if parsing fails or input is empty.
        """
        if not raw or not raw.strip():
            return None

        try:
            result = json.loads(raw)
            if isinstance(result, dict):
                return result
            return None
        except (json.JSONDecodeError, ValueError):
            return None

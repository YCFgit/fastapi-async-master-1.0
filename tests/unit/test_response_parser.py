"""Tests for response_parser module - Task 7."""

import pytest

from worker.response_parser import ResponseParser, ResponseParseError


class TestResponseParser:
    """Test ResponseParser methods."""

    def setup_method(self):
        self.parser = ResponseParser()

    # --- test_basic_jsonpath ---
    def test_basic_jsonpath(self):
        """Basic $.data.field extraction."""
        data = {"data": {"translated_text": "Hello World"}}
        result = self.parser.extract(data, "$.data.translated_text")
        assert result == "Hello World"

    # --- test_nested_jsonpath ---
    def test_nested_jsonpath(self):
        """Array element access $.choices[0].message.content."""
        data = {
            "choices": [
                {"message": {"content": "This is the result"}}
            ]
        }
        result = self.parser.extract(data, "$.choices[0].message.content")
        assert result == "This is the result"

    # --- test_array_result ---
    def test_array_result(self):
        """Extracting an array value."""
        data = {"data": {"items": [1, 2, 3]}}
        result = self.parser.extract(data, "$.data.items")
        assert result == [1, 2, 3]

    # --- test_missing_path_returns_none ---
    def test_missing_path_returns_none(self):
        """Missing path should return None in non-strict mode."""
        data = {"data": {"other": "value"}}
        result = self.parser.extract(data, "$.data.translated_text", strict=False)
        assert result is None

    # --- test_missing_path_raises_when_strict ---
    def test_missing_path_raises_when_strict(self):
        """Missing path should raise ResponseParseError in strict mode."""
        data = {"data": {"other": "value"}}
        with pytest.raises(ResponseParseError):
            self.parser.extract(data, "$.data.translated_text", strict=True)

    # --- test_extract_error_message ---
    def test_extract_error_message(self):
        """Extract error message from response."""
        data = {"error": {"message": "Rate limit exceeded"}}
        result = self.parser.extract_error(data, "$.error.message")
        assert result == "Rate limit exceeded"

    # --- test_extract_error_missing ---
    def test_extract_error_missing(self):
        """Missing error path should return None."""
        data = {"data": "ok"}
        result = self.parser.extract_error(data, "$.error.message")
        assert result is None

    # --- test_non_json_fallback ---
    def test_non_json_fallback(self):
        """Non-JSON string should return None."""
        result = self.parser.parse_raw_response("This is not JSON")
        assert result is None

    # --- test_empty_response ---
    def test_empty_response(self):
        """Empty string should return None."""
        result = self.parser.parse_raw_response("")
        assert result is None

    # --- test_json_response ---
    def test_json_response(self):
        """Valid JSON string should be parsed to dict."""
        raw = '{"status": "ok", "data": {"result": "success"}}'
        result = self.parser.parse_raw_response(raw)
        assert isinstance(result, dict)
        assert result["status"] == "ok"
        assert result["data"]["result"] == "success"

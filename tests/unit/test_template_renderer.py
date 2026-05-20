"""Tests for template_renderer module - Task 6."""

import pytest

from worker.template_renderer import TemplateRenderer, TemplateRenderError


class TestTemplateRenderer:
    """Test TemplateRenderer methods."""

    def setup_method(self):
        self.renderer = TemplateRenderer(timeout=5)

    # --- test_basic_render ---
    def test_basic_render(self):
        """Basic variable substitution in JSON template."""
        template_str = '{"text": "{{content}}"}'
        data = {"content": "Hello"}
        result = self.renderer.render(template_str, data)
        assert result == '{"text": "Hello"}'

    # --- test_params_render ---
    def test_params_render(self):
        """Nested params access via dot notation."""
        template_str = '{{params.target_lang}}'
        data = {"params": {"target_lang": "zh-CN"}}
        result = self.renderer.render(template_str, data)
        assert result == "zh-CN"

    # --- test_default_filter ---
    def test_default_filter(self):
        """Default filter should provide fallback value."""
        template_str = '{{params.lang | default("en")}}'
        data = {"params": {}}
        result = self.renderer.render(template_str, data)
        assert result == "en"

    # --- test_missing_variable_raises_error ---
    def test_missing_variable_raises_error(self):
        """StrictUndefined should raise error for missing variables."""
        template_str = '{{missing_var}}'
        data = {}
        with pytest.raises(TemplateRenderError):
            self.renderer.render(template_str, data)

    # --- test_sandbox_prevents_private_access ---
    def test_sandbox_prevents_private_access(self):
        """Sandbox should prevent access to private attributes."""
        template_str = '{{config.__class__}}'
        data = {"config": {"key": "value"}}
        with pytest.raises(TemplateRenderError):
            self.renderer.render(template_str, data)

    # --- test_empty_template ---
    def test_empty_template(self):
        """Static content without variables should pass through."""
        template_str = '{"static": "content"}'
        data = {}
        result = self.renderer.render(template_str, data)
        assert result == '{"static": "content"}'

    # --- test_complex_template ---
    def test_complex_template(self):
        """Complex nested JSON with multiple variables."""
        template_str = '''
        {
            "source": "{{source_lang}}",
            "target": "{{target_lang}}",
            "text": "{{content}}",
            "model": "{{model | default('gpt-4')}}"
        }
        '''.strip()
        data = {
            "source_lang": "en",
            "target_lang": "zh-CN",
            "content": "Hello World",
        }
        result = self.renderer.render(template_str, data)
        assert '"source": "en"' in result
        assert '"target": "zh-CN"' in result
        assert '"text": "Hello World"' in result
        assert '"model": "gpt-4"' in result

    # --- test_render_json ---
    def test_render_json(self):
        """render_json should return parsed dict."""
        template_str = '{"text": "{{content}}", "lang": "{{lang}}"}'
        data = {"content": "Hello", "lang": "en"}
        result = self.renderer.render_json(template_str, data)
        assert isinstance(result, dict)
        assert result["text"] == "Hello"
        assert result["lang"] == "en"

    # --- test_validate_template_syntax_valid ---
    def test_validate_template_syntax_valid(self):
        """Valid template syntax should return True."""
        assert self.renderer.validate_syntax('{{variable}}') is True

    # --- test_validate_template_syntax_invalid ---
    def test_validate_template_syntax_invalid(self):
        """Invalid template syntax should return False."""
        assert self.renderer.validate_syntax('{{unclosed') is False

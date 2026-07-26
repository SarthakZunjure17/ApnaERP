import logging
from typing import Any, Dict, Optional
from jinja2 import Environment, BaseLoader, TemplateSyntaxError, UndefinedError

logger = logging.getLogger("app.services.template")

# Create a sandboxed Jinja2 Environment
jinja_env = Environment(loader=BaseLoader(), autoescape=True)


class TemplateService:
    """
    Service responsible for Jinja2 dynamic template rendering.
    Supports variables like {{user_name}}, {{employee_name}}, {{department}}, {{date}}, {{invoice_number}}, {{amount}}.
    """
    @staticmethod
    def render(template_str: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Renders a Jinja2 template string with the provided context dictionary.
        """
        if not template_str:
            return ""
        
        context_data = context or {}
        try:
            template = jinja_env.from_string(template_str)
            rendered = template.render(**context_data)
            return rendered
        except (TemplateSyntaxError, UndefinedError) as e:
            logger.error(f"Jinja2 template rendering error: {e}")
            # Fallback to plain string if Jinja rendering encounters syntax error
            return template_str


template_service = TemplateService()

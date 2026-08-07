from typing import Any, Dict
import jinja2


class NotificationTemplateEngine:
    """
    Template rendering engine for HTML emails, SMS, WhatsApp, and push notification messages.
    """
    def __init__(self):
        self._env = jinja2.Environment(loader=jinja2.DictLoader({
            "welcome_email": "<h1>Welcome to ApnaERP, {{ name }}!</h1><p>Your account {{ email }} has been created.</p>",
            "scheduled_report": "<h2>Scheduled Report: {{ report_name }}</h2><p>Attached is your requested report snapshot generated on {{ generated_at }}.</p>",
            "password_reset": "<p>Hello {{ name }}, click <a href='{{ reset_url }}'>here</a> to reset your password.</p>",
            "kpi_alert": "<h3 style='color:red;'>KPI Threshold Breach Alert</h3><p>KPI <b>{{ kpi_name }}</b> value <b>{{ current_value }}</b> breached threshold <b>{{ threshold_value }}</b>.</p>",
            "invoice_notice": "<p>Dear {{ customer_name }}, Invoice <b>{{ invoice_number }}</b> for {{ amount }} is ready.</p>",
        }))

    def render(self, template_name: str, context: Dict[str, Any]) -> str:
        try:
            tmpl = self._env.get_template(template_name)
            return tmpl.render(**context)
        except jinja2.TemplateNotFound:
            # Fallback inline string rendering
            return f"[{template_name}] Context: {context}"

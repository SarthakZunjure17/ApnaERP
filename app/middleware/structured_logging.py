import json
import logging
import re
from typing import Any, Dict


class SensitiveDataMasker:
    """
    Utility for masking passwords, tokens, secrets, and authorization headers in production logs.
    """
    SENSITIVE_KEYS = {"password", "secret", "token", "authorization", "api_key", "key_hash", "access_token"}

    @classmethod
    def mask_dict(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        masked = {}
        for k, v in data.items():
            if any(s in k.lower() for s in cls.SENSITIVE_KEYS):
                masked[k] = "******"
            elif isinstance(v, dict):
                masked[k] = cls.mask_dict(v)
            else:
                masked[k] = v
        return masked


class JsonFormatter(logging.Formatter):
    """
    Production JSON Log Formatter.
    """
    def format(self, record: logging.LogRecord) -> str:
        log_obj = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if hasattr(record, "correlation_id"):
            log_obj["correlation_id"] = record.correlation_id
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_obj)

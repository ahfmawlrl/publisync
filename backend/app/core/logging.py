import re

import structlog


def _mask_pii(_logger: object, _method: str, event_dict: dict) -> dict:  # type: ignore[type-arg]
    """Mask PII in log output."""
    for key, value in event_dict.items():
        if not isinstance(value, str):
            continue
        # Email: kim@agency.co.kr → ***@***.kr
        value = re.sub(
            r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+",
            lambda m: "***@***." + m.group().rsplit(".", 1)[-1],
            value,
        )
        # Phone: 010-1234-5678 → ***-****-5678
        value = re.sub(
            r"\d{2,3}-\d{3,4}-(\d{4})",
            r"***-****-\1",
            value,
        )
        event_dict[key] = value
    return event_dict


def setup_logging(*, json_format: bool = True) -> None:
    """Configure structlog processors."""
    processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        _mask_pii,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]
    if json_format:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

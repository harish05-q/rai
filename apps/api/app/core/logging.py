import logging

logger = logging.getLogger("rai")


def configure_logging() -> None:
    if logger.handlers:
        return
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


def log_event(message: str, **fields: object) -> None:
    parts = [message]
    for key, value in fields.items():
        if value is None:
            continue
        lowered = key.lower()
        if any(token in lowered for token in ("secret", "token", "password", "authorization", "api_key")):
            continue
        parts.append(f"{key}={value}")
    logger.info(" ".join(parts))

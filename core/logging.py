from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)


def _build_file_handler(filename: str) -> RotatingFileHandler:
    handler = RotatingFileHandler(
        LOG_DIR / filename,
        maxBytes=2 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(
        logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    )
    return handler


def _build_console_handler() -> logging.StreamHandler:
    handler = logging.StreamHandler()
    handler.setLevel(logging.INFO)
    handler.setFormatter(
        logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    )
    return handler


def _configure_named_logger(name: str, file_name: str) -> None:
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()
    logger.propagate = False

    logger.addHandler(_build_file_handler(file_name))
    logger.addHandler(_build_console_handler())


def setup_logging() -> None:
    _configure_named_logger("default", "default.log")
    _configure_named_logger("client", "client.log")
    _configure_named_logger("parser", "parser.log")
    _configure_named_logger("renderer", "renderer.log")

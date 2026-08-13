import logging
import sys

from core.config import settings


class ColorFormatter(logging.Formatter):
    COLORS = {
        "DEBUG": "\033[36m",
        "INFO": "\033[32m",
        "WARNING": "\033[33m",
        "ERROR": "\033[31m",
        "CRITICAL": "\033[35m",
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        levelname = record.levelname
        if sys.stderr.isatty() and levelname in self.COLORS:
            record.levelname = f"{self.COLORS[levelname]}{levelname}{self.RESET}"
        try:
            return super().format(record)
        finally:
            record.levelname = levelname


def setup_logging(level: str = settings.LOG_LEVEL) -> None:
    root_logger = logging.getLogger()
    if getattr(root_logger, "_estra_logging_configured", False):
        return

    root_logger.setLevel(level)
    handler = logging.StreamHandler()
    handler.setFormatter(
        ColorFormatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%H:%M:%S",
        )
    )

    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger._estra_logging_configured = True


def get_logger(name: str) -> logging.Logger:
    setup_logging()
    return logging.getLogger(name)

"""
SMCBot Logger
Handles all logging — console, file, and UI feed.
"""

import logging
import os
from datetime import datetime
from collections import deque

log_buffer = deque(maxlen=500)


class UIHandler(logging.Handler):
    LEVEL_COLORS = {
        "DEBUG": "neu",
        "INFO": "ok",
        "WARNING": "warn",
        "ERROR": "err",
        "CRITICAL": "err",
    }

    def emit(self, record):
        entry = {
            "time": datetime.utcnow().strftime("%H:%M:%S"),
            "level": record.levelname,
            "msg": self.format(record),
            "type": self.LEVEL_COLORS.get(record.levelname, "neu"),
        }
        log_buffer.append(entry)


def setup_logger(name: str = "smcbot", log_dir: str = "logs") -> logging.Logger:
    os.makedirs(log_dir, exist_ok=True)

    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    if logger.handlers:
        return logger

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(formatter)
    logger.addHandler(console)

    today = datetime.utcnow().strftime("%Y-%m-%d")
    file_handler = logging.FileHandler(
        os.path.join(log_dir, f"smcbot_{today}.log")
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    ui_handler = UIHandler()
    ui_handler.setLevel(logging.DEBUG)
    ui_handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(ui_handler)

    return logger


def get_recent_logs(n: int = 100) -> list:
    return list(log_buffer)[-n:]


logger = setup_logger()
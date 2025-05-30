import logging
import os
from datetime import datetime

def setup_logger():
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)

    # Get current date in your desired format
    date_str = datetime.now().strftime("%Y_%m_%d")
    log_filename = os.path.join(log_dir, f"log_{date_str}.txt")

    logger = logging.getLogger("sync_logger")
    logger.setLevel(logging.DEBUG)

    # Remove any existing file handlers so a fresh one is added daily
    for handler in logger.handlers[:]:
        if isinstance(handler, logging.FileHandler):
            logger.removeHandler(handler)

    # Add console handler only once
    if not any(isinstance(h, logging.StreamHandler) for h in logger.handlers):
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        formatter = logging.Formatter(
            '%(asctime)s — %(levelname)s — %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    # Always create a new file handler for today
    file_handler = logging.FileHandler(log_filename, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        '%(asctime)s — %(levelname)s — %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger

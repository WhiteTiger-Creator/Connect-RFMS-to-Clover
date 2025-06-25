import logging
import os
from logging.handlers import TimedRotatingFileHandler

def setup_logger():
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)

    logger = logging.getLogger("sync_logger")
    logger.setLevel(logging.DEBUG)

    # Clear existing handlers
    if logger.hasHandlers():
        logger.handlers.clear()

    # Console Handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s — %(levelname)s — %(message)s', '%Y-%m-%d %H:%M:%S')
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Rotating File Handler: rotates at midnight
    log_file = os.path.join(log_dir, "log.txt")
    file_handler = TimedRotatingFileHandler(
        log_file, when="midnight", interval=1, encoding="utf-8", backupCount=7
    )
    file_handler.suffix = "%Y_%m_%d"
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger

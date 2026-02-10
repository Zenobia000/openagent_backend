"""日誌工具"""
import logging
from config import LOGGING

def get_logger(name: str) -> logging.Logger:
    """獲取配置好的 logger"""
    logger = logging.getLogger(name)
    logger.setLevel(LOGGING["level"])

    handler = logging.StreamHandler()
    formatter = logging.Formatter(LOGGING["format"])
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger

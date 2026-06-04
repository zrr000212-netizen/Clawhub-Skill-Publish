import logging
from typing import Optional


def get_logger(name: str, log_level: str = "INFO") -> logging.Logger:
    """
    获取日志记录器

    Args:
        name: 日志记录器名称
        log_level: 日志级别

    Returns:
        日志记录器
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, log_level.upper()))

    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger

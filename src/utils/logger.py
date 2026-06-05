import logging
import os
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
        # 控制台输出
        console_handler = logging.StreamHandler()
        formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s")
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        # 文件输出
        log_file = os.path.join(os.getcwd(), "clawhub_publisher.log")
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger

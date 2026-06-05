import time
import random
import logging
from typing import Callable, Any
from functools import wraps


def retry_with_backoff(max_retries: int = 3, base_delay: float = 1.0):
    """
    指数退避重试装饰器

    Args:
        max_retries: 最大重试次数
        base_delay: 基础延迟时间（秒）
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            logger = logging.getLogger(func.__module__)
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    # 检查是否是不应该重试的错误
                    error_msg = str(e).lower()
                    if "version already exists" in error_msg:
                        logger.warning(f"[{func.__name__}] 版本已存在，不重试")
                        raise
                    if attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                        logger.warning(f"[{func.__name__}] 第 {attempt + 1} 次执行失败，{delay:.1f}s 后重试 (共 {max_retries} 次)，错误: {str(e)}")
                        time.sleep(delay)
                    else:
                        logger.error(f"[{func.__name__}] 第 {attempt + 1} 次执行失败，已达最大重试次数 {max_retries}，错误: {str(e)}")
            raise last_exception
        return wrapper
    return decorator

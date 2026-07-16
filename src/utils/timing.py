# src/utils/timing.py
"""计时工具 - 提供函数执行时间测量功能"""
import functools
import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


def timer(func: Any) -> Any:
    """计时装饰器 - 测量函数执行时间"""

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = time.perf_counter() - start
        logger.info(f"⏱ [{func.__name__}] 执行耗时: {elapsed:.2f}秒")
        return result

    return wrapper


def timer_with_result(func: Any) -> Any:
    """计时装饰器 - 测量执行时间并将耗时附加到返回值中"""

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = time.perf_counter() - start
        if isinstance(result, dict):
            result["_elapsed_time"] = round(elapsed, 2)
        logger.info(f"⏱ [{func.__name__}] 执行耗时: {elapsed:.2f}秒")
        return result

    return wrapper


class TimingContext:
    """计时上下文管理器"""

    def __init__(self, name: str = "代码块") -> None:
        self.name = name
        self.start_time: float = 0.0
        self.end_time: float = 0.0

    def __enter__(self) -> "TimingContext":
        self.start_time = time.perf_counter()
        logger.info(f"▶ [{self.name}] 开始执行...")
        return self

    def __exit__(self, *args: Any) -> None:
        self.end_time = time.perf_counter()
        elapsed = self.end_time - self.start_time
        logger.info(f"⏱ [{self.name}] 执行耗时: {elapsed:.2f}秒")


def time_it(name: str = "代码块") -> TimingContext:
    """创建计时上下文"""
    return TimingContext(name)
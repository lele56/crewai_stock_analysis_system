# src/tools/circuit_breaker.py
"""数据源断路器 — 故障源自动熔断，避免拖慢全链路"""

from __future__ import annotations

from collections.abc import Callable
from enum import Enum
import logging
import threading
import time
from typing import Any

from src.config import Config

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """断路器状态枚举"""
    CLOSED = "closed"          # 正常
    OPEN = "open"              # 熔断，跳过
    HALF_OPEN = "half_open"    # 试探中


class CircuitBreaker:
    """单个数据源的断路器

    状态机：
    CLOSED ──连续失败 N 次──▶ OPEN ──等待 T 秒──▶ HALF_OPEN
    HALF_OPEN ──成功──▶ CLOSED
    HALF_OPEN ──失败──▶ OPEN
    """

    _instances: dict[str, CircuitBreaker] = {}
    _lock = threading.Lock()

    def __init__(self, name: str) -> None:
        self.name = name
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = 0.0
        self.last_success_time = 0.0
        self.total_successes = 0
        self.total_failures = 0
        self._enabled = Config.CIRCUIT_BREAKER_ENABLED

    # ── 工厂方法 ─────────────────────────────────

    @classmethod
    def get(cls, name: str) -> CircuitBreaker:
        """获取或创建断路器实例"""
        with cls._lock:
            if name not in cls._instances:
                cls._instances[name] = cls(name)
            return cls._instances[name]

    @classmethod
    def all_status(cls) -> dict[str, dict[str, Any]]:
        """获取所有断路器状态"""
        return {
            name: cb.status()
            for name, cb in cls._instances.items()
        }

    # ── 核心逻辑 ─────────────────────────────────

    def allow_request(self) -> bool:
        """是否允许请求通过"""
        if not self._enabled:
            return True
        if self.state == CircuitState.CLOSED:
            return True
        if self.state == CircuitState.OPEN:
            if time.time() - self.last_failure_time >= Config.CIRCUIT_RECOVERY_TIMEOUT:
                logger.info(f"断路器 [{self.name}]: OPEN → HALF_OPEN (试探)")
                self.state = CircuitState.HALF_OPEN
                return True
            return False
        # HALF_OPEN: 允许一次试探
        return True

    def record_success(self) -> None:
        """记录成功"""
        self.failure_count = 0
        self.last_success_time = time.time()
        self.total_successes += 1
        if self.state == CircuitState.HALF_OPEN:
            logger.info(f"断路器 [{self.name}]: HALF_OPEN → CLOSED (恢复)")
            self.state = CircuitState.CLOSED
        elif self.state == CircuitState.OPEN:
            self.state = CircuitState.CLOSED

    def record_failure(self, error: str = "") -> None:
        """记录失败"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        self.total_failures += 1
        if self.failure_count >= Config.CIRCUIT_FAILURE_THRESHOLD and self.state == CircuitState.CLOSED:
            logger.warning(f"断路器 [{self.name}]: CLOSED → OPEN ({self.failure_count} 次失败, {error[:80]})")
            self.state = CircuitState.OPEN
        elif self.state == CircuitState.HALF_OPEN:
            logger.warning(f"断路器 [{self.name}]: HALF_OPEN → OPEN (试探失败)")
            self.state = CircuitState.OPEN

    def reset(self) -> None:
        """手动重置断路器"""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        logger.info(f"断路器 [{self.name}]: 手动重置")

    def status(self) -> dict[str, Any]:
        """获取状态信息"""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "total_successes": self.total_successes,
            "total_failures": self.total_failures,
            "last_failure": (
                time.strftime("%H:%M:%S", time.localtime(self.last_failure_time))
                if self.last_failure_time else None
            ),
            "last_success": (
                time.strftime("%H:%M:%S", time.localtime(self.last_success_time))
                if self.last_success_time else None
            ),
        }


# ── 装饰器 ──────────────────────────────────────

def with_circuit_breaker(source_name: str) -> Callable[..., Any]:
    """断路器装饰器 — 自动绕开已熔断的数据源"""

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            cb = CircuitBreaker.get(source_name)
            if not cb.allow_request():
                logger.debug(f"断路器 [{source_name}]: 已熔断，跳过")
                return None
            try:
                result = func(*args, **kwargs)
                cb.record_success()
                return result
            except Exception as e:
                cb.record_failure(str(e))
                raise
        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        return wrapper
    return decorator
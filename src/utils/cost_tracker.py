# src/utils/cost_tracker.py
"""LLM 成本追踪 — 按 Agent 统计调用次数，估算 token 消耗和费用

使用方式：
tracker = CostTracker()
tracker.reset()
agent = Agent(..., step_callback=tracker.step_callback("agent_name"))
... 执行分析 ...
tracker.summary()  # → {"total_calls": 24, "estimated_cost_usd": 0.0123}
"""

from __future__ import annotations

from collections.abc import Callable
import threading
import time
from typing import Any

# ── 模型定价（$/1M tokens） ──────────────────────────
# 生产环境建议用 OpenAI 官方 dashboard 数据
MODEL_PRICES: dict[str, tuple[float, float]] = {
    # OpenAI
    "gpt-4o": (2.50, 10.00),
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4-turbo": (10.00, 30.00),
    "gpt-4": (30.00, 60.00),
    "gpt-3.5-turbo": (0.50, 1.50),
    "o3-mini": (1.10, 4.40),
    # DeepSeek
    "deepseek-chat": (0.14, 0.28),
    "deepseek-reasoner": (0.55, 2.19),
    # Anthropic
    "claude-3-5-sonnet": (3.00, 15.00),
    "claude-3-haiku": (0.25, 1.25),
    "claude-3-opus": (15.00, 75.00),
    # Google
    "gemini-2.0-flash": (0.0, 0.0),
    "gemini-1.5-flash": (0.0, 0.0),
    "gemini-1.5-pro": (0.0, 0.0),
    "gemini-2.5-pro": (0.0, 0.0),
    # 国产
    "qwen-turbo": (0.0, 0.0),
    "qwen-plus": (0.0, 0.0),
    "glm-4-flash": (0.0, 0.0),
    "moonshot-v1-8k": (0.0, 0.0),
    # 默认
    "default": (0.0, 0.0),
}


class CostTracker:
    """全局单例成本追踪器"""

    _instance: CostTracker | None = None
    _lock = threading.Lock()

    def __new__(cls) -> CostTracker:
        """单例模式：确保全局只有一个追踪器实例"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._reset()
        return cls._instance

    def _reset(self) -> None:
        """初始化/重置追踪器内部状态"""
        self.per_agent: dict[str, dict[str, int]] = {}
        self.start_time = 0.0
        self._active = False
        self._llm_ref: Any = None
        self._fallback_used: list[str] = []

    def reset(self, llm: Any = None) -> None:
        """启动追踪器：记录开始时间，绑定 LLM 实例"""
        self._reset()
        self.start_time = time.perf_counter()
        self._active = True
        self._llm_ref = llm

    def step_callback(self, agent_name: str) -> Callable[..., Any]:
        """返回一个 step_callback 闭包，直接传给 Agent(step_callback=...)"""

        def callback(step_output: Any) -> None:
            if not self._active:
                return
            entry = self.per_agent.setdefault(agent_name, {"calls": 0, "input_chars": 0, "output_chars": 0})
            entry["calls"] += 1
            output_str = str(step_output) if step_output else ""
            entry["output_chars"] += len(output_str)
            # 粗略估算输入 token（prompt + tool output）
            entry["input_chars"] += len(output_str) * 2

        return callback

    def _resolve_model(self) -> str:
        """从 LLM 引用获取实际使用的模型名"""
        llm = self._llm_ref
        if isinstance(llm, str):
            return llm.split("/")[-1]
        return "default"

    def _record_fallback_if_any(self) -> None:
        """如果 LLM 发生了故障转移，记录到历史"""
        pass  # 当前版本通过字符串切换模型，无需记录

    def summary(self) -> dict[str, Any]:
        """获取成本汇总，自动识别实际使用的模型"""
        if not self._active:
            return {"active": False, "total_calls": 0, "estimated_cost_usd": 0}

        model_key = self._resolve_model()
        self._record_fallback_if_any()

        input_price, output_price = MODEL_PRICES.get(
            model_key,
            MODEL_PRICES.get("default", (0.0, 0.0)),
        )

        total_input = sum(v["input_chars"] for v in self.per_agent.values())
        total_output = sum(v["output_chars"] for v in self.per_agent.values())
        total_calls = sum(v["calls"] for v in self.per_agent.values())

        # 4 字符 ≈ 1 token（粗略估算）
        input_tokens = total_input / 4
        output_tokens = total_output / 4
        cost = (input_tokens / 1_000_000) * input_price + (output_tokens / 1_000_000) * output_price

        elapsed = round(time.perf_counter() - self.start_time, 1)

        return {
            "active": True,
            "model": model_key,
            "fallback_chain": self._fallback_used if self._fallback_used else None,
            "elapsed_seconds": elapsed,
            "total_calls": total_calls,
            "estimated_input_tokens": int(input_tokens),
            "estimated_output_tokens": int(output_tokens),
            "estimated_cost_usd": round(cost, 6),
            "cost_note": "免费模型" if cost == 0 else None,
            "per_agent": {
                name: {
                    "calls": v["calls"],
                    "estimated_input_tokens": int(v["input_chars"] / 4),
                    "estimated_output_tokens": int(v["output_chars"] / 4),
                }
                for name, v in self.per_agent.items()
            },
        }
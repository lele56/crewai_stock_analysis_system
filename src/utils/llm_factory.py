"""LLM 工厂 — 统一 LLM 创建入口

.env 配置示例：
LLM_MODEL=gemini/gemini-2.0-flash
LLM_FALLBACK=deepseek/deepseek-chat,openai/gpt-4o-mini
LLM_TEMPERATURE=0.1

环境变量方式切换模型：
LLM_MODEL=deepseek/deepseek-chat python main.py

注意：LLM_FALLBACK 目前仅用于记录，实际故障转移需要 CrewAI 原生支持。
临时切换模型直接改 LLM_MODEL 环境变量即可。
"""

from __future__ import annotations

import logging
import os

from crewai import LLM

from src.config import Config

logger = logging.getLogger(__name__)


def get_llm() -> LLM:
    """获取 LLM 实例（带 temperature 和 timeout 控制）"""
    model = Config.LLM_MODEL
    kwargs = {
        "model": model,
        "temperature": Config.LLM_TEMPERATURE,
        "max_tokens": Config.LLM_MAX_TOKENS,
        "timeout": Config.LLM_TIMEOUT,
        "api_key": Config.LLM_API_KEY or None,
        "base_url": Config.LLM_BASE_URL or None,
    }
    # 清理空值
    kwargs = {k: v for k, v in kwargs.items() if v is not None and v != ""}

    if Config.LLM_FALLBACK_LIST:
        logger.info(f"LLM 故障转移列表已配置: {model} -> {Config.LLM_FALLBACK_LIST}")

    llm = LLM(**kwargs)
    logger.info(f"LLM 初始化: {model}, temperature={Config.LLM_TEMPERATURE}, timeout={Config.LLM_TIMEOUT}s")
    return llm
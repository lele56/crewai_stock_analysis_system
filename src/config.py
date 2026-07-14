# src/config.py
"""
统一配置中心
所有LLM、Agent、缓存、路径等参数集中管理，一处修改全局生效
"""
import os
from pathlib import Path


class Config:
    """项目全局配置"""

    # ── 项目路径 ─────────────────────────────────
    PROJECT_ROOT = Path(__file__).resolve().parent.parent
    SRC_DIR = PROJECT_ROOT / "src"
    CONFIG_DIR = PROJECT_ROOT / "config"
    CACHE_DIR = PROJECT_ROOT / "cache"
    TEMPLATES_DIR = PROJECT_ROOT / "templates"
    REPORTS_DIR = PROJECT_ROOT / "reports"
    DATA_DIR = PROJECT_ROOT / "data"

    # ── LLM 配置 ─────────────────────────────────
    LLM_MODEL = os.getenv("OPENAI_MODEL_NAME", "gpt-4o-mini")
    LLM_API_KEY = os.getenv("OPENAI_API_KEY", "")
    LLM_BASE_URL = os.getenv("OPENAI_BASE_URL", "")
    LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.1"))
    LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "4096"))

    # ── Agent 通用配置 ───────────────────────────
    AGENT_MAX_ITER = int(os.getenv("AGENT_MAX_ITER", "3"))
    AGENT_ALLOW_DELEGATION = os.getenv("AGENT_ALLOW_DELEGATION", "false").lower() == "true"
    AGENT_VERBOSE = os.getenv("AGENT_VERBOSE", "true").lower() == "true"

    # ── Crew 配置 ────────────────────────────────
    CREW_PROCESS = os.getenv("CREW_PROCESS", "sequential")
    CREW_VERBOSE = os.getenv("CREW_VERBOSE", "false").lower() == "true"

    # ── 缓存配置 ─────────────────────────────────
    CACHE_ENABLED = os.getenv("CACHE_ENABLED", "true").lower() == "true"
    CACHE_TTL = int(os.getenv("CACHE_TTL", "86400"))  # 24小时

    # ── 并发与限流 ───────────────────────────────
    MAX_WORKERS = int(os.getenv("MAX_WORKERS", "2"))
    API_RETRY_COUNT = int(os.getenv("API_RETRY_COUNT", "3"))
    API_RETRY_DELAY = float(os.getenv("API_RETRY_DELAY", "1.0"))

    # ── 服务配置 ─────────────────────────────────
    FASTAPI_HOST = os.getenv("FASTAPI_HOST", "0.0.0.0")
    FASTAPI_PORT = int(os.getenv("FASTAPI_PORT", "8000"))
    FLASK_HOST = os.getenv("FLASK_HOST", "0.0.0.0")
    FLASK_PORT = int(os.getenv("FLASK_PORT", "5000"))

    # ── 工具配置 ─────────────────────────────────
    SERPER_API_KEY = os.getenv("SERPER_API_KEY", "")
    SERPER_ENABLED = os.getenv("SERPER_ENABLED", "true").lower() == "true"

    # ── 数据过滤配置 ─────────────────────────────
    FINANCIAL_DATA_YEARS = int(os.getenv("FINANCIAL_DATA_YEARS", "2"))

    # ── 日志配置 ─────────────────────────────────
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT = os.getenv("LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    # ── 数据源配置 ───────────────────────────────
    DATA_SOURCE_ORDER = ["tencent", "sina", "tickflow", "akshare", "tushare"]

    @classmethod
    def ensure_dirs(cls) -> None:
        """确保所有需要的目录存在"""
        for attr_name in dir(cls):
            if attr_name.endswith("_DIR"):
                dir_path = getattr(cls, attr_name)
                if isinstance(dir_path, Path):
                    dir_path.mkdir(parents=True, exist_ok=True)

    @classmethod
    def display(cls) -> str:
        """显示当前配置（隐藏敏感信息）"""
        lines = ["=== 当前配置 ==="]
        for attr_name in sorted(dir(cls)):
            if attr_name.startswith("_") or attr_name in ("ensure_dirs", "display"):
                continue
            value = getattr(cls, attr_name)
            if "KEY" in attr_name and value:
                value = value[:8] + "***" if len(str(value)) > 8 else "***"
            lines.append(f"  {attr_name} = {value}")
        return "\n".join(lines)
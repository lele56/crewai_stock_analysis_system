# src/config.py
"""统一配置中心
所有LLM、Agent、缓存、路径等参数集中管理，一处修改全局生效
"""

from enum import StrEnum
import os
from pathlib import Path


class AnalysisProfile(StrEnum):
    """分析深度配置

    rapid:    仅核心 Agent，跳过验证/协调类 Agent，适合快速扫描
    standard: 平衡模式，5+5+4=14 Agent，适合日常分析
    deep:     全量 Agent + 更多迭代，适合深度研究报告
    """
    RAPID = "rapid"
    STANDARD = "standard"
    DEEP = "deep"


class Config:
    """项目全局配置"""

    # ── 项目路径 ─────────────────────────────────
    PROJECT_ROOT = Path(__file__).resolve().parent.parent
    SRC_DIR = PROJECT_ROOT / "src"
    CREW_CONFIG_DIR = SRC_DIR / "crews" / "config"
    CACHE_DIR = PROJECT_ROOT / "cache"
    REPORTS_DIR = PROJECT_ROOT / "reports"

    # ── 分析深度 ─────────────────────────────────
    ANALYSIS_PROFILE = AnalysisProfile(os.getenv("ANALYSIS_PROFILE", "rapid"))

    # ── LLM 配置 ─────────────────────────────────
    LLM_MODEL = os.getenv("OPENAI_MODEL_NAME", "gpt-4o-mini")
    LLM_FALLBACK_LIST = [m.strip() for m in os.getenv("LLM_FALLBACK", "").split(",") if m.strip()]
    LLM_COST_TRACKING = os.getenv("LLM_COST_TRACKING", "false").lower() == "true"
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

    # ── Redis 配置 ───────────────────────────────
    REDIS_ENABLED = os.getenv("REDIS_ENABLED", "true").lower() == "true"
    REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_DB = int(os.getenv("REDIS_DB", "0"))
    REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "")
    REDIS_PREFIX = os.getenv("REDIS_PREFIX", "stock_analysis")
    REDIS_ANALYSIS_TTL = int(os.getenv("REDIS_ANALYSIS_TTL", "86400"))      # 分析结果 24h
    REDIS_COLLECTION_TTL = int(os.getenv("REDIS_COLLECTION_TTL", "3600"))   # 采集数据 1h

    # ── 并发与限流 ───────────────────────────────
    MAX_WORKERS = int(os.getenv("MAX_WORKERS", "2"))
    API_RETRY_COUNT = int(os.getenv("API_RETRY_COUNT", "3"))
    API_RETRY_DELAY = float(os.getenv("API_RETRY_DELAY", "1.0"))

    # ── 数据源熔断配置 ───────────────────────────
    CIRCUIT_BREAKER_ENABLED = os.getenv("CIRCUIT_BREAKER_ENABLED", "true").lower() == "true"
    CIRCUIT_FAILURE_THRESHOLD = int(os.getenv("CIRCUIT_FAILURE_THRESHOLD", "3"))
    CIRCUIT_RECOVERY_TIMEOUT = int(os.getenv("CIRCUIT_RECOVERY_TIMEOUT", "300"))  # 5 分钟
    SOURCE_TIMEOUT = int(os.getenv("SOURCE_TIMEOUT", "10"))  # 单数据源超时秒数

    # ── 阶段超时（秒） ───────────────────────────
    STAGE_TIMEOUT_DATA = int(os.getenv("STAGE_TIMEOUT_DATA", "180"))
    STAGE_TIMEOUT_ANALYSIS = int(os.getenv("STAGE_TIMEOUT_ANALYSIS", "300"))
    STAGE_TIMEOUT_DECISION = int(os.getenv("STAGE_TIMEOUT_DECISION", "180"))

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
    DATA_SOURCE_ORDER = ["tencent", "sina", "tickflow", "akshare"]

    # ── Profile → Agent 映射 ─────────────────────
    PROFILE_AGENTS_DATA = {
        AnalysisProfile.RAPID: ["market_researcher", "financial_data_expert", "financial_ratio_analyst", "technical_analyst"],
        AnalysisProfile.STANDARD: ["market_researcher", "financial_data_expert", "financial_ratio_analyst", "technical_analyst", "data_collection_coordinator"],
        AnalysisProfile.DEEP: ["market_researcher", "financial_data_expert", "financial_ratio_analyst", "technical_analyst", "data_collection_coordinator"],
    }
    PROFILE_AGENTS_ANALYSIS = {
        AnalysisProfile.RAPID: ["fundamental_analyst", "risk_assessment_specialist", "industry_expert"],
        AnalysisProfile.STANDARD: ["fundamental_analyst", "risk_assessment_specialist", "industry_expert", "analysis_coordinator"],
        AnalysisProfile.DEEP: ["fundamental_analyst", "risk_assessment_specialist", "industry_expert", "analysis_coordinator"],
    }
    PROFILE_AGENTS_DECISION = {
        AnalysisProfile.RAPID: ["investment_advisor"],
        AnalysisProfile.STANDARD: ["investment_advisor", "report_generator"],
        AnalysisProfile.DEEP: ["investment_advisor", "report_generator"],
    }
    PROFILE_MAX_ITER = {
        AnalysisProfile.RAPID: 2,
        AnalysisProfile.STANDARD: 3,
        AnalysisProfile.DEEP: 5,
    }

    @classmethod
    def get_profile_agents(cls, phase: str, profile: AnalysisProfile | None = None) -> list[str]:
        """获取指定 profile 下某阶段的 Agent 列表"""
        p = profile or cls.ANALYSIS_PROFILE
        mapping = {
            "data": cls.PROFILE_AGENTS_DATA,
            "analysis": cls.PROFILE_AGENTS_ANALYSIS,
            "decision": cls.PROFILE_AGENTS_DECISION,
        }
        return mapping.get(phase, {}).get(p, [])

    @classmethod
    def get_max_iter(cls, profile: AnalysisProfile | None = None) -> int:
        """获取指定 profile 的 max_iter"""
        p = profile or cls.ANALYSIS_PROFILE
        return cls.PROFILE_MAX_ITER.get(p, 3)

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
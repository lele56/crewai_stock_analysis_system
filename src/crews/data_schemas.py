# src/crews/data_schemas.py
"""数据收集阶段的结构化输出模型 — Pydantic v2

每个模型对应一个数据收集任务，用于 CrewAI 的 output_pydantic 强制结构化输出。
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class FinancialMetrics(BaseModel):
    """财务指标 — 来自 financial_data_collection + financial_ratio_calculation"""
    revenue: list[float] = Field(default_factory=list, description="近三年营收（亿元）")
    net_profit: list[float] = Field(default_factory=list, description="近三年净利润（亿元）")
    total_assets: float = 0.0
    total_liabilities: float = 0.0
    operating_cash_flow: float = 0.0
    gross_margin: float = Field(default=0.0, description="毛利率")
    net_margin: float = Field(default=0.0, description="净利率")
    roe: float = Field(default=0.0, description="ROE")
    roa: float = Field(default=0.0, description="ROA")
    debt_ratio: float = Field(default=0.0, description="资产负债率")
    current_ratio: float = Field(default=0.0, description="流动比率")
    quick_ratio: float = Field(default=0.0, description="速动比率")
    revenue_growth: float = Field(default=0.0, description="营收同比增长率")
    profit_growth: float = Field(default=0.0, description="净利润同比增长率")
    pe: float = Field(default=0.0, description="市盈率")
    pb: float = Field(default=0.0, description="市净率")
    ps: float = Field(default=0.0, description="市销率")
    market_cap: float = Field(default=0.0, description="总市值（亿元）")
    dividend_yield: float = Field(default=0.0, description="股息率")

    def to_prompt_text(self) -> str:
        """格式化为分析 Agent 的 prompt 文本"""
        lines = ["【财务指标】"]
        if self.revenue:
            lines.append(f"  近三年营收(亿): {self.revenue}")
        if self.net_profit:
            lines.append(f"  近三年净利润(亿): {self.net_profit}")
        if self.total_assets:
            lines.append(f"  总资产(亿): {self.total_assets}")
        if self.total_liabilities:
            lines.append(f"  总负债(亿): {self.total_liabilities}")
        if self.operating_cash_flow:
            lines.append(f"  经营现金流(亿): {self.operating_cash_flow}")
        if self.gross_margin:
            lines.append(f"  毛利率: {self.gross_margin:.1%}")
        if self.net_margin:
            lines.append(f"  净利率: {self.net_margin:.1%}")
        if self.roe:
            lines.append(f"  ROE: {self.roe:.1%}")
        if self.roa:
            lines.append(f"  ROA: {self.roa:.1%}")
        if self.debt_ratio:
            lines.append(f"  资产负债率: {self.debt_ratio:.1%}")
        if self.current_ratio:
            lines.append(f"  流动比率: {self.current_ratio:.2f}")
        if self.quick_ratio:
            lines.append(f"  速动比率: {self.quick_ratio:.2f}")
        if self.revenue_growth:
            lines.append(f"  营收增长率: {self.revenue_growth:.1%}")
        if self.profit_growth:
            lines.append(f"  利润增长率: {self.profit_growth:.1%}")
        if self.pe:
            lines.append(f"  PE: {self.pe:.1f}")
        if self.pb:
            lines.append(f"  PB: {self.pb:.1f}")
        if self.ps:
            lines.append(f"  PS: {self.ps:.1f}")
        if self.market_cap:
            lines.append(f"  总市值(亿): {self.market_cap:.0f}")
        if self.dividend_yield:
            lines.append(f"  股息率: {self.dividend_yield:.1%}")
        return "\n".join(lines)

    def is_empty(self) -> bool:
        """检查财务数据是否为空"""
        return not any([self.revenue, self.net_profit, self.roe, self.pe])


class MarketData(BaseModel):
    """市场数据 — 来自 market_research"""
    price: float = Field(default=0.0, description="当前股价")
    change_pct: float = Field(default=0.0, description="涨跌幅")
    volume: float = Field(default=0.0, description="成交量（手）")
    avg_volume_20d: float = Field(default=0.0, description="20日均量")
    high_52w: float = Field(default=0.0, description="52周最高")
    low_52w: float = Field(default=0.0, description="52周最低")
    beta: float = Field(default=0.0, description="Beta系数")
    volatility_30d: float = Field(default=0.0, description="30日波动率")

    def to_prompt_text(self) -> str:
        """格式化为分析 Agent 的 prompt 文本"""
        lines = ["【市场数据】"]
        if self.price:
            lines.append(f"  当前股价: {self.price}")
        if self.change_pct:
            lines.append(f"  涨跌幅: {self.change_pct:+.2%}")
        if self.volume:
            lines.append(f"  成交量(手): {self.volume:,.0f}")
        if self.avg_volume_20d:
            lines.append(f"  20日均量: {self.avg_volume_20d:,.0f}")
        if self.high_52w:
            lines.append(f"  52周高: {self.high_52w}")
        if self.low_52w:
            lines.append(f"  52周低: {self.low_52w}")
        if self.beta:
            lines.append(f"  Beta: {self.beta:.2f}")
        if self.volatility_30d:
            lines.append(f"  30日波动率: {self.volatility_30d:.1%}")
        return "\n".join(lines)

    def is_empty(self) -> bool:
        """检查市场数据是否为空"""
        return self.price == 0.0


class TechnicalData(BaseModel):
    """技术指标 — 来自 technical_data_collection"""
    ma_5: float = 0.0
    ma_20: float = 0.0
    ma_50: float = 0.0
    ma_200: float = 0.0
    rsi_14: float = Field(default=0.0, description="14日RSI")
    macd: float = 0.0
    macd_signal: float = 0.0
    macd_histogram: float = 0.0
    bollinger_upper: float = 0.0
    bollinger_middle: float = 0.0
    bollinger_lower: float = 0.0
    atr_14: float = Field(default=0.0, description="14日ATR")

    def to_prompt_text(self) -> str:
        """格式化为分析 Agent 的 prompt 文本"""
        lines = ["【技术指标】"]
        if self.ma_5:
            lines.append(f"  MA5: {self.ma_5:.2f}")
        if self.ma_20:
            lines.append(f"  MA20: {self.ma_20:.2f}")
        if self.ma_50:
            lines.append(f"  MA50: {self.ma_50:.2f}")
        if self.ma_200:
            lines.append(f"  MA200: {self.ma_200:.2f}")
        if self.rsi_14:
            lines.append(f"  RSI(14): {self.rsi_14:.1f}")
        if self.macd:
            lines.append(f"  MACD: {self.macd:.4f}  Signal: {self.macd_signal:.4f}  Hist: {self.macd_histogram:.4f}")
        if self.bollinger_upper:
            bb = f"{self.bollinger_lower:.2f} / {self.bollinger_middle:.2f} / {self.bollinger_upper:.2f}"
            lines.append(f"  布林带: {bb}")
        if self.atr_14:
            lines.append(f"  ATR(14): {self.atr_14:.2f}")
        return "\n".join(lines)

    def is_empty(self) -> bool:
        """检查技术指标是否为空"""
        return not any([self.rsi_14, self.ma_20, self.ma_50])


class IndustryData(BaseModel):
    """行业数据 — 来自 market_research"""
    sector: str = Field(default="", description="板块")
    industry: str = Field(default="", description="行业")
    market_position: str = Field(default="", description="行业地位")
    market_share: float = Field(default=0.0, description="市场份额")
    competitors: list[str] = Field(default_factory=list, description="主要竞争对手")
    industry_growth: float = Field(default=0.0, description="行业增长率")
    industry_size: float = Field(default=0.0, description="行业规模（亿元）")
    trends: str = Field(default="", description="发展趋势")
    opportunities: str = Field(default="", description="机遇")
    threats: str = Field(default="", description="挑战")

    def to_prompt_text(self) -> str:
        """格式化为分析 Agent 的 prompt 文本"""
        lines = ["【行业数据】"]
        if self.sector:
            lines.append(f"  板块: {self.sector}")
        if self.industry:
            lines.append(f"  行业: {self.industry}")
        if self.market_position:
            lines.append(f"  行业地位: {self.market_position}")
        if self.market_share:
            lines.append(f"  市场份额: {self.market_share:.1%}")
        if self.competitors:
            lines.append(f"  竞争对手: {', '.join(self.competitors)}")
        if self.industry_growth:
            lines.append(f"  行业增长率: {self.industry_growth:.1%}")
        if self.industry_size:
            lines.append(f"  行业规模(亿): {self.industry_size:.0f}")
        if self.trends:
            lines.append(f"  趋势: {self.trends}")
        if self.opportunities:
            lines.append(f"  机遇: {self.opportunities}")
        if self.threats:
            lines.append(f"  挑战: {self.threats}")
        return "\n".join(lines)

    def is_empty(self) -> bool:
        """检查行业数据是否为空"""
        return len(self.sector) == 0


class CollectionData(BaseModel):
    """数据收集阶段的完整结构化输出"""
    company: str = ""
    ticker: str = ""
    financial: FinancialMetrics = Field(default_factory=FinancialMetrics)
    market: MarketData = Field(default_factory=MarketData)
    technical: TechnicalData = Field(default_factory=TechnicalData)
    industry: IndustryData = Field(default_factory=IndustryData)

    @property
    def is_effectively_empty(self) -> bool:
        """检查是否所有关键数据都为空"""
        has_financial = any([
            self.financial.revenue, self.financial.net_profit, self.financial.roe,
            self.financial.roa, self.financial.revenue_growth, self.financial.pe,
        ])
        has_market = self.market.price > 0
        has_technical = any([self.technical.rsi_14, self.technical.ma_20, self.technical.ma_50])
        has_industry = len(self.industry.sector) > 0
        return not (has_financial or has_market or has_technical or has_industry)

    def to_financial_prompt(self) -> str:
        """生成基本面分析 prompt 文本"""
        return "\n\n".join([self.financial.to_prompt_text()])

    def to_risk_prompt(self) -> str:
        """生成风险评估 prompt 文本"""
        return "\n\n".join([self.market.to_prompt_text(), self.technical.to_prompt_text()])

    def to_industry_prompt(self) -> str:
        """生成行业分析 prompt 文本"""
        return "\n\n".join([self.market.to_prompt_text(), self.industry.to_prompt_text()])

    def to_market_prompt(self) -> str:
        """生成市场数据 prompt 文本"""
        return self.market.to_prompt_text()

    def to_technical_prompt(self) -> str:
        """生成技术指标 prompt 文本"""
        return self.technical.to_prompt_text()


# ── output_pydantic 专用模型：每个任务对应一个 ──

class MarketResearchOutput(BaseModel):
    """market_research 任务输出 — 合并市场 + 行业数据"""
    price: float = Field(default=0.0, description="当前股价")
    change_pct: float = Field(default=0.0, description="涨跌幅（小数，如 0.05 表示 +5%）")
    volume: float = Field(default=0.0, description="成交量（手）")
    avg_volume_20d: float = Field(default=0.0, description="20日均量")
    high_52w: float = Field(default=0.0, description="52周最高价")
    low_52w: float = Field(default=0.0, description="52周最低价")
    beta: float = Field(default=0.0, description="Beta系数")
    volatility_30d: float = Field(default=0.0, description="30日波动率（小数）")
    sector: str = Field(default="", description="板块名称")
    industry: str = Field(default="", description="行业名称")
    market_position: str = Field(default="", description="行业地位：龙头/领先/跟随/挑战者")
    market_share: float = Field(default=0.0, description="市场份额（小数）")
    competitors: list[str] = Field(default_factory=list, description="主要竞争对手")
    industry_growth: float = Field(default=0.0, description="行业增长率（小数）")
    industry_size: float = Field(default=0.0, description="行业规模（亿元）")
    trends: str = Field(default="", description="行业发展趋势")
    opportunities: str = Field(default="", description="发展机遇")
    threats: str = Field(default="", description="面临挑战")


class FinancialDataOutput(BaseModel):
    """financial_data_collection 任务输出"""
    revenue: list[float] = Field(default_factory=list, description="近三年营收（亿元）")
    net_profit: list[float] = Field(default_factory=list, description="近三年净利润（亿元）")
    total_assets: float = Field(default=0.0, description="总资产（亿元）")
    total_liabilities: float = Field(default=0.0, description="总负债（亿元）")
    operating_cash_flow: float = Field(default=0.0, description="经营现金流（亿元）")
    gross_margin: float = Field(default=0.0, description="毛利率（小数）")
    net_margin: float = Field(default=0.0, description="净利率（小数）")
    roe: float = Field(default=0.0, description="ROE（小数）")
    roa: float = Field(default=0.0, description="ROA（小数）")
    debt_ratio: float = Field(default=0.0, description="资产负债率（小数）")
    current_ratio: float = Field(default=0.0, description="流动比率")
    quick_ratio: float = Field(default=0.0, description="速动比率")
    revenue_growth: float = Field(default=0.0, description="营收同比增长率（小数）")
    profit_growth: float = Field(default=0.0, description="净利润同比增长率（小数）")
    pe: float = Field(default=0.0, description="市盈率")
    pb: float = Field(default=0.0, description="市净率")
    ps: float = Field(default=0.0, description="市销率")
    market_cap: float = Field(default=0.0, description="总市值（亿元）")
    dividend_yield: float = Field(default=0.0, description="股息率（小数）")


class FinancialRatioOutput(FinancialDataOutput):
    """financial_ratio_calculation 任务输出 — 与 FinancialDataOutput 字段相同，语义上表示经计算的比率"""


class TechnicalDataOutput(BaseModel):
    """technical_data_collection 任务输出"""
    ma_5: float = Field(default=0.0, description="5日均线")
    ma_20: float = Field(default=0.0, description="20日均线")
    ma_50: float = Field(default=0.0, description="50日均线")
    ma_200: float = Field(default=0.0, description="200日均线")
    rsi_14: float = Field(default=0.0, description="14日RSI")
    macd: float = Field(default=0.0, description="MACD值")
    macd_signal: float = Field(default=0.0, description="MACD信号线")
    macd_histogram: float = Field(default=0.0, description="MACD柱")
    bollinger_upper: float = Field(default=0.0, description="布林带上轨")
    bollinger_middle: float = Field(default=0.0, description="布林带中轨")
    bollinger_lower: float = Field(default=0.0, description="布林带下轨")
    atr_14: float = Field(default=0.0, description="14日ATR")
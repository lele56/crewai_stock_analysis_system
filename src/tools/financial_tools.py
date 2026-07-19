# src/tools/financial_tools.py
"""金融数据工具包 - 包含财务计算等工具"""

import json
import logging

from src.tools.financial_calculations import (
    calculate_dcf,
    calculate_growth_rates,
    calculate_leverage_ratios,
    calculate_liquidity_ratios,
    calculate_profitability_ratios,
    calculate_valuation_ratios,
    find_yoy_previous,
    parse_report_text,
)
from src.tools.reporting_tools import BaseTool

logger = logging.getLogger(__name__)

# 模块级缓存，避免同一进程内重复调 API
_financial_api_cache: dict[str, dict] = {}


def _enrich_market_data(ticker: str, data: dict[str, float]) -> None:
    """从 stock_cache 的 info 补充市场数据（PE/PB/市值/当前价格），不覆盖已有字段"""
    try:
        from src.tools.akshare_data_cache import load_stock_cache

        cache = load_stock_cache(ticker)
        if not cache:
            return
        info = cache.get("info", {})
        if not info:
            return

        _mappings = [
            ("trailingPE", "pe_ratio"),
            ("priceToBook", "pb_ratio"),
            ("marketCap", "market_cap"),
            ("currentPrice", "current_price"),
        ]
        for info_key, data_key in _mappings:
            if data_key in data:
                continue
            val = info.get(info_key)
            if val is not None and val != "N/A":
                try:
                    fval = float(val)
                    if fval > 0:
                        data[data_key] = fval
                except (ValueError, TypeError):
                    pass
    except Exception as e:
        logger.debug("补充市场数据失败: %s", str(e)[:50])


class FinancialCalculatorTool(BaseTool):
    """金融计算器工具 — 优先从 API 直接获取财务数据，兜底用正则从文本提取"""

    name: str = "Financial Calculator Tool"
    description: str = (
        "计算财务指标和比率。参数: ticker(股票代码), financial_data(可选文本), "
        "calculation_type(可选: liquidity,profitability,leverage,growth,dcf,valuation,all)"
    )

    def _run(
        self,
        ticker: str = "",
        financial_data: str = "",
        calculation_type: str = "all",
    ) -> str:
        try:
            data = {}
            # 优先：直接从 API 获取真实财务数据
            if ticker:
                data = self._fetch_financial_from_api(ticker)
                if data:
                    logger.info("从 API 获取财务数据成功，跳过文本解析")

            # 兜底：从文本中提取（兼容 CrewAI 可能传入 dict 的情况）
            if not data and financial_data:
                if isinstance(financial_data, dict):
                    data = financial_data
                elif isinstance(financial_data, str) and financial_data.strip():
                    data = self._parse_financial_data(financial_data)

            if not data:
                logger.warning("财务数据为空，无法计算")
                return "财务数据为空，请先通过 AkShare Data Tool 获取股票数据"

            logger.info(f"开始计算财务指标，类型: {calculation_type}, 数据键: {list(data.keys())[:10]}")

            results = {}

            ct = calculation_type.lower()
            calc_types = {t.strip() for t in ct.split(",") if t.strip()}

            if "liquidity" in calc_types or "all" in calc_types:
                results["liquidity_ratios"] = calculate_liquidity_ratios(data)

            if "profitability" in calc_types or "all" in calc_types:
                results["profitability_ratios"] = calculate_profitability_ratios(data)

            if "leverage" in calc_types or "all" in calc_types:
                results["leverage_ratios"] = calculate_leverage_ratios(data)

            if "growth" in calc_types or "all" in calc_types:
                results["growth_rates"] = calculate_growth_rates(data)

            if "dcf" in calc_types or "all" in calc_types:
                results["dcf_valuation"] = calculate_dcf(data)

            if "valuation" in calc_types or "all" in calc_types:
                results["valuation_ratios"] = calculate_valuation_ratios(data)

            report = self._generate_financial_report(results)
            logger.info("财务指标计算完成")
            return report

        except Exception as e:
            error_msg = f"财务指标计算失败: {str(e)}"
            logger.error(error_msg)
            return error_msg

    def _parse_financial_data(self, financial_data: str) -> dict:
        """解析财务数据，支持JSON和文本报告两种格式"""
        try:
            data = json.loads(financial_data)
            if isinstance(data, dict) and data:
                return data
        except json.JSONDecodeError:
            logger.debug("JSON 解析失败，回退文本解析")

        data = parse_report_text(financial_data)
        if data:
            return data
        return {"raw": financial_data}

    @staticmethod
    def _fetch_financial_from_api(ticker: str) -> dict:
        """获取财务数据：优先三级缓存，缓存未命中则调 API 并回写缓存；
        同时补充市场数据（PE/PB/市值/价格）供估值和 DCF 使用
        """
        from src.tools.akshare_data_cache import (
            _FINANCIAL_KEY_MAP,
            _FINANCIAL_PREV_MAP,
            _safe_float,
            load_financial_from_cache,
            load_stock_cache,
            save_financial_cache,
        )
        from src.tools.akshare_data_parser import get_financial_statements

        # L0: 模块级内存缓存（最快，避免重复调用 load_financial_from_cache）
        if ticker in _financial_api_cache:
            return _financial_api_cache[ticker]

        data: dict[str, float] = {}

        # L1/L2: 三级缓存（内存 → Redis → 文件）
        cached = load_financial_from_cache(ticker)
        if cached:
            data = cached
            # 从主缓存补充上一期数据，用于增长率计算
            if "previous_revenue" not in data:
                stock_cache = load_stock_cache(ticker)
                if stock_cache:
                    for section in ["financials", "balance_sheet"]:
                        records = stock_cache.get(section, [])
                        if len(records) > 1:
                            prev_row = find_yoy_previous(records)
                            if prev_row is None:
                                prev_row = records[1]
                            for cn, en in _FINANCIAL_PREV_MAP.items():
                                if cn in prev_row and en not in data:
                                    val = _safe_float(prev_row[cn])
                                    if val is not None:
                                        data[en] = val

        # L3: 直接调 API（key mapping 与 load_financial_from_cache 保持一致）
        if not data:
            try:
                raw: dict[str, float] = {}
                prev_raw: dict[str, float] = {}
                for stype in ["利润表", "资产负债表", "现金流量表"]:
                    df = get_financial_statements(ticker, stype)
                    if not df.empty:
                        record = df.iloc[0].to_dict()
                        for k, v in record.items():
                            val = _safe_float(v)
                            if val is not None:
                                raw[k] = val
                        # 上一期数据（同比匹配，用于增长率计算）
                        if len(df) > 1:
                            records = df.reset_index().to_dict(orient="records")
                            # 确保 REPORT_DATE 在 records 中
                            if "REPORT_DATE" not in records[0] and df.index.name == "REPORT_DATE":
                                for i, rec in enumerate(records):
                                    rec["REPORT_DATE"] = str(df.index[i])
                            prev_record = find_yoy_previous(records)
                            if prev_record is None:
                                prev_record = df.iloc[1].to_dict()
                            for k, v in prev_record.items():
                                pval = _safe_float(v)
                                if pval is not None:
                                    prev_raw[k] = pval

                for cn, en in _FINANCIAL_KEY_MAP.items():
                    if cn in raw:
                        data[en] = raw[cn]

                # 上一期数据映射（使用模块级共享 _FINANCIAL_PREV_MAP）
                for cn, en in _FINANCIAL_PREV_MAP.items():
                    if cn in prev_raw:
                        data[en] = prev_raw[cn]

                # 毛利 = 营收 - 营业成本
                revenue = data.get("revenue", 0)
                operating_cost = data.get("operating_cost", 0)
                if revenue > 0 and operating_cost > 0:
                    data["gross_profit"] = revenue - operating_cost

                if data:
                    save_financial_cache(ticker, data)
                    logger.info("直接从 API 获取财务数据成功")
            except Exception as e:
                logger.warning("直接调 API 获取财务数据失败: %s", str(e)[:80])

        # 补充市场数据（PE/PB/市值/当前价格），从 stock_cache 的 info 中提取
        if data:
            _enrich_market_data(ticker, data)
            _financial_api_cache[ticker] = data

        return data

    def _generate_financial_report(self, results: dict) -> str:
        """生成财务指标报告（精简版，避免 LLM 上下文溢出）"""
        _pct_keys = {"roa", "roe", "debt_to_assets", "price_return"}

        def _fmt(ratio_name: str, value: float) -> str:
            if "growth" in ratio_name or "margin" in ratio_name or ratio_name in _pct_keys:
                return f"{value:.2f}%"
            if ratio_name == "estimated_intrinsic_value":
                if abs(value) >= 1e8:
                    return f"{value / 1e8:.2f}亿"
                if abs(value) >= 1e4:
                    return f"{value / 1e4:.2f}万"
                return f"{value:.2f}"
            if ratio_name == "price_to_intrinsic":
                return f"{value:.4f}"
            return f"{value:.2f}"

        lines = []
        for category, ratios in results.items():
            if not ratios:
                continue
            cat_name = category.replace("_", " ").title()
            items = []
            for ratio_name, value in ratios.items():
                name = self._translate_ratio_name(ratio_name)
                items.append(f"{name}: {_fmt(ratio_name, value)}")
            if items:
                lines.append(f"{cat_name}: " + ", ".join(items))
        return "\n".join(lines) if lines else "无可用数据"

    def _translate_ratio_name(self, ratio_name: str) -> str:
        """翻译财务指标名称"""
        translations = {
            "current_ratio": "流动比率",
            "quick_ratio": "速动比率",
            "cash_ratio": "现金比率",
            "gross_margin": "毛利率",
            "net_margin": "净利率",
            "roa": "资产收益率",
            "roe": "净资产收益率",
            "debt_to_assets": "资产负债率",
            "equity_multiplier": "权益乘数",
            "interest_coverage": "利息保障倍数",
            "revenue_growth": "营收增长率",
            "net_income_growth": "净利润增长率",
            "asset_growth": "资产增长率",
            "price_return": "价格涨幅",
            # DCF / 估值
            "estimated_intrinsic_value": "估算内在价值",
            "price_to_intrinsic": "价格/内在价值比",
            "pe_ratio": "市盈率",
            "pb_ratio": "市净率",
            "market_cap_to_net_income": "市值/净利润",
            "ps_ratio": "市销率",
        }
        return translations.get(ratio_name, ratio_name)


# 使用示例
if __name__ == "__main__":
    from src.tools.akshare_tools import AkShareTool

    ak_tool = AkShareTool()
    logger.info("=== 测试AkShare工具 ===")
    result = ak_tool._run("sh600000", "6mo")
    logger.info(result[:500] + "...")

    calc_tool = FinancialCalculatorTool()
    logger.info("=== 测试金融计算器工具 ===")
    test_data = {
        "current_assets": 1000000,
        "current_liabilities": 500000,
        "inventory": 200000,
        "cash": 300000,
        "revenue": 2000000,
        "gross_profit": 800000,
        "net_income": 400000,
        "total_assets": 3000000,
        "equity": 1500000,
        "total_debt": 1000000,
    }
    import json

    calc_result = calc_tool._run(json.dumps(test_data))
    logger.info(calc_result)
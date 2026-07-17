# src/tools/financial_tools.py
"""金融数据工具包 - 包含财务计算等工具"""

from datetime import datetime
import json
import logging
import re

from src.tools.reporting_tools import BaseTool

logger = logging.getLogger(__name__)

# 模块级缓存，避免同一进程内重复调 API
_financial_api_cache: dict[str, dict] = {}


def _enrich_market_data(ticker: str, data: dict[str, float]) -> None:
    """从 stock_cache 的 info 补充市场数据（PE/PB/市值/当前价格），不覆盖已有字段"""
    try:
        from src.tools.akshare_data_parser import load_stock_cache

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
            calc_types = set(t.strip() for t in ct.split(",") if t.strip())

            if "liquidity" in calc_types or "all" in calc_types:
                results["liquidity_ratios"] = self._calculate_liquidity_ratios(data)

            if "profitability" in calc_types or "all" in calc_types:
                results["profitability_ratios"] = self._calculate_profitability_ratios(data)

            if "leverage" in calc_types or "all" in calc_types:
                results["leverage_ratios"] = self._calculate_leverage_ratios(data)

            if "growth" in calc_types or "all" in calc_types:
                results["growth_rates"] = self._calculate_growth_rates(data)

            if "dcf" in calc_types or "all" in calc_types:
                results["dcf_valuation"] = self._calculate_dcf(data)

            if "valuation" in calc_types or "all" in calc_types:
                results["valuation_ratios"] = self._calculate_valuation_ratios(data)

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
            pass

        data = self._parse_report_text(financial_data)
        if data:
            return data
        return {"raw": financial_data}

    @staticmethod
    def _find_yoy_previous(records: list[dict]) -> dict | None:
        """从 record 列表中找同比（同月）上一期数据。
        records[0] 是最新一期，返回同月的前一年记录；找不到则返回 records[1]。
        """
        if len(records) < 2:
            return None
        current = records[0]
        date_str = current.get("REPORT_DATE", "") or current.get("报告期", "") or current.get("report_date", "")
        if not date_str:
            return records[1]
        try:
            dt = datetime.strptime(str(date_str)[:10], "%Y-%m-%d")
            target_month = dt.month
            target_year = dt.year - 1
            for record in records[1:]:
                rd = record.get("REPORT_DATE", "") or record.get("报告期", "") or record.get("report_date", "")
                if not rd:
                    continue
                try:
                    rd_dt = datetime.strptime(str(rd)[:10], "%Y-%m-%d")
                    if rd_dt.month == target_month and rd_dt.year == target_year:
                        return record
                except ValueError:
                    continue
        except (ValueError, IndexError):
            pass
        return records[1]

    @staticmethod
    def _fetch_financial_from_api(ticker: str) -> dict:
        """获取财务数据：优先三级缓存，缓存未命中则调 API 并回写缓存；
        同时补充市场数据（PE/PB/市值/价格）供估值和 DCF 使用"""
        from src.tools.akshare_data_parser import (
            load_financial_from_cache, load_stock_cache,
            save_financial_cache, get_financial_statements, _safe_float,
            _FINANCIAL_KEY_MAP, _FINANCIAL_PREV_MAP,
        )

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
                            prev_row = FinancialCalculatorTool._find_yoy_previous(records)
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
                            prev_record = FinancialCalculatorTool._find_yoy_previous(records)
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

    def _parse_report_text(self, text: str) -> dict:
        """从股票数据报告文本中提取结构化财务数据"""
        result = {}

        def _extract_number(pattern: str, source: str = text) -> float:
            m = re.search(pattern, source)
            if m:
                num_str = m.group(1).replace(",", "").replace("，", "").replace("元", "").strip()
                try:
                    return float(num_str)
                except ValueError:
                    pass
            return 0.0

        result["revenue"] = _extract_number(r"(?:最新营收|营业总收入|营业收入)\**\*?\s*[：:]\s*([\d,]+\.?\d*)")
        result["net_income"] = _extract_number(r"(?:最新净利润|净利润)\**\*?\s*[：:]\s*([\d,]+\.?\d*)")

        gross_margin_str = None
        m = re.search(r"毛利率\**[：:]\s*([\d.]+)%", text)
        if m:
            gross_margin_str = m.group(1)
            result["gross_margin"] = float(gross_margin_str)
        if "revenue" in result and result["revenue"] > 0 and "gross_margin" in result:
            result["gross_profit"] = result["revenue"] * result["gross_margin"] / 100.0

        result["current_assets"] = _extract_number(r"流动资产\**[：:]\s*([\d,]+\.?\d*)")
        result["current_liabilities"] = _extract_number(r"流动负债\**[：:]\s*([\d,]+\.?\d*)")
        result["total_assets"] = _extract_number(r"资产总计\**[：:]\s*([\d,]+\.?\d*)")
        result["total_debt"] = _extract_number(r"负债合计\**[：:]\s*([\d,]+\.?\d*)")
        result["inventory"] = _extract_number(r"存货\**[：:]\s*([\d,]+\.?\d*)")
        result["cash"] = _extract_number(r"货币资金\**[：:]\s*([\d,]+\.?\d*)")
        result["equity"] = _extract_number(r"股东权益\**[：:]\s*([\d,]+\.?\d*)")

        result["operating_cashflow"] = _extract_number(r"经营活动现金流量净额\**[：:]\s*([\d,-]+\.?\d*)")
        result["investing_cashflow"] = _extract_number(r"投资活动现金流量净额\**[：:]\s*([\d,-]+\.?\d*)")
        result["financing_cashflow"] = _extract_number(r"筹资活动现金流量净额\**[：:]\s*([\d,-]+\.?\d*)")

        operating_profit = _extract_number(r"营业利润\**[：:]\s*([\d,]+\.?\d*)")
        if operating_profit > 0:
            result["operating_profit"] = operating_profit
        result["interest_expense"] = _extract_number(r"利息费用\**[：:]\s*([\d,]+\.?\d*)")

        mktcap = _extract_number(r"市值\**[：:]\s*¥?([\d,]+\.?\d*)")
        if mktcap > 0:
            result["market_cap"] = mktcap

        price = _extract_number(r"当前价格\**[：:]\s*¥?([\d.]+)")
        if price > 0:
            result["current_price"] = price

        pe = _extract_number(r"市盈率\**[：:]\s*([\d.]+)")
        if pe > 0:
            result["pe_ratio"] = pe

        pb = _extract_number(r"市净率\**[：:]\s*([\d.]+)")
        if pb > 0:
            result["pb_ratio"] = pb

        period_return = _extract_number(r"(?:期间)?涨幅\**[：:]\s*([\d.-]+)%")
        if "period_return" not in result:
            result["period_return"] = period_return

        logger.info(
            "从报告中提取财务数据: revenue=%s, net_income=%s, total_assets=%s, equity=%s",
            result.get("revenue"), result.get("net_income"),
            result.get("total_assets"), result.get("equity"),
        )
        return result

    def _calculate_liquidity_ratios(self, data: dict) -> dict[str, float]:
        """计算流动性比率"""
        ratios = {}

        try:
            # 流动比率
            current_assets = data.get("current_assets", 0)
            current_liabilities = data.get("current_liabilities", 0)
            if current_liabilities > 0:
                ratios["current_ratio"] = current_assets / current_liabilities

            # 速动比率
            inventory = data.get("inventory", 0)
            quick_assets = current_assets - inventory
            if current_liabilities > 0:
                ratios["quick_ratio"] = quick_assets / current_liabilities

            # 现金比率
            cash = data.get("cash", 0)
            if current_liabilities > 0:
                ratios["cash_ratio"] = cash / current_liabilities

        except Exception as e:
            logger.error(f"计算流动性比率失败: {str(e)}")

        return ratios

    def _calculate_profitability_ratios(self, data: dict) -> dict[str, float]:
        """计算盈利能力比率"""
        ratios = {}

        try:
            # 毛利率
            revenue = data.get("revenue", 0)
            gross_profit = data.get("gross_profit", 0)
            if revenue > 0:
                ratios["gross_margin"] = (gross_profit / revenue) * 100

            # 净利率
            net_income = data.get("net_income", 0)
            if revenue > 0:
                ratios["net_margin"] = (net_income / revenue) * 100

            # 资产收益率
            total_assets = data.get("total_assets", 0)
            if total_assets > 0:
                ratios["roa"] = (net_income / total_assets) * 100

            # 净资产收益率
            equity = data.get("equity", 0)
            if equity > 0:
                ratios["roe"] = (net_income / equity) * 100

        except Exception as e:
            logger.error(f"计算盈利能力比率失败: {str(e)}")

        return ratios

    def _calculate_leverage_ratios(self, data: dict) -> dict[str, float]:
        """计算杠杆比率"""
        ratios = {}

        try:
            # 资产负债率
            total_assets = data.get("total_assets", 0)
            total_debt = data.get("total_debt", 0)
            if total_assets > 0:
                ratios["debt_to_assets"] = (total_debt / total_assets) * 100

            # 权益乘数
            equity = data.get("equity", 0)
            if equity > 0:
                ratios["equity_multiplier"] = total_assets / equity

            # 利息保障倍数 = 营业利润 / 利息费用
            operating_profit = data.get("operating_profit", 0)
            interest_expense = data.get("interest_expense", 0)
            if interest_expense > 0:
                ratios["interest_coverage"] = operating_profit / interest_expense

        except Exception as e:
            logger.error(f"计算杠杆比率失败: {str(e)}")

        return ratios

    def _calculate_growth_rates(self, data: dict) -> dict[str, float]:
        """计算增长率"""
        rates = {}

        try:
            current_revenue = data.get("current_revenue", 0) or data.get("revenue", 0)
            previous_revenue = data.get("previous_revenue", 0)
            if previous_revenue > 0:
                rates["revenue_growth"] = ((current_revenue - previous_revenue) / previous_revenue) * 100

            current_net_income = data.get("current_net_income", 0) or data.get("net_income", 0)
            previous_net_income = data.get("previous_net_income", 0)
            if previous_net_income > 0:
                rates["net_income_growth"] = ((current_net_income - previous_net_income) / previous_net_income) * 100

            total_assets_current = data.get("total_assets", 0)
            previous_assets = data.get("previous_total_assets", 0)
            if previous_assets > 0:
                rates["asset_growth"] = ((total_assets_current - previous_assets) / previous_assets) * 100

            period_return = data.get("period_return", 0)
            if period_return != 0:
                rates["price_return"] = period_return

        except Exception as e:
            logger.error(f"计算增长率失败: {str(e)}")

        return rates

    def _calculate_dcf(self, data: dict) -> dict[str, float]:
        """简化DCF估值模型（全公司口径：总FCF → 总内在价值）"""
        dcf = {}
        try:
            fcf = data.get("operating_cashflow", 0) or data.get("net_income", 0) * 0.8
            growth_rate = data.get("period_return", 5) / 100.0
            if fcf > 0:
                projected_fcf = fcf * (1 + growth_rate) ** 5
                terminal_value = projected_fcf * 15
                dcf["estimated_intrinsic_value"] = terminal_value / (1.1 ** 5)
                # 用总市值/总内在价值，而非每股价格（DCF 是全公司口径）
                market_cap = data.get("market_cap", 0)
                if market_cap > 0:
                    dcf["price_to_intrinsic"] = market_cap / dcf["estimated_intrinsic_value"]
        except Exception as e:
            logger.error(f"DCF估值计算失败: {str(e)}")
        return dcf

    def _calculate_valuation_ratios(self, data: dict) -> dict[str, float]:
        """计算估值比率"""
        ratios = {}
        try:
            if data.get("pe_ratio", 0) > 0:
                ratios["pe_ratio"] = data["pe_ratio"]
            if data.get("pb_ratio", 0) > 0:
                ratios["pb_ratio"] = data["pb_ratio"]
            if data.get("market_cap", 0) > 0 and data.get("net_income", 0) > 0:
                ratios["market_cap_to_net_income"] = data["market_cap"] / data["net_income"]
            if data.get("market_cap", 0) > 0 and data.get("revenue", 0) > 0:
                ratios["ps_ratio"] = data["market_cap"] / data["revenue"]
        except Exception as e:
            logger.error(f"估值比率计算失败: {str(e)}")
        return ratios

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
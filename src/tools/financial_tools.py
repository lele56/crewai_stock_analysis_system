# src/tools/financial_tools.py
"""金融数据工具包 - 包含财务计算等工具"""

from datetime import datetime
import json
import logging
import re

from src.tools.reporting_tools import BaseTool

logger = logging.getLogger(__name__)


class FinancialCalculatorTool(BaseTool):
    """金融计算器工具 — 优先从 API 直接获取财务数据，兜底用正则从文本提取"""

    name: str = "Financial Calculator Tool"
    description: str = (
        "计算财务指标和比率。传 ticker 可直接从 API 获取真实财务数据（推荐），"
        "传 financial_data 则从文本中提取。参数: ticker(股票代码), financial_data(可选文本), calculation_type"
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

            # 兜底：从文本中提取
            if not data and financial_data and financial_data.strip():
                data = self._parse_financial_data(financial_data)

            if not data:
                logger.warning("财务数据为空，无法计算")
                return "财务数据为空，请先通过 AkShare Data Tool 获取股票数据"

            logger.info(f"开始计算财务指标，类型: {calculation_type}, 数据键: {list(data.keys())[:10]}")

            results = {}

            ct = calculation_type.lower()
            if ct in ("liquidity", "all"):
                results["liquidity_ratios"] = self._calculate_liquidity_ratios(data)

            if ct in ("profitability", "all"):
                results["profitability_ratios"] = self._calculate_profitability_ratios(data)

            if ct in ("leverage", "all"):
                results["leverage_ratios"] = self._calculate_leverage_ratios(data)

            if ct in ("growth", "all"):
                results["growth_rates"] = self._calculate_growth_rates(data)

            if ct in ("dcf", "dcf_valuation", "dcf valuation calculation", "all"):
                results["dcf_valuation"] = self._calculate_dcf(data)

            if ct in ("valuation", "valuation_analysis", "all"):
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
    def _fetch_financial_from_api(ticker: str) -> dict:
        """获取财务数据：优先缓存，缓存未命中则直接调 API"""
        from src.tools.akshare_data_parser import load_financial_from_cache

        data = load_financial_from_cache(ticker)
        if data:
            return data

        try:
            from src.tools.akshare_data_parser import get_financial_statements, _safe_float

            result: dict[str, float] = {}
            for stype, sections in [("利润表", ["financials"]), ("资产负债表", ["balance_sheet"]), ("现金流量表", ["cashflow"])]:
                df = get_financial_statements(ticker, stype)
                if not df.empty:
                    record = df.iloc[0].to_dict()
                    for k, v in record.items():
                        val = _safe_float(v)
                        if val is not None:
                            result[k] = val

            _key_map = {
                # 利润表
                "TOTAL_OPERATE_INCOME": "revenue", "OPERATE_INCOME": "revenue",
                "NETPROFIT": "net_income", "PARENT_NETPROFIT": "net_income",
                "OPERATE_PROFIT": "operating_profit",
                "OPERATE_COST": "operating_cost",
                "SALE_EXPENSE": "sale_expense",
                "MANAGE_EXPENSE": "manage_expense",
                "FINANCE_EXPENSE": "finance_expense",
                "RESEARCH_EXPENSE": "research_expense",
                "INTEREST_EXPENSE": "interest_expense",
                "INCOME_TAX": "income_tax",
                "TOTAL_OPERATE_COST": "total_operating_cost",
                # 资产负债表
                "ASSET_BALANCE": "total_assets",
                "EQUITY_BALANCE": "equity",
                "CURRENT_ASSET_BALANCE": "current_assets",
                "CURRENT_LIAB_BALANCE": "current_liabilities",
                "INVENTORY": "inventory",
                "MONETARYFUNDS": "cash",
                "LIAB_BALANCE": "total_debt",
                "ACCOUNTS_RECE": "accounts_receivable",
                "ACCOUNTS_PAYABLE": "accounts_payable",
                "FIXED_ASSET": "fixed_assets",
                "BORROW_FUND": "borrow_fund",
                "SHORT_LOAN": "short_loan",
                # 现金流量表
                "NETCASH_OPERATE": "operating_cashflow",
                "NETCASH_INVEST": "investing_cashflow",
                "NETCASH_FINANCE": "financing_cashflow",
                "TOTAL_OPERATE_INFLOW": "total_operating_inflow",
                "TOTAL_OPERATE_OUTFLOW": "total_operating_outflow",
                # 每股指标
                "EPSJB": "eps",
                "BPS": "bps",
            }
            for cn, en in _key_map.items():
                if cn in result:
                    result[en] = result[cn]

            if result:
                logger.info("直接从 API 获取财务数据成功")
                return result
        except Exception as e:
            logger.warning("直接调 API 获取财务数据失败: %s", str(e)[:80])

        return {}

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

        ebit = _extract_number(r"营业利润\**[：:]\s*([\d,]+\.?\d*)")
        if ebit > 0:
            result["ebit"] = ebit
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

        period_return = _extract_number(r"期间涨幅\**[：:]\s*([\d.-]+)%")
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

            # 利息保障倍数
            ebit = data.get("ebit", 0)
            interest_expense = data.get("interest_expense", 0)
            if interest_expense > 0:
                ratios["interest_coverage"] = ebit / interest_expense

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

            current_assets = data.get("current_assets", 0)
            previous_assets = data.get("previous_assets", 0)
            if previous_assets > 0:
                rates["asset_growth"] = ((current_assets - previous_assets) / previous_assets) * 100

            period_return = data.get("period_return", 0)
            if period_return != 0:
                rates["price_return"] = period_return

        except Exception as e:
            logger.error(f"计算增长率失败: {str(e)}")

        return rates

    def _calculate_dcf(self, data: dict) -> dict[str, float]:
        """简化DCF估值模型"""
        dcf = {}
        try:
            fcf = data.get("operating_cashflow", 0) or data.get("net_income", 0) * 0.8
            growth_rate = data.get("period_return", 5) / 100.0
            if fcf > 0:
                projected_fcf = fcf * (1 + growth_rate) ** 5
                terminal_value = projected_fcf * 15
                dcf["estimated_intrinsic_value"] = terminal_value / (1.1 ** 5)
                if data.get("current_price", 0) > 0:
                    dcf["price_to_intrinsic"] = data["current_price"] / dcf["estimated_intrinsic_value"]
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
        lines = []
        for category, ratios in results.items():
            if not ratios:
                continue
            cat_name = category.replace("_", " ").title()
            items = []
            for ratio_name, value in ratios.items():
                name = self._translate_ratio_name(ratio_name)
                if "growth" in ratio_name or "margin" in ratio_name or ratio_name in ("roa", "roe"):
                    items.append(f"{name}: {value:.2f}%")
                else:
                    items.append(f"{name}: {value:.2f}")
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
        }
        return translations.get(ratio_name, ratio_name)

    def _generate_analysis_suggestions(self, results: dict) -> str:
        """生成分析建议"""
        suggestions = "## 分析建议\n\n"

        # 流动性分析
        liquidity = results.get("liquidity_ratios", {})
        current_ratio = liquidity.get("current_ratio", 0)
        if current_ratio < 1:
            suggestions += "- **流动性风险**: 流动比率低于1，可能存在短期偿债压力\n"
        elif current_ratio > 2:
            suggestions += "- **资金利用**: 流动比率较高，可考虑提高资金使用效率\n"

        # 盈利能力分析
        profitability = results.get("profitability_ratios", {})
        net_margin = profitability.get("net_margin", 0)
        if net_margin < 5:
            suggestions += "- **盈利能力**: 净利率较低，需要提高盈利能力\n"
        elif net_margin > 20:
            suggestions += "- **盈利能力**: 净利率表现优秀，具有较强的竞争优势\n"

        # 杠杆分析
        leverage = results.get("leverage_ratios", {})
        debt_to_assets = leverage.get("debt_to_assets", 0)
        if debt_to_assets > 70:
            suggestions += "- **财务风险**: 资产负债率较高，财务风险需要关注\n"
        elif debt_to_assets < 30:
            suggestions += "- **财务保守**: 资产负债率较低，可考虑适度增加财务杠杆\n"

        # 增长分析
        growth = results.get("growth_rates", {})
        revenue_growth = growth.get("revenue_growth", 0)
        if revenue_growth > 20:
            suggestions += "- **增长强劲**: 营收增长率较高，业务发展良好\n"
        elif revenue_growth < 0:
            suggestions += "- **增长停滞**: 营收出现负增长，需要关注业务发展\n"

        return suggestions


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
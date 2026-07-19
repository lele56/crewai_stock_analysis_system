# src/tools/financial_calculations.py
"""财务计算引擎 — 比率计算、增长率、DCF估值、文本解析"""

from datetime import datetime
import logging
import re

logger = logging.getLogger(__name__)


def parse_report_text(text: str) -> dict:
    """从股票数据报告文本中提取结构化财务数据"""
    result = {}

    def _extract_number(pattern: str, source: str = text) -> float:
        m = re.search(pattern, source)
        if m:
            num_str = m.group(1).replace(",", "").replace("，", "").replace("元", "").strip()
            try:
                return float(num_str)
            except ValueError:
                logger.debug(f"数值提取失败: pattern={pattern[:30]}, text_snippet={num_str[:20]}")
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


def calculate_liquidity_ratios(data: dict) -> dict[str, float]:
    """计算流动性比率（流动比率、速动比率、现金比率）"""
    ratios = {}
    try:
        current_assets = data.get("current_assets", 0)
        current_liabilities = data.get("current_liabilities", 0)
        if current_liabilities > 0:
            ratios["current_ratio"] = current_assets / current_liabilities

        inventory = data.get("inventory", 0)
        quick_assets = current_assets - inventory
        if current_liabilities > 0:
            ratios["quick_ratio"] = quick_assets / current_liabilities

        cash = data.get("cash", 0)
        if current_liabilities > 0:
            ratios["cash_ratio"] = cash / current_liabilities
    except Exception as e:
        logger.error(f"计算流动性比率失败: {str(e)}")
    return ratios


def calculate_profitability_ratios(data: dict) -> dict[str, float]:
    """计算盈利能力比率（毛利率、净利率、ROA、ROE）"""
    ratios = {}
    try:
        revenue = data.get("revenue", 0)
        gross_profit = data.get("gross_profit", 0)
        if revenue > 0:
            ratios["gross_margin"] = (gross_profit / revenue) * 100

        net_income = data.get("net_income", 0)
        if revenue > 0:
            ratios["net_margin"] = (net_income / revenue) * 100

        total_assets = data.get("total_assets", 0)
        if total_assets > 0:
            ratios["roa"] = (net_income / total_assets) * 100

        equity = data.get("equity", 0)
        if equity > 0:
            ratios["roe"] = (net_income / equity) * 100
    except Exception as e:
        logger.error(f"计算盈利能力比率失败: {str(e)}")
    return ratios


def calculate_leverage_ratios(data: dict) -> dict[str, float]:
    """计算杠杆比率（资产负债率、权益乘数、利息保障倍数）"""
    ratios = {}
    try:
        total_assets = data.get("total_assets", 0)
        total_debt = data.get("total_debt", 0)
        if total_assets > 0:
            ratios["debt_to_assets"] = (total_debt / total_assets) * 100

        equity = data.get("equity", 0)
        if equity > 0:
            ratios["equity_multiplier"] = total_assets / equity

        operating_profit = data.get("operating_profit", 0)
        interest_expense = data.get("interest_expense", 0)
        if interest_expense > 0:
            ratios["interest_coverage"] = operating_profit / interest_expense
    except Exception as e:
        logger.error(f"计算杠杆比率失败: {str(e)}")
    return ratios


def calculate_growth_rates(data: dict) -> dict[str, float]:
    """计算增长率（营收、净利润、资产、价格）"""
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


def calculate_dcf(data: dict) -> dict[str, float]:
    """简化DCF估值模型（全公司口径：总FCF → 总内在价值）"""
    dcf = {}
    try:
        fcf = data.get("operating_cashflow", 0) or data.get("net_income", 0) * 0.8
        growth_rate = data.get("period_return", 5) / 100.0
        if fcf > 0:
            projected_fcf = fcf * (1 + growth_rate) ** 5
            terminal_value = projected_fcf * 15
            dcf["estimated_intrinsic_value"] = terminal_value / (1.1 ** 5)
            market_cap = data.get("market_cap", 0)
            if market_cap > 0:
                dcf["price_to_intrinsic"] = market_cap / dcf["estimated_intrinsic_value"]
    except Exception as e:
        logger.error(f"DCF估值计算失败: {str(e)}")
    return dcf


def calculate_valuation_ratios(data: dict) -> dict[str, float]:
    """计算估值比率（PE、PB、PS、市值/净利润）"""
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


def find_yoy_previous(records: list[dict]) -> dict | None:
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
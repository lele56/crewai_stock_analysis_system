# tests/test_data_types.py
"""测试工具对各种数据类型的响应 - 不依赖 LLM，直接调用"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger("test")


def test_market_data_types():
    """测试 market_data_tool 所有已知/未知数据类型"""
    from src.tools.market_data_tool import MarketDataTool
    md = MarketDataTool()

    all_types = [
        # 已知类型
        "market_overview", "market_data", "market_summary", "stock_market_data",
        "sector_performance", "market_sentiment",
        # LLM 生成过的类型
        "China_A_share_market_data", "stock_daily_history", "index_daily_history",
        "fund_flow_and_sentiment", "index_constituents",
        "income_statement_balance_sheet_cashflow", "competitor_financial_performance",
        "valutation_and_context", "financial_data", "industry_analysis",
        "stock_analysis", "company_analysis", "price_data", "market_research",
        "sector_analysis", "market_mood", "sentiment_analysis",
        # 故意错误的
        "unknown_weird_type", "DCF Valuation Calculation", "",
    ]

    passed = 0
    failed = 0
    for dtype in all_types:
        result = md._run("测试", dtype)
        if "失败" in result:
            print(f"  ❌ {dtype}: {result[:80]}")
            failed += 1
        else:
            print(f"  ✅ {dtype}: {result[:60]}...")
            passed += 1

    print(f"\n  market_data_tool: {passed} 通过, {failed} 失败\n")
    assert failed == 0, f"market_data_tool 有 {failed} 个类型失败"


def test_financial_calculation_types():
    """测试 financial_calculator_tool 所有计算类型"""
    from src.tools.financial_tools import FinancialCalculatorTool
    fc = FinancialCalculatorTool()

    test_data = '{"current_assets": 1e6, "current_liabilities": 5e5, "inventory": 2e5, "cash": 3e5, "revenue": 2e6, "gross_profit": 8e5, "net_income": 4e5, "total_assets": 3e6, "equity": 1.5e6, "total_debt": 1e6}'

    calc_types = [
        "liquidity", "profitability", "leverage", "growth", "all",
        "DCF Valuation Calculation", "dcf", "dcf_valuation",
        "valuation", "valuation_analysis",
        "unknown_calc", "",
    ]

    passed = 0
    failed = 0
    for ct in calc_types:
        result = fc._run(test_data, ct)
        if "失败" in result:
            print(f"  ❌ {ct}: {result[:80]}")
            failed += 1
        else:
            has_data = "无可用数据" not in result
            print(f"  {'✅' if has_data else '⚠️ '} {ct}: {result[:80]}...")
            passed += 1

    print(f"\n  financial_calculator_tool: {passed} 通过, {failed} 失败\n")
    assert failed == 0, f"financial_calculator_tool 有 {failed} 个类型失败"


def test_financial_regex_from_report():
    """测试从真实报告文本中提取财务数据"""
    from src.tools.akshare_tools import AkShareTool
    from src.tools.financial_tools import FinancialCalculatorTool

    print("=" * 60)
    print("测试: 从 AkShare 报告提取财务数据")
    print("=" * 60)

    ak = AkShareTool()
    fc = FinancialCalculatorTool()

    print("\n>>> 获取真实数据...")
    raw = ak._run("sh600519", "1y")
    print(f"  报告长度: {len(raw)} 字符")

    # 检查报告中有哪些字段
    import re
    fields = ["最新营收", "最新净利润", "流动资产", "流动负债", "资产总计",
              "负债合计", "存货", "货币资金", "股东权益", "营业利润",
              "经营活动现金流量净额", "市值", "当前价格", "市盈率", "市净率"]
    print("\n>>> 报告中字段存在情况:")
    for f in fields:
        found = re.search(rf"{f}\**\s*[：:]", raw)
        print(f"  {'✅' if found else '❌'} {f}")

    print("\n>>> 财务计算器解析结果:")
    result = fc._run(raw, "all")
    # 提取关键指标
    for key in ["revenue", "net_income", "current_assets", "total_assets", "equity"]:
        m = re.search(rf"从报告中提取财务数据.*?{key}=([\d.]+)", result)
        if m:
            val = float(m.group(1))
            print(f"  {'✅' if val > 0 else '❌'} {key}: {val:,.0f}")
        else:
            print(f"  ❌ {key}: 未找到")

    print()


def test_reporting_tool_types():
    """测试 reporting_tool 各种报告类型"""
    from src.tools.reporting_tools import ReportWritingTool
    rw = ReportWritingTool()

    report_types = [
        "Financial Data Report", "Market Research Report", "Technical Analysis Report",
        "Executive Summary", "Investment Analysis", "Risk Assessment",
        "Comprehensive Analysis", "Final Report", "MarketResearch",
        "", "unknown_type",
    ]

    passed = 0
    failed = 0
    for rt in report_types:
        result = rw._run('{"test": "data"}', rt)
        if "失败" in result or "error" in result.lower():
            print(f"  ❌ {rt}: {result[:80]}")
            failed += 1
        else:
            print(f"  ✅ {rt}: {result[:60]}...")
            passed += 1

    print(f"\n  reporting_tool: {passed} 通过, {failed} 失败\n")
    assert failed == 0, f"reporting_tool 有 {failed} 个类型失败"


if __name__ == "__main__":
    print("=" * 60)
    print("数据类型兼容性测试")
    print("=" * 60)

    all_ok = True
    all_ok &= test_market_data_types()
    all_ok &= test_financial_calculation_types()
    test_financial_regex_from_report()
    all_ok &= test_reporting_tool_types()

    print("=" * 60)
    print(f"结果: {'全部通过 ✅' if all_ok else '存在问题 ❌'}")
    print("=" * 60)
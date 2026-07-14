# scripts/validate_data_sources.py
"""数据源验证脚本 - 测试腾讯/新浪/TickFlow/akshare/tushare数据获取"""
import sys
import os
import time
import logging

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.config import Config

_log_level = getattr(logging, Config.LOG_LEVEL, logging.INFO)
logging.basicConfig(level=_log_level, format=Config.LOG_FORMAT)
logger = logging.getLogger(__name__)


def test_stock_basic_info():
    print("\n" + "=" * 60)
    print("  1. 测试股票基本信息获取")
    print("=" * 60)
    from src.tools.akshare_data_parser import get_stock_basic_info

    test_stocks = [
        ("sh600000", "浦发银行"),
        ("sz000001", "平安银行"),
        ("sh600519", "贵州茅台"),
        ("sz000858", "五粮液"),
    ]

    for ticker, name in test_stocks:
        print(f"\n  [{ticker}] {name}:")
        try:
            info = get_stock_basic_info(ticker)
            print(f"    公司名称: {info.get('longName', 'N/A')}")
            print(f"    行业: {info.get('industry', 'N/A')}")
            mcap = info.get('marketCap', 0)
            print(f"    市值: {'¥' + f'{mcap:,.0f}' if mcap else 'N/A'}")
            price = info.get('currentPrice', 0)
            print(f"    当前价格: {'¥' + f'{price:.2f}' if price else 'N/A'}")
            print(f"    市盈率: {info.get('trailingPE', 'N/A')}")
            print(f"    市净率: {info.get('priceToBook', 'N/A')}")
            print(f"    股息率: {info.get('dividendYield', 0)}")
            print(f"    Beta: {info.get('beta', 'N/A')}")
            print(f"    52周最高: ¥{info.get('fiftyTwoWeekHigh', 0):.2f}")
            print(f"    52周最低: ¥{info.get('fiftyTwoWeekLow', 0):.2f}")
        except Exception as e:
            print(f"    错误: {str(e)[:100]}")
        time.sleep(0.5)


def test_history_data():
    print("\n" + "=" * 60)
    print("  2. 测试历史K线数据获取")
    print("=" * 60)
    from src.tools.akshare_data_parser import get_stock_history_data

    test_cases = [
        ("sh600000", "1mo"),
        ("sz000001", "3mo"),
        ("sh600519", "6mo"),
    ]

    for ticker, period in test_cases:
        print(f"\n  [{ticker}] 周期={period}:")
        try:
            df = get_stock_history_data(ticker, period)
            if df.empty:
                print("    结果: 空数据")
            else:
                print(f"    数据条数: {len(df)}")
                print(f"    日期范围: {df.index[0]} ~ {df.index[-1]}")
                print(f"    最新收盘价: ¥{df['Close'].iloc[-1]:.2f}")
                print(f"    最高价: ¥{df['High'].max():.2f}")
                print(f"    最低价: ¥{df['Low'].min():.2f}")
                print(f"    平均成交量: {df['Volume'].mean():,.0f}")
        except Exception as e:
            print(f"    错误: {str(e)[:100]}")
        time.sleep(0.5)


def test_financial_statements():
    print("\n" + "=" * 60)
    print("  3. 测试财务报表获取")
    print("=" * 60)
    from src.tools.akshare_data_parser import get_financial_statements

    for statement_type in ["利润表", "资产负债表", "现金流量表"]:
        print(f"\n  [{statement_type}] sh600000:")
        try:
            df = get_financial_statements("sh600000", statement_type)
            if df.empty:
                print("    结果: 空数据")
            else:
                print(f"    数据条数: {len(df)}")
                print(f"    列数: {len(df.columns)}")
                print(f"    列名: {', '.join(df.columns[:5])}...")
        except Exception as e:
            print(f"    错误: {str(e)[:100]}")
        time.sleep(0.5)


def test_data_source_availability():
    print("\n" + "=" * 60)
    print("  4. 数据源可用性检查")
    print("=" * 60)
    from src.tools.akshare_data_sources import TICKFLOW_AVAILABLE, TUSHARE_AVAILABLE
    print(f"\n  TickFlow: {'✓ 可用' if TICKFLOW_AVAILABLE else '✗ 未安装'}")
    print(f"  Tushare:  {'✓ 可用' if TUSHARE_AVAILABLE else '✗ 未安装'}")
    try:
        import akshare
        print(f"  akshare:  ✓ 可用 (版本: {akshare.__version__})")
    except ImportError:
        print("  akshare:  ✗ 未安装")


def test_report_generation():
    print("\n" + "=" * 60)
    print("  5. 测试报告生成")
    print("=" * 60)
    from src.tools.akshare_data_parser import (
        get_stock_basic_info, get_stock_history_data, get_financial_statements,
        generate_stock_report,
    )
    ticker = "sh600000"
    print(f"\n  生成 {ticker} 完整报告:")
    try:
        info = get_stock_basic_info(ticker)
        time.sleep(0.3)
        hist = get_stock_history_data(ticker, "1mo")
        time.sleep(0.3)
        financials = get_financial_statements(ticker, "利润表")
        time.sleep(0.3)
        balance = get_financial_statements(ticker, "资产负债表")
        time.sleep(0.3)
        cashflow = get_financial_statements(ticker, "现金流量表")
        report = generate_stock_report(ticker, info, hist, financials, balance, cashflow)
        print(f"  报告长度: {len(report)} 字符")
        print(f"  报告预览:\n{report[:500]}...")
    except Exception as e:
        print(f"  错误: {str(e)[:100]}")


def test_export_formats():
    print("\n" + "=" * 60)
    print("  6. 测试多格式导出")
    print("=" * 60)
    from src.tools.reporting_tools import DataExportTool
    import json

    test_data = json.dumps({
        "company": "浦发银行", "ticker": "sh600000",
        "industry": "银行", "currentPrice": 10.50,
        "marketCap": 300000000000, "trailingPE": 5.2,
        "recommendation": "持有", "overall_score": 72.5,
        "risk_factors": ["利率风险", "信用风险", "监管风险"],
        "financial_metrics": {"ROE": "12.5%", "ROA": "0.8%", "NIM": "2.1%"},
    }, ensure_ascii=False)

    tool = DataExportTool()
    for fmt in ["json", "csv", "markdown", "html", "txt", "word"]:
        try:
            path = tool._run(test_data, export_format=fmt, filename=f"test_validate_{fmt}")
            print(f"  {fmt:10s}: ✓ {path}")
        except Exception as e:
            print(f"  {fmt:10s}: ✗ {str(e)[:80]}")


if __name__ == "__main__":
    print("=" * 60)
    print("  股票数据源验证脚本")
    print("=" * 60)

    test_data_source_availability()
    test_stock_basic_info()
    test_history_data()
    test_financial_statements()
    test_report_generation()
    test_export_formats()

    print("\n" + "=" * 60)
    print("  验证完成！")
    print("=" * 60)
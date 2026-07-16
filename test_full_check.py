"""全链路测试 - 验证所有数据源和工具"""
import sys, json, os
sys.path.insert(0, ".")

passed = 0
failed = 0

def check(desc, ok):
    global passed, failed
    if ok:
        passed += 1
        print(f"  [PASS] {desc}")
    else:
        failed += 1
        print(f"  [FAIL] {desc}")
    return ok

# ═══════════════════════════════════════════════════════════════
print("=" * 60)
print("1. 模块导入")
print("=" * 60)

try:
    import akshare as ak
    check(f"akshare 导入 (版本: {ak.__version__})", True)
except Exception as e:
    check(f"akshare 导入: {e}", False)

try:
    from src.tools.akshare_data_sources import (
        get_tencent_kline, get_tickflow_kline, get_akshare_kline,
        get_financial_data_em, get_index_daily_tx,
        TICKFLOW_AVAILABLE
    )
    check("akshare_data_sources 导入", True)
except Exception as e:
    check(f"akshare_data_sources 导入: {e}", False)

try:
    from src.tools.akshare_data_parser import (
        generate_stock_report, get_stock_basic_info, get_stock_history_data,
        get_financial_statements, load_stock_cache, _save_stock_cache,
        _safe_float, _extract_financial_metrics, _extract_balance_sheet_metrics,
        _extract_cashflow_metrics, _validate_stock_data
    )
    check("akshare_data_parser 导入", True)
except Exception as e:
    check(f"akshare_data_parser 导入: {e}", False)

try:
    from src.tools.market_data_tool import MarketDataTool, _fetch_index_data, _fetch_sector_data
    check("market_data_tool 导入", True)
except Exception as e:
    check(f"market_data_tool 导入: {e}", False)

try:
    from src.tools.akshare_tools import AkShareTool
    check("akshare_tools 导入", True)
except Exception as e:
    check(f"akshare_tools 导入: {e}", False)

try:
    from src.tools.financial_tools import FinancialCalculatorTool
    check("financial_tools 导入", True)
except Exception as e:
    check(f"financial_tools 导入: {e}", False)

try:
    from src.tools.technical_tools import TechnicalAnalysisTool
    check("technical_tools 导入", True)
except Exception as e:
    check(f"technical_tools 导入: {e}", False)

# ═══════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("2. _safe_float 数值转换")
print("=" * 60)

tests = [
    ("1.5亿", 1.5e8), ("3000万", 3e7), ("3,000", 3000),
    ("N/A", None), (None, None), ("0", 0.0), ("1.5e10", 1.5e10),
    ("-500万", -5e6),
]
for val, exp in tests:
    r = _safe_float(val)
    ok = (r == exp) or (r is None and exp is None)
    check(f"_safe_float({val!r}) = {r}", ok)

# ═══════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("3. 个股K线数据 (多数据源)")
print("=" * 60)

ticker = "600519"

# 腾讯K线
try:
    df = get_tencent_kline(ticker, "1mo")
    check(f"腾讯K线: {len(df)} 行, 列: {list(df.columns)}", not df.empty and len(df) > 0)
except Exception as e:
    check(f"腾讯K线: {e}", False)

# TickFlow K线
try:
    df = get_tickflow_kline(ticker, "1mo")
    check(f"TickFlow K线: {len(df)} 行", not df.empty and len(df) > 0)
except Exception as e:
    check(f"TickFlow K线: {e}", False)

# akshare K线
try:
    df = get_akshare_kline(ticker, "1mo")
    check(f"akshare K线: {len(df)} 行", not df.empty and len(df) > 0)
except Exception as e:
    check(f"akshare K线: {e}", False)

# ═══════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("4. 个股基本信息")
print("=" * 60)

try:
    info = get_stock_basic_info(ticker)
    check(f"基本信息: {info.get('名称', 'N/A')}, 行业: {info.get('行业', 'N/A')}", len(info) > 2)
except Exception as e:
    check(f"基本信息: {e}", False)

# ═══════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("5. 财务数据")
print("=" * 60)

for stype in ["利润表", "资产负债表", "现金流量表"]:
    try:
        df = get_financial_statements(ticker, stype)
        check(f"{stype}: {len(df)} 行 × {len(df.columns)} 列", not df.empty)
    except Exception as e:
        check(f"{stype}: {e}", False)

# ═══════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("6. 整合数据报告 (generate_stock_report)")
print("=" * 60)

try:
    info = get_stock_basic_info(ticker)
    import pandas as pd
    import time
    time.sleep(0.5)
    hist = get_stock_history_data(ticker, "1mo")
    time.sleep(0.5)
    financials = get_financial_statements(ticker, "利润表")
    time.sleep(0.3)
    balance_sheet = get_financial_statements(ticker, "资产负债表")
    time.sleep(0.3)
    cashflow = get_financial_statements(ticker, "现金流量表")

    report = generate_stock_report(ticker, info, hist, financials, balance_sheet, cashflow)
    check(f"报告生成: {len(report)} 字符", isinstance(report, str) and len(report) > 100)
except Exception as e:
    check(f"报告生成: {e}", False)

# ═══════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("7. 缓存读写 + JSON序列化")
print("=" * 60)

try:
    import pandas as pd
    info = get_stock_basic_info(ticker)
    hist = get_stock_history_data(ticker, "1mo")
    financials = get_financial_statements(ticker, "利润表")
    balance_sheet = get_financial_statements(ticker, "资产负债表")
    cashflow = get_financial_statements(ticker, "现金流量表")

    _save_stock_cache(ticker, hist, financials, balance_sheet, cashflow, info)
    cached = load_stock_cache(ticker)
    check(f"缓存写入/读取: K线={len(cached.get('kline',[]))}, validated={cached.get('validated')}",
          cached is not None and len(cached.get('kline', [])) > 0)
except Exception as e:
    check(f"缓存读写: {e}", False)

# ═══════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("8. 市场数据 (指数/板块)")
print("=" * 60)

try:
    result = _fetch_index_data()
    check(f"指数数据: {len(result)} 个", len(result) == 6)
    for name, data in result.items():
        print(f"     {name}: {data['price']:.2f} ({data['change_pct']:+.2f}%)")
except Exception as e:
    check(f"指数数据: {e}", False)

try:
    result = _fetch_sector_data()
    check(f"板块数据: {len(result)} 个", len(result) >= 0)
except Exception as e:
    check(f"板块数据: {e}", False)

# ═══════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("9. 工具类执行")
print("=" * 60)

# MarketDataTool
try:
    tool = MarketDataTool()
    result = tool._run("market_overview")
    check("MarketDataTool._run", len(result) > 50)
except Exception as e:
    check(f"MarketDataTool._run: {e}", False)

# AkShareTool
try:
    tool = AkShareTool()
    result = tool._run(ticker, "1mo")
    check("AkShareTool._run", len(result) > 200)
except Exception as e:
    check(f"AkShareTool._run: {e}", False)

# FinancialCalculatorTool
try:
    tool = FinancialCalculatorTool()
    result = tool._run(ticker=ticker)
    check("FinancialCalculatorTool._run", len(result) > 50)
except Exception as e:
    check(f"FinancialCalculatorTool._run: {e}", False)

# TechnicalAnalysisTool
try:
    tool = TechnicalAnalysisTool()
    result = tool._run(ticker, "1mo")
    check("TechnicalAnalysisTool._run", len(result) > 50)
except Exception as e:
    check(f"TechnicalAnalysisTool._run: {e}", False)

# ═══════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print(f"结果: {passed} PASS, {failed} FAIL")
print("=" * 60)

if failed > 0:
    sys.exit(1)
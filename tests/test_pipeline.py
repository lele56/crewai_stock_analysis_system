# tests/test_pipeline.py
"""端到端测试脚本 - 无需启动 Web 服务器"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("test_pipeline")


def test_tools():
    """测试各工具独立运行"""
    print("=" * 60)
    print("阶段 0: 工具独立测试")
    print("=" * 60)

    results = {}

    # 1. AkShare Tool
    print("\n>>> 1. AkShare Data Tool")
    from src.tools.akshare_tools import AkShareTool

    ak = AkShareTool()
    raw = ak._run("sh600519", "1y")
    print(f"  数据长度: {len(raw)} 字符")
    print(f"  前200字: {raw[:200]}")
    results["akshare"] = {"len": len(raw), "ok": "股票数据报告" in raw}

    # 2. Financial Calculator
    print("\n>>> 2. Financial Calculator Tool")
    from src.tools.financial_tools import FinancialCalculatorTool

    fc = FinancialCalculatorTool()
    fc_result = fc._run(raw, "all")
    print(f"  计算结果:\n{fc_result[:500]}")
    results["financial"] = {"ok": "财务指标分析报告" in fc_result}

    # 3. Market Data Tool
    print("\n>>> 3. Market Data Tool")
    from src.tools.market_data_tool import MarketDataTool

    md = MarketDataTool()
    for dtype in ["market_overview", "sector_performance", "market_sentiment", "stock_daily_history"]:
        r = md._run("test", dtype)
        print(f"  {dtype}: {r[:80]}...")
    results["market"] = {"ok": True}

    # 4. Technical Analysis Tool
    print("\n>>> 4. Technical Analysis Tool")
    from src.tools.technical_analysis_tool import TechnicalAnalysisTool

    ta = TechnicalAnalysisTool()
    ta_result = ta._run(raw, "all")
    print(f"  计算结果:\n{ta_result[:300]}")
    results["technical"] = {"ok": "技术分析" in ta_result}

    # 5. Reporting Tool
    print("\n>>> 5. Reporting Tool")
    from src.tools.reporting_tools import ReportWritingTool

    rw = ReportWritingTool()
    rw_result = rw._run(raw, "Financial Data Report")
    print(f"  报告长度: {len(rw_result)} 字符")
    results["reporting"] = {"ok": len(rw_result) > 100}

    return results


def test_data_collection_crew():
    """测试数据收集阶段"""
    print("\n" + "=" * 60)
    print("阶段 1: 数据收集 Crew")
    print("=" * 60)

    from src.crews.data_collection_crew import DataCollectionCrew

    crew = DataCollectionCrew()
    result = crew.execute_data_collection("贵州茅台", "sh600519")
    ok = result.get("status") == "success"
    print(f"  状态: {result.get('status')}")
    print(f"  耗时: {result.get('execution_time', 'N/A')} 秒")
    if ok:
        raw = result.get("result", "")
        if hasattr(raw, "raw"):
            raw = raw.raw
        print(f"  结果长度: {len(str(raw))} 字符")
    else:
        print(f"  错误: {result.get('error')}")
    return result


def test_analysis_crew(collection_result):
    """测试分析阶段"""
    print("\n" + "=" * 60)
    print("阶段 2: 分析 Crew")
    print("=" * 60)

    from src.crews.analysis_crew import AnalysisCrew

    crew = AnalysisCrew()
    result = crew.execute_collaborative_analysis(
        "贵州茅台", "sh600519", collection_result.get("result")
    )
    ok = result.get("success")
    print(f"  成功: {ok}")
    if ok:
        scores = result.get("collaboration_scores", {})
        print(f"  评分: {scores}")
        rec = result.get("final_recommendation", {})
        print(f"  建议: {rec.get('action', 'N/A')} (置信度: {rec.get('confidence', 'N/A')})")
    else:
        print(f"  错误: {result.get('error')}")
    return result


def test_decision_crew(analysis_result):
    """测试决策阶段"""
    print("\n" + "=" * 60)
    print("阶段 3: 决策 Crew")
    print("=" * 60)

    from src.crews.decision_crew import DecisionCrew

    crew = DecisionCrew()
    result = crew.execute_decision_process("贵州茅台", "sh600519", analysis_result)
    ok = result.get("success")
    print(f"  成功: {ok}")
    if ok:
        rec = result.get("final_recommendation", {})
        print(f"  决策: {rec.get('action', 'N/A')} (置信度: {rec.get('confidence', 'N/A')})")
        metrics = result.get("collective_decision_metrics", {})
        print(f"  投票数: {metrics.get('vote_count', 'N/A')}")
    else:
        print(f"  错误: {result.get('error')}")
    return result


def test_integration(collection_result, analysis_result, decision_result):
    """测试集成阶段"""
    print("\n" + "=" * 60)
    print("阶段 4: 集成 & 报告生成")
    print("=" * 60)

    from src.stock_analysis_system import StockAnalysisSystem

    system = StockAnalysisSystem()
    final = system._integrate_results(
        "贵州茅台", "sh600519",
        collection_result, analysis_result, decision_result,
    )
    print(f"  成功: {final.get('success')}")
    print(f"  投资评级: {final.get('investment_rating', {})}")
    print(f"  报告路径: {final.get('report_path', 'N/A')}")
    print(f"  数据路径: {final.get('data_path', 'N/A')}")
    return final


def test_full_pipeline(use_cache: bool = False):
    """完整流水线测试"""
    print("\n" + "=" * 60)
    print(f"完整流水线测试 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    from src.stock_analysis_system import StockAnalysisSystem

    system = StockAnalysisSystem()
    result = system.analyze_stock("贵州茅台", "sh600519", use_cache=use_cache)
    print(f"\n  最终结果: {'成功' if result.get('success') else '失败'}")
    if result.get("success"):
        print(f"  评分: {result.get('scores', {})}")
        print(f"  投资评级: {result.get('investment_rating', {})}")
        print(f"  报告路径: {result.get('report_path', 'N/A')}")
        print(f"  数据路径: {result.get('data_path', 'N/A')}")
    else:
        print(f"  错误: {result.get('error')}")
    return result


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="股票分析系统测试脚本")
    parser.add_argument("--tools", action="store_true", help="仅测试工具")
    parser.add_argument("--stages", action="store_true", help="分阶段测试")
    parser.add_argument("--full", action="store_true", help="完整流水线测试")
    parser.add_argument("--all", action="store_true", help="运行所有测试")
    args = parser.parse_args()

    if args.all or (not args.tools and not args.stages and not args.full):
        args.tools = args.stages = args.full = True

    tool_results = None
    collection_result = None
    analysis_result = None
    decision_result = None

    if args.tools:
        tool_results = test_tools()

    if args.stages:
        collection_result = test_data_collection_crew()
        if collection_result.get("status") == "success":
            analysis_result = test_analysis_crew(collection_result)
            if analysis_result.get("success"):
                decision_result = test_decision_crew(analysis_result)
                if decision_result.get("success"):
                    test_integration(collection_result, analysis_result, decision_result)

    if args.full:
        test_full_pipeline()

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)
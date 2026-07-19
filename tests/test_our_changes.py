# tests/test_our_changes.py
"""验证本次修改的数据模型和协作函数"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.crews.analysis_executor import (
    _extract_score_from_text,
    _has_prompt_keys,
    _score_to_rating,
    analyze_collaboration_quality,
    build_debate_prompt,
    build_iteration_prompt,
    calculate_collaboration_scores,
    generate_agent_abstract,
)
from src.crews.data_collection_executor import (
    _build_quality_check_input,
    _guess_position,
    _parse_quality_result,
    _safe_float,
    _safe_list,
)
from src.crews.data_parser import collection_data_to_prompt
from src.crews.data_schemas import (
    CollectionData,
    FinancialMetrics,
    IndustryData,
    MarketData,
    TechnicalData,
)


def test_data_schemas():
    print("\n=== 1. Data Schemas ===")
    md = MarketData()
    assert md.is_empty() is True
    md.price = 100.0
    assert md.is_empty() is False
    print("  MarketData.is_empty: OK")

    fm = FinancialMetrics()
    assert fm.is_empty() is True
    fm.revenue = [100.0]
    assert fm.is_empty() is False
    print("  FinancialMetrics.is_empty: OK")

    td = TechnicalData()
    assert td.is_empty() is True
    td.rsi_14 = 50.0
    assert td.is_empty() is False
    print("  TechnicalData.is_empty: OK")

    ind = IndustryData()
    assert ind.is_empty() is True
    ind.sector = "科技"
    assert ind.is_empty() is False
    print("  IndustryData.is_empty: OK")

    cd = CollectionData(company="test", ticker="000001")
    assert cd.is_effectively_empty is True
    cd.market = md
    assert cd.is_effectively_empty is False
    print("  CollectionData.is_effectively_empty: OK")

    p = cd.to_market_prompt()
    assert "100.0" in p
    print("  to_market_prompt: OK")

    p = cd.to_technical_prompt()
    assert "技术指标" in p or "技术" in p
    print("  to_technical_prompt: OK")


def test_executor_helpers():
    print("\n=== 2. Data Collection Executor ===")
    assert _safe_float("123.45") == 123.45
    assert _safe_float(None) == 0.0
    assert _safe_float("abc") == 0.0
    print("  _safe_float: OK")

    assert _safe_list([1, 2, 3]) == [1.0, 2.0, 3.0]
    assert _safe_list(None) == []
    print("  _safe_list: OK")

    assert _guess_position({"market_cap": 6000}) == "龙头"
    assert _guess_position({"market_cap": 500}) == "跟随"
    print("  _guess_position: OK")

    cd = CollectionData(company="test", ticker="000001")
    cd.market = MarketData(price=100.0)
    prompt = _build_quality_check_input("测试", "000001", cd)
    assert "测试" in prompt
    assert "000001" in prompt
    print("  _build_quality_check_input: OK")

    parsed = _parse_quality_result(
        '{"completeness": "high", "issues": [], "summary": "OK"}'
    )
    assert parsed["completeness"] == "high"
    print("  _parse_quality_result: OK")

    assert _has_prompt_keys({"financial_data": "x", "risk_data": "y", "industry_data": "z"}) is True
    assert _has_prompt_keys({"financial_data": "x"}) is False
    print("  _has_prompt_keys: OK")


def test_analysis_executor():
    print("\n=== 3. Analysis Executor ===")
    assert _extract_score_from_text("最终评分: 77") == 77.0
    assert _extract_score_from_text("综合评分: 85") == 85.0
    assert _extract_score_from_text("评分: 50") == 50.0
    print("  _extract_score_from_text: OK")

    assert _score_to_rating(85) == "优秀"
    assert _score_to_rating(70) == "良好"
    assert _score_to_rating(50) == "一般"
    assert _score_to_rating(35) == "较差"
    assert _score_to_rating(20) == "差"
    print("  _score_to_rating: OK")

    abstract = generate_agent_abstract("分析完成，评分: 77/100", "fundamental")
    assert abstract["score"] == 77.0
    assert abstract["rating"] == "良好"
    print("  generate_agent_abstract: OK")

    prompt = build_debate_prompt("fundamental", "营收增长20%", [
        {"agent_name": "risk", "score": 60, "rating": "一般", "key_points": "风险高"},
        {"agent_name": "industry", "score": 80, "rating": "优秀", "key_points": "行业好"},
    ])
    assert "fundamental" in prompt
    assert "风险高" in prompt
    print("  build_debate_prompt: OK")

    questions = build_iteration_prompt("", {"task_1": "分析1", "task_2": "分析2", "task_3": "分析3"})
    assert len(questions) == 3
    print("  build_iteration_prompt: OK")

    scores = calculate_collaboration_scores([
        "基本面评分: 80/100",
        "风险评分: 60/100",
        "行业评分: 70/100",
    ])
    assert len(scores) > 0
    print(f"  calculate_collaboration_scores: OK ({len(scores)} scores)")

    quality = analyze_collaboration_quality(scores)
    assert "consistency" in quality
    print(f"  analyze_collaboration_quality: OK (consistency={quality['consistency']})")


def test_data_parser():
    print("\n=== 4. Data Parser ===")
    cd = CollectionData(company="test", ticker="000001")
    cd.market = MarketData(price=100.0)
    prompt_data = collection_data_to_prompt(cd)
    assert "financial_data" in prompt_data
    assert "risk_data" in prompt_data
    assert "industry_data" in prompt_data
    print("  collection_data_to_prompt: OK")


def test_collection_data_to_prompt():
    print("\n=== 5. CollectionData.to_*_prompt ===")
    cd = CollectionData(
        company="茅台",
        ticker="600519",
        market=MarketData(price=1500.0, change_pct=0.05),
        financial=FinancialMetrics(roe=0.30, pe=25.0),
        technical=TechnicalData(rsi_14=55.0, ma_20=1480.0),
        industry=IndustryData(sector="白酒", industry="消费品"),
    )
    fp = cd.to_financial_prompt()
    assert "ROE" in fp
    print("  to_financial_prompt: OK")

    rp = cd.to_risk_prompt()
    assert "1500" in rp
    print("  to_risk_prompt: OK")

    ip = cd.to_industry_prompt()
    assert "白酒" in ip
    print("  to_industry_prompt: OK")

    mp = cd.to_market_prompt()
    assert "1500" in mp
    print("  to_market_prompt: OK")

    tp = cd.to_technical_prompt()
    assert "RSI" in tp
    print("  to_technical_prompt: OK")


if __name__ == "__main__":
    test_data_schemas()
    test_executor_helpers()
    test_analysis_executor()
    test_data_parser()
    test_collection_data_to_prompt()
    print("\n=== ALL TESTS PASSED ===")
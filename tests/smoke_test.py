#!/usr/bin/env python3
# tests/smoke_test.py
"""
快速验证脚本 - 测试完整分析流程，确认报告能正常生成
只会跑一只股票，验证全部三个阶段。
"""
import sys
import os
import time
import json
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from dotenv import load_dotenv
load_dotenv()

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'reports')
os.makedirs(OUTPUT_DIR, exist_ok=True)

def test_smoke():
    """快速冒烟测试 - 跑一只股票验证全流程"""
    print("=" * 60)
    print("  AI 股票分析系统 - 冒烟测试")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    from src.stock_analysis_system import StockAnalysisSystem

    system = StockAnalysisSystem()
    company = "贵州茅台"
    ticker = "sh600519"

    stage_start = time.time()
    progress_log = []

    def progress_callback(update):
        progress_log.append(update)
        bar = "█" * (update["progress"] // 5) + "░" * (20 - update["progress"] // 5)
        print(f"  [{bar}] {update['progress']:3d}% | {update['stage']}: {update['message']}")

    print(f"\n📊 测试目标: {company} ({ticker})\n")

    result = system.analyze_stock(
        company, ticker,
        use_cache=False,
        progress_callback=progress_callback
    )

    elapsed = time.time() - stage_start
    print(f"\n⏱️  总耗时: {elapsed:.1f} 秒 ({elapsed/60:.1f} 分钟)")

    # 验证结果
    checks = []

    # 1. 基本成功
    checks.append(("分析成功", result.get("success", False)))

    # 2. 有投资评级
    rating = result.get("investment_rating", {})
    checks.append(("投资评级", isinstance(rating, dict) and len(rating) > 0))

    # 3. 有评分
    score = result.get("overall_score", 0)
    checks.append(("综合评分", isinstance(score, (int, float)) and 0 < score <= 100))

    # 4. 报告文件存在
    report_path = result.get("report_path", "")
    checks.append(("报告路径", bool(report_path)))

    if report_path and os.path.exists(report_path):
        file_size = os.path.getsize(report_path)
        checks.append((f"报告大小 ({file_size} bytes)", file_size > 100))
    else:
        checks.append(("报告文件存在", False))

    reports_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'reports')
    if os.path.exists(reports_dir):
        md_files = [f for f in os.listdir(reports_dir) if f.endswith('.md')]
        checks.append((f"reports/目录下 {len(md_files)} 个MD文件", len(md_files) > 0))

    print("\n" + "=" * 60)
    print("  验证结果")
    print("=" * 60)

    all_pass = True
    for name, passed in checks:
        status = "✅" if passed else "❌"
        if not passed:
            all_pass = False
        print(f"  {status} {name}: {passed}")

    print(f"\n{'所有检查通过 ✅' if all_pass else '部分检查失败 ❌'}")

    json_path = os.path.join(OUTPUT_DIR, f"test_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump({
            "test_time": datetime.now().isoformat(),
            "company": company,
            "ticker": ticker,
            "elapsed_seconds": elapsed,
            "checks": {name: passed for name, passed in checks},
            "all_pass": all_pass,
            "progress_log": progress_log
        }, f, ensure_ascii=False, indent=2, default=str)
    print(f"\n📄 测试结果: {json_path}")

    return all_pass

if __name__ == "__main__":
    ok = test_smoke()
    sys.exit(0 if ok else 1)
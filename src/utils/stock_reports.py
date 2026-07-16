# src/utils/stock_reports.py
"""股票分析报告生成器"""

from datetime import datetime
import logging
from typing import Any

logger = logging.getLogger(__name__)


def generate_summary_report(results: list[dict[str, Any]]) -> str:
    """生成批量分析摘要报告"""
    logger.info("生成批量分析摘要报告")
    successful = [r for r in results if r["success"]]
    failed = [r for r in results if not r["success"]]

    report = f"""
# 批量股票分析报告

**分析时间**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**总股票数**: {len(results)}
**成功分析**: {len(successful)}
**失败分析**: {len(failed)}

## 分析摘要

### 成功分析股票
"""
    for result in successful:
        rating = result.get("investment_rating", {})
        rating_str = rating.get("rating", "未评级") if isinstance(rating, dict) else str(rating) if rating else "未评级"
        report += f"- **{result['company']} ({result['ticker']})**: {rating_str}\n"

    if failed:
        report += "\n### 失败分析股票\n"
        for result in failed:
            report += f"- **{result['company']} ({result['ticker']})**: {result.get('error', '未知错误')}\n"

    if successful:
        report += "\n## 统计分析\n"
        rating_stats = {}
        for result in successful:
            rating = result.get("investment_rating", {})
            rating_str = (
                rating.get("rating", "未评级") if isinstance(rating, dict) else str(rating) if rating else "未评级"
            )
            rating_stats[rating_str] = rating_stats.get(rating_str, 0) + 1
        report += "### 投资评级分布\n"
        for rating, count in rating_stats.items():
            report += f"- {rating}: {count} ({(count / len(successful)) * 100:.1f}%)\n"
        scores = [result.get("overall_score", 0) for result in successful]
        if scores:
            report += "\n### 综合评分统计\n"
            report += f"- 平均综合评分: {sum(scores) / len(scores):.1f}/100\n"
            report += f"- 最高评分: {max(scores):.1f}/100\n"
            report += f"- 最低评分: {min(scores):.1f}/100\n"

    report += "\n---\n*报告由股票分析系统自动生成*\n"
    return report

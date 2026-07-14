# src/utils/batch_report_generator.py
"""批量分析报告生成器"""
import json
import os
import logging
from datetime import datetime
from typing import Dict, Any

logger = logging.getLogger(__name__)


def generate_batch_summary(results: dict, errors: list, progress: dict) -> Dict[str, Any]:
    """生成批量分析摘要"""
    summary = {
        'analysis_time': datetime.now().isoformat(),
        'total_stocks': progress['total'],
        'successful_analyses': len(results),
        'failed_analyses': len(errors),
        'average_score': 0,
        'rating_distribution': {},
        'top_performers': [],
        'bottom_performers': []
    }
    scores = [result.get('overall_score', 0) for result in results.values()]
    if scores:
        summary['average_score'] = sum(scores) / len(scores)
    rating_counts = {}
    for result in results.values():
        rating = result.get('investment_rating', {}).get('rating', '未评级')
        rating_counts[rating] = rating_counts.get(rating, 0) + 1
    summary['rating_distribution'] = rating_counts
    sorted_results = sorted(results.items(), key=lambda x: x[1].get('overall_score', 0), reverse=True)
    summary['top_performers'] = [
        {'ticker': ticker, 'score': result.get('overall_score', 0)}
        for ticker, result in sorted_results[:5]
    ]
    summary['bottom_performers'] = [
        {'ticker': ticker, 'score': result.get('overall_score', 0)}
        for ticker, result in sorted_results[-5:]
    ]
    return summary


def export_batch_results(results: dict, errors: list, export_format: str = "json",
                        filepath: str = "") -> str:
    """导出批量分析结果"""
    if not filepath:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filepath = f"exports/batch_analysis_{timestamp}.{export_format}"
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    try:
        if export_format == "json":
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump({
                    'results': results, 'errors': errors,
                    'summary': generate_batch_summary(results, errors, {'total': len(results)})
                }, f, ensure_ascii=False, indent=2)
        elif export_format == "csv":
            import pandas as pd
            rows = [{
                'ticker': ticker, 'company': result.get('company', ''),
                'overall_score': result.get('overall_score', 0),
                'rating': result.get('investment_rating', {}).get('rating', ''),
                'success': result.get('success', False)
            } for ticker, result in results.items()]
            pd.DataFrame(rows).to_csv(filepath, index=False, encoding='utf-8')
        elif export_format == "excel":
            import pandas as pd
            rows = [{
                'ticker': ticker, 'company': result.get('company', ''),
                'overall_score': result.get('overall_score', 0),
                'rating': result.get('investment_rating', {}).get('rating', ''),
                'success': result.get('success', False),
                'analysis_time': result.get('timestamp', '')
            } for ticker, result in results.items()]
            pd.DataFrame(rows).to_excel(filepath, index=False)
        else:
            raise ValueError(f"不支持的导出格式: {export_format}")
        logger.info(f"结果已导出: {filepath}")
        return filepath
    except Exception as e:
        logger.error(f"导出结果失败: {str(e)}")
        raise
# src/stock_analysis_system.py
"""
股票分析系统主协调器
整合所有Crews和Flows，提供统一的分析接口
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import json
import concurrent.futures
import threading
import os

from src.crews.data_collection_crew import DataCollectionCrew
from src.crews.analysis_crew import AnalysisCrew
from src.crews.decision_crew import DecisionCrew
from src.utils.stock_cache_manager import StockCacheManager
from src.utils.stock_reports import generate_summary_report
from src.config import Config

log_dir = os.path.dirname(os.path.abspath(__file__)) + '/../'
log_file = os.path.join(log_dir, 'log.txt')
_log_level = getattr(logging, Config.LOG_LEVEL, logging.INFO)

logger = logging.getLogger()
logger.setLevel(_log_level)
for handler in logger.handlers[:]:
    logger.removeHandler(handler)

console_handler = logging.StreamHandler()
console_handler.setLevel(_log_level)
console_handler.setFormatter(logging.Formatter(Config.LOG_FORMAT))
logger.addHandler(console_handler)

file_handler = logging.FileHandler(log_file, encoding='utf-8', mode='a')
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(file_handler)

logger = logging.getLogger(__name__)


class StockAnalysisSystem:
    """股票分析系统主类"""

    def __init__(self):
        self.data_collection_crew = DataCollectionCrew()
        self.analysis_crew = AnalysisCrew()
        self.decision_crew = DecisionCrew()
        self.cache_manager = StockCacheManager()
        logger.info("股票分析系统初始化完成")

    def analyze_stock(self, company: str, ticker: str,
                     use_cache: bool = True) -> Dict[str, Any]:
        """分析单只股票"""
        logger.info(f"开始分析股票: {company} ({ticker})")

        if use_cache and self.cache_manager.check_cache(ticker):
            logger.info(f"使用缓存数据: {ticker}")
            return self.cache_manager.get_from_cache(ticker)

        try:
            logger.info("第一阶段：数据收集")
            collection_result = self.data_collection_crew.execute_data_collection(company, ticker)
            if collection_result['status'] != 'success':
                return {'success': False, 'error': f"数据收集失败: {collection_result.get('error', '未知错误')}",
                        'company': company, 'ticker': ticker}

            logger.info("第二阶段：分析")
            analysis_result = self.analysis_crew.execute_analysis(company, ticker, collection_result['result'])
            if not analysis_result['success']:
                return {'success': False, 'error': f"分析失败: {analysis_result['error']}",
                        'company': company, 'ticker': ticker}

            logger.info("第三阶段：决策")
            decision_result = self.decision_crew.execute_decision_process(company, ticker, analysis_result['result'])
            if not decision_result['success']:
                return {'success': False, 'error': f"决策失败: {decision_result['error']}",
                        'company': company, 'ticker': ticker}

            final_result = self._integrate_results(
                company, ticker,
                collection_result['data'], analysis_result['data'], decision_result['data']
            )
            if use_cache:
                self.cache_manager.save_to_cache(ticker, final_result)
            self.cache_manager.add_to_history(final_result)
            logger.info(f"股票分析完成: {company} ({ticker})")
            return final_result

        except Exception as e:
            logger.error(f"股票分析异常: {company} ({ticker}), 错误: {str(e)}")
            return {'success': False, 'error': f"分析过程发生异常: {str(e)}",
                    'company': company, 'ticker': ticker}

    def analyze_multiple_stocks(self, stocks: List[Dict[str, str]],
                               max_workers: int = 3) -> List[Dict[str, Any]]:
        """批量分析多只股票"""
        logger.info(f"开始批量分析 {len(stocks)} 只股票")
        results = []
        lock = threading.Lock()

        def analyze_single_stock(stock_data):
            result = self.analyze_stock(stock_data['company'], stock_data['ticker'], use_cache=True)
            with lock:
                results.append(result)

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(analyze_single_stock, stock) for stock in stocks]
            concurrent.futures.wait(futures)

        logger.info(f"批量分析完成，成功: {len([r for r in results if r['success']])}/{len(stocks)}")
        return results

    def generate_summary_report(self, results: List[Dict[str, Any]]) -> str:
        return generate_summary_report(results)

    def _integrate_results(self, company: str, ticker: str,
                          collection_data: Dict, analysis_data: Dict,
                          decision_data: Dict) -> Dict[str, Any]:
        scores = self.analysis_crew.calculate_analysis_score(analysis_data)
        investment_rating = self.decision_crew.get_investment_rating(decision_data)
        analysis_summary = self.analysis_crew.generate_analysis_summary(analysis_data)
        full_report = self.decision_crew.generate_investment_report(
            company, ticker, {**collection_data, **analysis_data, **decision_data}
        )
        report_path = self.decision_crew.save_report(company, ticker, full_report)
        data_path = self.decision_crew.export_to_json(company, ticker, {
            'company': company, 'ticker': ticker,
            'collection_data': collection_data, 'analysis_data': analysis_data,
            'decision_data': decision_data, 'scores': scores, 'investment_rating': investment_rating
        })
        return {
            'success': True, 'company': company, 'ticker': ticker,
            'timestamp': datetime.now().isoformat(),
            'collection_data': collection_data, 'analysis_data': analysis_data,
            'decision_data': decision_data, 'scores': scores,
            'investment_rating': investment_rating, 'analysis_summary': analysis_summary,
            'full_report': full_report, 'report_path': report_path, 'data_path': data_path,
            'overall_score': scores['overall_score']
        }

    def get_analysis_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        return self.cache_manager.get_analysis_history(limit)

    def get_cache_stats(self) -> Dict[str, Any]:
        return self.cache_manager.get_cache_stats()

    def clear_cache(self):
        self.cache_manager.clear_cache()

    def export_history(self, filepath: str):
        self.cache_manager.export_history(filepath)


# 使用示例
if __name__ == "__main__":
    system = StockAnalysisSystem()
    print("=== 单个股票分析 ===")
    result = system.analyze_stock("苹果公司", "AAPL")
    if result['success']:
        print(f"分析成功: {result['company']}")
        print(f"投资评级: {result['investment_rating']['rating']}")
        print(f"综合评分: {result['overall_score']:.1f}/100")
    else:
        print(f"分析失败: {result['error']}")

    print("\n=== 批量股票分析 ===")
    stocks = [{'company': '微软', 'ticker': 'MSFT'}, {'company': '谷歌', 'ticker': 'GOOGL'},
              {'company': '亚马逊', 'ticker': 'AMZN'}]
    batch_results = system.analyze_multiple_stocks(stocks)
    print(f"批量分析完成: {len(batch_results)} 只股票")

    summary = system.generate_summary_report(batch_results)
    print(f"\n=== 摘要报告 ===\n{summary[:500]}...")

    print(f"\n缓存统计: {system.get_cache_stats()}")
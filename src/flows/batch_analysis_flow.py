# src/flows/batch_analysis_flow.py
"""
批量分析流程控制
使用Flows实现批量股票分析流程控制
"""
from crewai.flow.flow import Flow, listen, start, router
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
import logging
from datetime import datetime

# 导入团队和工具
from src.crews.data_collection_crew import DataCollectionCrew
from src.crews.analysis_crew import AnalysisCrew
from src.crews.decision_crew import DecisionCrew
from src.utils.batch_analyzer import BatchStockAnalyzer

logger = logging.getLogger(__name__)


class BatchAnalysisState(BaseModel):
    """批量分析状态模型"""
    stocks: List[Dict[str, str]] = []
    results: Dict[str, Any] = {}
    errors: List[Dict[str, Any]] = []
    progress: Dict[str, Any] = {}
    strategy: str = "parallel"
    max_workers: int = 5
    current_stage: str = "initialized"
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    success_count: int = 0
    failure_count: int = 0


class BatchAnalysisFlow(Flow[BatchAnalysisState]):
    """批量分析流程"""

    def __init__(self):
        super().__init__()
        self.batch_analyzer = BatchStockAnalyzer()

    @start()
    def initialize_batch_analysis(self):
        """初始化批量分析"""
        logger.info("=== 初始化批量分析流程 ===")
        self.state.current_stage = "initialization"
        self.state.start_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # 设置默认股票列表
        default_stocks = [
            {'company': '苹果公司', 'ticker': 'AAPL'},
            {'company': '微软', 'ticker': 'MSFT'},
            {'company': '谷歌', 'ticker': 'GOOGL'},
            {'company': '亚马逊', 'ticker': 'AMZN'},
            {'company': '特斯拉', 'ticker': 'TSLA'}
        ]

        self.state.stocks = default_stocks
        self.state.strategy = "parallel"
        self.state.max_workers = 3

        logger.info(f"准备分析 {len(default_stocks)} 只股票")
        return {"stocks": default_stocks, "strategy": "parallel", "max_workers": 3}

    @listen("initialize_batch_analysis")
    def validate_stock_list(self, config_data):
        """验证股票列表"""
        logger.info("=== 验证股票列表 ===")
        self.state.current_stage = "validation"

        try:
            stocks = config_data.get('stocks', [])
            if not stocks:
                return {"success": False, "error": "股票列表为空"}

            # 验证股票格式
            for stock in stocks:
                if not isinstance(stock, dict) or 'company' not in stock or 'ticker' not in stock:
                    return {"success": False, "error": f"股票格式错误: {stock}"}

            self.state.stocks = stocks
            logger.info(f"验证通过: {len(stocks)} 只股票")
            return {"success": True, "stocks": stocks}

        except Exception as e:
            logger.error(f"股票列表验证失败: {str(e)}")
            return {"success": False, "error": str(e)}

    @listen("validate_stock_list")
    def execute_batch_analysis(self, validation_result):
        """执行批量分析"""
        logger.info("=== 执行批量分析 ===")
        self.state.current_stage = "execution"

        try:
            if not validation_result.get('success', False):
                return {"success": False, "error": "验证失败"}

            # 设置进度回调
            def progress_callback(progress):
                self.state.progress = progress
                logger.info(f"进度: {progress.get('percentage', 0):.1f}%")

            self.batch_analyzer.set_progress_callback(progress_callback)

            # 执行批量分析
            result = self.batch_analyzer.analyze_multiple_stocks(
                self.state.stocks,
                strategy=self.state.strategy
            )

            if result['success']:
                self.state.results = result['results']
                self.state.errors = result['errors']
                self.state.success_count = result['success_count']
                self.state.failure_count = result['failure_count']
                self.state.progress = result['progress']

                logger.info("批量分析完成")
                return result
            else:
                logger.error(f"批量分析失败: {result.get('error', '未知错误')}")
                return {"success": False, "error": result.get('error')}

        except Exception as e:
            logger.error(f"批量分析异常: {str(e)}")
            return {"success": False, "error": str(e)}

    @listen("execute_batch_analysis")
    def generate_batch_summary(self, analysis_result):
        """生成批量分析摘要"""
        logger.info("=== 生成批量分析摘要 ===")
        self.state.current_stage = "summary"

        try:
            if not analysis_result.get('success', False):
                return {"success": False, "error": "分析失败"}

            # 生成摘要
            summary = self._generate_summary_report()

            # 导出结果
            export_path = self.batch_analyzer.export_results("json")

            self.state.end_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            logger.info("批量分析摘要生成完成")
            return {
                "success": True,
                "summary": summary,
                "export_path": export_path,
                "total_stocks": len(self.state.stocks),
                "success_count": self.state.success_count,
                "failure_count": self.state.failure_count,
                "success_rate": (self.state.success_count / len(self.state.stocks)) * 100 if self.state.stocks else 0,
                "start_time": self.state.start_time,
                "end_time": self.state.end_time
            }

        except Exception as e:
            logger.error(f"生成摘要异常: {str(e)}")
            return {"success": False, "error": str(e)}

    def _generate_summary_report(self) -> Dict[str, Any]:
        """生成摘要报告"""
        return {
            "analysis_time": self.state.start_time,
            "total_stocks": len(self.state.stocks),
            "successful_analyses": self.state.success_count,
            "failed_analyses": self.state.failure_count,
            "success_rate": (self.state.success_count / len(self.state.stocks)) * 100 if self.state.stocks else 0,
            "average_score": sum(result.get('overall_score', 0) for result in self.state.results.values()) / len(self.state.results) if self.state.results else 0,
            "errors": self.state.errors,
            "top_performers": [
                {"ticker": ticker, "score": result.get('overall_score', 0)}
                for ticker, result in sorted(self.state.results.items(), key=lambda x: x[1].get('overall_score', 0), reverse=True)[:3]
            ],
            "bottom_performers": [
                {"ticker": ticker, "score": result.get('overall_score', 0)}
                for ticker, result in sorted(self.state.results.items(), key=lambda x: x[1].get('overall_score', 0))[:3]
            ]
        }

    def run_batch_analysis(self, stocks: List[Dict[str, str]], strategy: str = "parallel", max_workers: int = 5) -> Dict[str, Any]:
        """运行批量分析"""
        self.state.stocks = stocks
        self.state.strategy = strategy
        self.state.max_workers = max_workers
        self.state.start_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        try:
            # 直接使用批量分析器
            self.batch_analyzer = BatchStockAnalyzer(max_workers=max_workers)

            # 设置进度回调
            def progress_callback(progress):
                self.state.progress = progress
                logger.info(f"进度: {progress.get('percentage', 0):.1f}%")

            self.batch_analyzer.set_progress_callback(progress_callback)

            # 执行分析
            result = self.batch_analyzer.analyze_multiple_stocks(stocks, strategy=strategy)

            # 更新状态
            self.state.results = result.get('results', {})
            self.state.errors = result.get('errors', [])
            self.state.success_count = result.get('success_count', 0)
            self.state.failure_count = result.get('failed_count', 0)
            self.state.end_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            # 生成最终结果
            return {
                "success": True,
                "summary": self._generate_summary_report(),
                "results": result.get('results', {}),
                "errors": result.get('errors', []),
                "total_stocks": len(stocks),
                "success_count": self.state.success_count,
                "failure_count": self.state.failure_count,
                "success_rate": (self.state.success_count / len(stocks)) * 100 if stocks else 0,
                "start_time": self.state.start_time,
                "end_time": self.state.end_time
            }

        except Exception as e:
            return {"success": False, "error": str(e)}


# 使用示例
if __name__ == "__main__":
    flow = BatchAnalysisFlow()
    # result = flow.kickoff()  # 启动交互式流程

    # 或者直接运行
    test_stocks = [
        {'company': '苹果公司', 'ticker': 'AAPL'},
        {'company': '微软', 'ticker': 'MSFT'},
        {'company': '谷歌', 'ticker': 'GOOGL'}
    ]

    result = flow.run_batch_analysis(test_stocks, strategy="parallel")
    print(result)
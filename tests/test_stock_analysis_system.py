# tests/test_stock_analysis_system.py
"""
股票分析系统测试
"""
import unittest
import sys
import os
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# 添加src目录到路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from src.stock_analysis_system import StockAnalysisSystem
from src.crews.data_collection_crew import DataCollectionCrew
from src.crews.analysis_crew import AnalysisCrew
from src.crews.decision_crew import DecisionCrew


class TestStockAnalysisSystem(unittest.TestCase):
    """股票分析系统测试"""

    def setUp(self):
        """测试初始化"""
        self.system = StockAnalysisSystem()

    def test_system_initialization(self):
        """测试系统初始化"""
        self.assertIsNotNone(self.system.data_collection_crew)
        self.assertIsNotNone(self.system.analysis_crew)
        self.assertIsNotNone(self.system.decision_crew)
        self.assertEqual(len(self.system.analysis_history), 0)
        self.assertIsInstance(self.system.cache, dict)

    @patch('src.stock_analysis_system.DataCollectionCrew')
    def test_analyze_stock_success(self, mock_crew):
        """测试成功的股票分析"""
        # 模拟数据收集团队
        mock_crew_instance = Mock()
        mock_crew_instance.execute_data_collection.return_value = {
            'success': True,
            'data': {'test': 'data'}
        }
        mock_crew.return_value = mock_crew_instance

        # 模拟分析团队
        with patch.object(self.system.analysis_crew, 'execute_analysis') as mock_analysis:
            mock_analysis.return_value = {
                'success': True,
                'data': {'analysis': 'result'}
            }

            # 模拟决策团队
            with patch.object(self.system.decision_crew, 'execute_decision_process') as mock_decision:
                mock_decision.return_value = {
                    'success': True,
                    'data': {'decision': 'result'}
                }

                # 执行测试
                result = self.system.analyze_stock("测试公司", "TEST", use_cache=False)

                # 验证结果
                self.assertTrue(result['success'])
                self.assertEqual(result['company'], "测试公司")
                self.assertEqual(result['ticker'], "TEST")

    @patch('src.stock_analysis_system.DataCollectionCrew')
    def test_analyze_stock_collection_failure(self, mock_crew):
        """测试数据收集失败的情况"""
        mock_crew_instance = Mock()
        mock_crew_instance.execute_data_collection.return_value = {
            'success': False,
            'error': '数据收集失败'
        }
        mock_crew.return_value = mock_crew_instance

        result = self.system.analyze_stock("测试公司", "TEST", use_cache=False)

        self.assertFalse(result['success'])
        self.assertIn('数据收集失败', result['error'])

    def test_analyze_multiple_stocks(self):
        """测试批量分析"""
        stocks = [
            {'company': '公司1', 'ticker': 'TICKER1'},
            {'company': '公司2', 'ticker': 'TICKER2'}
        ]

        with patch.object(self.system, 'analyze_stock') as mock_analyze:
            mock_analyze.return_value = {
                'success': True,
                'company': '测试公司',
                'ticker': 'TEST',
                'overall_score': 75.0,
                'investment_rating': {'rating': '买入'}
            }

            results = self.system.analyze_multiple_stocks(stocks, max_workers=2)

            self.assertEqual(len(results), 2)
            self.assertTrue(all(result['success'] for result in results))

    def test_cache_functionality(self):
        """测试缓存功能"""
        # 添加数据到缓存
        self.system.cache['TEST'] = {
            'data': {'cached': 'data'},
            'timestamp': datetime.now().timestamp()
        }

        # 测试缓存检查
        self.assertTrue(self.system._check_cache('TEST'))

        # 测试从缓存获取
        cached_data = self.system._get_from_cache('TEST')
        self.assertEqual(cached_data['data']['cached'], 'data')

    def test_generate_summary_report(self):
        """测试生成摘要报告"""
        results = [
            {
                'success': True,
                'company': '公司1',
                'ticker': 'TICKER1',
                'overall_score': 80.0,
                'investment_rating': {'rating': '买入'}
            },
            {
                'success': False,
                'company': '公司2',
                'ticker': 'TICKER2',
                'error': '分析失败'
            }
        ]

        summary = self.system.generate_summary_report(results)

        self.assertIn('总股票数: 2', summary)
        self.assertIn('成功分析: 1', summary)
        self.assertIn('失败分析: 1', summary)
        self.assertIn('成功率: 50.0%', summary)

    def test_clear_cache(self):
        """测试清空缓存"""
        self.system.cache['TEST'] = {'data': 'test'}
        self.system.clear_cache()
        self.assertEqual(len(self.system.cache), 0)


class TestDataCollectionCrew(unittest.TestCase):
    """数据收集团队测试"""

    def setUp(self):
        """测试初始化"""
        self.crew = DataCollectionCrew()

    def test_crew_initialization(self):
        """测试团队初始化"""
        self.assertIsNotNone(self.crew.agents_config)
        self.assertIsNotNone(self.crew.tasks_config)

    @patch('src.crews.data_collection_crew.Crew')
    def test_execute_data_collection(self, mock_crew_class):
        """测试数据收集执行"""
        mock_crew = Mock()
        mock_crew.kickoff.return_value = "分析结果"
        mock_crew_class.return_value = mock_crew

        result = self.crew.execute_data_collection("测试公司", "TEST")

        self.assertTrue(result['success'])
        self.assertEqual(result['company'], "测试公司")
        self.assertEqual(result['ticker'], "TEST")

    @patch('src.crews.data_collection_crew.Crew')
    def test_execute_data_collection_failure(self, mock_crew_class):
        """测试数据收集失败"""
        mock_crew = Mock()
        mock_crew.kickoff.side_effect = Exception("分析失败")
        mock_crew_class.return_value = mock_crew

        result = self.crew.execute_data_collection("测试公司", "TEST")

        self.assertFalse(result['success'])
        self.assertIn("分析失败", result['error'])


class TestAnalysisCrew(unittest.TestCase):
    """分析团队测试"""

    def setUp(self):
        """测试初始化"""
        self.crew = AnalysisCrew()

    def test_crew_initialization(self):
        """测试团队初始化"""
        self.assertIsNotNone(self.crew.agents_config)
        self.assertIsNotNone(self.crew.tasks_config)

    def test_calculate_analysis_score(self):
        """测试分析评分计算"""
        analysis_data = {
            'fundamental_analysis': {'analysis_text': '优秀的基本面'},
            'risk_assessment': {'analysis_text': '风险较低'},
            'industry_analysis': {'analysis_text': '行业领先'},
            'sentiment_analysis': {'analysis_text': '市场情绪积极'}
        }

        scores = self.crew.calculate_analysis_score(analysis_data)

        self.assertIn('fundamental_score', scores)
        self.assertIn('risk_score', scores)
        self.assertIn('overall_score', scores)
        self.assertGreater(scores['overall_score'], 0)
        self.assertLessEqual(scores['overall_score'], 100)

    def test_generate_analysis_summary(self):
        """测试分析摘要生成"""
        analysis_data = {
            'fundamental_analysis': {'analysis_text': '优秀的基本面'},
            'risk_assessment': {'analysis_text': '风险较低'},
            'industry_analysis': {'analysis_text': '行业领先'},
            'sentiment_analysis': {'analysis_text': '市场情绪积极'}
        }

        summary = self.crew.generate_analysis_summary(analysis_data)

        self.assertIn('分析摘要', summary)
        self.assertIn('基本面评分', summary)
        self.assertIn('风险评分', summary)
        self.assertIn('投资建议', summary)


class TestDecisionCrew(unittest.TestCase):
    """决策团队测试"""

    def setUp(self):
        """测试初始化"""
        self.crew = DecisionCrew()

    def test_crew_initialization(self):
        """测试团队初始化"""
        self.assertIsNotNone(self.crew.agents_config)
        self.assertIsNotNone(self.crew.tasks_config)

    def test_get_investment_rating(self):
        """测试投资评级获取"""
        decision_data = {
            'investment_recommendation': {
                'analysis_text': '基于综合分析，建议买入该股票'
            }
        }

        rating = self.crew.get_investment_rating(decision_data)

        self.assertIn('rating', rating)
        self.assertIn('code', rating)
        self.assertIn('color', rating)

    def test_generate_investment_report(self):
        """测试投资报告生成"""
        company = "测试公司"
        ticker = "TEST"
        all_data = {
            'market_research': {'analysis_text': '市场表现良好'},
            'financial_analysis': {'analysis_text': '财务状况稳健'},
            'investment_recommendation': {'analysis_text': '建议买入'}
        }

        report = self.crew.generate_investment_report(company, ticker, all_data)

        self.assertIn(company, report)
        self.assertIn(ticker, report)
        self.assertIn('投资分析报告', report)

    @patch('builtins.open', create=True)
    @patch('os.path.exists')
    def test_save_report(self, mock_exists, mock_open):
        """测试报告保存"""
        mock_exists.return_value = True
        mock_file = Mock()
        mock_open.return_value.__enter__.return_value = mock_file

        report_content = "测试报告内容"
        filepath = self.crew.save_report("测试公司", "TEST", report_content)

        self.assertTrue(filepath.endswith('.md'))
        mock_file.write.assert_called_once_with(report_content)


if __name__ == '__main__':
    # 运行测试
    unittest.main(verbosity=2)
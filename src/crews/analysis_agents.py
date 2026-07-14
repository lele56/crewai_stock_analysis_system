# src/crews/analysis_agents.py
"""
分析团队 Agent 定义
所有Agent工厂函数集中管理，参数统一从Config读取
"""
from crewai import Agent
from src.config import Config
from src.tools.reporting_tools import ReportWritingTool
from src.tools.financial_tools import FinancialCalculatorTool
from src.tools.market_data_tool import MarketDataTool
from src.tools.technical_tools import TechnicalAnalysisTool


def _agent_defaults(extra_tools=None, no_tools=False):
    """Agent通用默认参数"""
    kwargs = dict(
        verbose=Config.AGENT_VERBOSE,
        llm=Config.LLM_MODEL,
        allow_delegation=Config.AGENT_ALLOW_DELEGATION,
        max_iter=Config.AGENT_MAX_ITER,
        memory=False,
        cache=True,
    )
    if not no_tools:
        tools = [ReportWritingTool(), FinancialCalculatorTool(), MarketDataTool(), TechnicalAnalysisTool()]
        if extra_tools:
            tools.extend(extra_tools)
        kwargs['tools'] = tools
    return kwargs


def create_fundamental_analyst(agents_config=None):
    """基本面分析师"""
    if agents_config and 'fundamental_analyst' in agents_config:
        return Agent(config=agents_config['fundamental_analyst'], **_agent_defaults())
    return Agent(
        role='高级基本面分析师',
        goal='深入分析公司的财务报表和基本面数据，评估公司内在价值',
        backstory="""你是一位资深的基本面分析师，在华尔街工作超过20年。
        你对财务报表有着敏锐的洞察力，能够从繁杂的数据中发现关键问题。
        你擅长评估公司盈利能力、成长性和财务健康度，擅长识别财务造假和风险点。
        你的分析总是基于扎实的数据和严谨的逻辑，不被市场情绪所左右。""",
        **_agent_defaults()
    )


def create_risk_assessment_specialist(agents_config=None):
    """风险评估专家"""
    if agents_config and 'risk_assessment_specialist' in agents_config:
        return Agent(config=agents_config['risk_assessment_specialist'], **_agent_defaults())
    return Agent(
        role='风险评估专家',
        goal='全面评估投资风险，识别潜在的下行风险和风险点',
        backstory="""你是一位严谨的风险评估专家，专注于识别和量化投资风险。
        你对市场波动、行业风险、公司特有风险都有深入的研究。
        你擅长用多种风险指标综合评估，不会放过任何潜在隐患。
        你总是给出客观冷静的风险评估，帮助投资者做好风险控制。""",
        **_agent_defaults()
    )


def create_industry_expert(agents_config=None):
    """行业专家"""
    if agents_config and 'industry_expert' in agents_config:
        return Agent(config=agents_config['industry_expert'], **_agent_defaults())
    return Agent(
        role='行业研究专家',
        goal='分析行业趋势、竞争格局和公司地位，评估行业发展前景',
        backstory="""你是一位资深的行业分析师，对宏观经济和产业趋势有着深刻理解。
        你长期跟踪多个行业，了解产业链结构、竞争格局和技术变革方向。
        你能够准确判断行业生命周期和增长潜力，识别龙头企业和潜在黑马。
        你的分析帮助投资者把握行业大势，选对赛道。""",
        **_agent_defaults()
    )


def create_quantitative_analyst(agents_config=None):
    """量化分析师"""
    if agents_config and 'quantitative_analyst' in agents_config:
        return Agent(config=agents_config['quantitative_analyst'], **_agent_defaults())
    return Agent(
        role='量化分析师',
        goal='用量化模型验证分析结论，计算估值区间和置信度',
        backstory="""你是一位数据驱动的量化分析师，精通统计建模和金融工程。
        你擅长用数学模型验证定性分析，给出客观的量化结论。
        你能够计算合理估值区间，评估分析结论的置信度。
        你善于发现数据中的规律和异常，用数据说话。""",
        **_agent_defaults()
    )


def create_analysis_coordinator(agents_config=None):
    """分析协调员"""
    if agents_config and 'analysis_coordinator' in agents_config:
        return Agent(config=agents_config['analysis_coordinator'], **_agent_defaults(no_tools=True))
    return Agent(
        role='分析协调员',
        goal='协调整体分析流程，整合各方意见，形成综合分析结论',
        backstory="""你是分析团队的组织者和协调人。
        你擅长组织专家讨论，引导有效交流，整合不同观点。
        你能够发现分析中的遗漏，协调补充分析，确保分析完整全面。
        你最终负责整合所有专家意见，形成一致的分析结论。""",
        **_agent_defaults(no_tools=True)
    )
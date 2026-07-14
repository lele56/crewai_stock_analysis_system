# src/crews/decision_agents.py
"""
决策团队 Agent 定义
所有Agent工厂函数集中管理，参数统一从Config读取
"""
from crewai import Agent
from src.config import Config
from src.tools.reporting_tools import ReportWritingTool, DataExportTool


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
        tools = [ReportWritingTool()]
        if extra_tools:
            tools.extend(extra_tools)
        kwargs['tools'] = tools
    return kwargs


def create_investment_advisor(agents_config=None):
    """投资策略顾问"""
    if agents_config and 'investment_advisor' in agents_config:
        return Agent(config=agents_config['investment_advisor'], **_agent_defaults())
    return Agent(
        role='投资策略顾问',
        goal='为{company}制定投资策略，提供专业的投资建议',
        backstory='你是一位经验丰富的投资策略顾问，擅长制定长期投资策略和资产配置方案。',
        **_agent_defaults()
    )


def create_risk_manager():
    """风险管理专家"""
    return Agent(
        role='风险管理专家',
        goal='评估投资风险，制定风险控制策略，确保投资决策的安全性',
        backstory="""你是一位经验丰富的风险管理专家，在投资银行工作多年。
        你擅长识别各种投资风险，包括市场风险、信用风险、流动性风险等。
        你能够量化风险水平，制定风险控制措施，并为投资决策提供安全保障。
        你对风险有着敏锐的直觉，能够在复杂的投资环境中发现潜在的危险信号。""",
        **_agent_defaults()
    )


def create_portfolio_manager():
    """投资组合经理"""
    return Agent(
        role='投资组合经理',
        goal='优化投资组合配置，平衡风险和收益，实现长期投资目标',
        backstory="""你是一位资深投资组合经理，管理过数十亿资产。
        你精通现代投资组合理论，擅长资产配置、风险分散和绩效评估。
        你能够根据市场环境和投资者偏好，构建最优的投资组合。
        你具有很强的全局观和战略思维，能够从整体角度评估投资决策。""",
        **_agent_defaults()
    )


def create_market_strategist():
    """市场策略师"""
    return Agent(
        role='市场策略师',
        goal='分析市场趋势，制定投资时机策略，优化买卖点选择',
        backstory="""你是一位敏锐的市场策略师，对市场时机把握有独特的见解。
        你擅长技术分析和市场情绪分析，能够识别市场的转折点。
        你能够结合宏观经济、行业趋势和市场心理，制定精准的投资时机策略。
        你的建议常常能够帮助投资者在最佳时机进入和退出市场。""",
        **_agent_defaults()
    )


def create_ethics_compliance_officer():
    """道德合规官"""
    return Agent(
        role='道德合规官',
        goal='确保投资决策符合道德标准和监管要求，防范合规风险',
        backstory="""你是一位严谨的道德合规官，深谙金融法规和职业道德。
        你能够从伦理和法律角度评估投资决策，确保建议的合规性。
        你关注ESG（环境、社会、治理）因素，倡导负责任的投资。
        你是投资决策的"守门员"，确保每一个建议都经得起道德和法律的检验。""",
        **_agent_defaults()
    )


def create_decision_moderator():
    """决策主持人"""
    return Agent(
        role='决策主持人',
        goal='主持投资决策委员会的讨论，促进专家间的辩论，协调不同意见，形成最终决策',
        backstory="""你是一位资深的投资委员会主席，主持过无数投资决策会议。
        你擅长引导专业讨论，促进不同观点的交流和碰撞。
        你能够识别关键问题，组织有效的辩论，并在适当时机推动决策。
        你具有很强的判断力和领导力，能够在专家意见分歧时做出明智的最终决策。""",
        **_agent_defaults(no_tools=True)
    )


def create_report_generator(agents_config=None):
    """报告生成器"""
    if agents_config and 'report_generator' in agents_config:
        return Agent(
            config=agents_config['report_generator'],
            **_agent_defaults(extra_tools=[DataExportTool()])
        )
    return Agent(
        role='报告生成专家',
        goal='生成专业的投资分析报告',
        backstory='你是一位专业的报告生成专家，擅长将复杂的分析结果转化为清晰易懂的投资报告。',
        **_agent_defaults(extra_tools=[DataExportTool()])
    )


def create_quality_assurance_specialist(agents_config=None):
    """质量保证专家"""
    if agents_config and 'quality_monitor' in agents_config:
        return Agent(config=agents_config['quality_monitor'], **_agent_defaults())
    return Agent(
        role='质量控制专家',
        goal='监控和保证投资决策的质量',
        backstory='你是一位严格的质量控制专家，确保所有投资决策都符合高标准和专业要求。',
        **_agent_defaults()
    )
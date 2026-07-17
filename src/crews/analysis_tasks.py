# src/crews/analysis_tasks.py
"""分析团队 Task 定义"""

from crewai import Task


def create_fundamental_analysis_task(tasks_config: dict | None = None) -> Task:
    """创建基本面分析任务"""
    if tasks_config and "fundamental_analysis" in tasks_config:
        return Task(
            config=tasks_config["fundamental_analysis"],
            agent=None,
        )
    return Task(
        description="""基于以下采集数据，对{company}进行深度基本面分析：

【原始采集数据】
{raw_data}

请完成以下分析：
1. 分析财务报表（营收、利润、现金流、资产负债）
2. 评估盈利能力指标（ROE、ROA、毛利率、净利率）
3. 评估成长性（营收增长率、利润增长率）
4. 评估财务健康度（负债率、流动比率、利息覆盖倍数）
5. 计算合理估值区间和置信度
6. 用量化方法验证分析结论的数据支撑
7. 给出基本面评分（0-100）""",
        expected_output="基本面分析报告（含量化验证），含评分和详细分析",
        agent=None,
    )


def create_risk_assessment_task(tasks_config: dict | None = None) -> Task:
    """创建风险评估任务"""
    if tasks_config and "risk_assessment" in tasks_config:
        return Task(
            config=tasks_config["risk_assessment"],
            agent=None,
        )
    return Task(
        description="""基于以下采集数据，对{company}进行风险评估：

【原始采集数据】
{raw_data}

请完成以下分析：
1. 分析市场风险（波动率、Beta、最大回撤）
2. 分析行业风险（政策、竞争、技术变革）
3. 分析公司特有风险（治理、财务、法律）
4. 量化综合风险水平
5. 给出风险评分（0-100，越低越安全）""",
        expected_output="风险评估报告，含评分和风险矩阵",
        agent=None,
    )


def create_industry_analysis_task(tasks_config: dict | None = None) -> Task:
    """创建行业分析任务"""
    if tasks_config and "industry_analysis" in tasks_config:
        return Task(
            config=tasks_config["industry_analysis"],
            agent=None,
        )
    return Task(
        description="""基于以下采集数据，对{company}所在行业进行深度分析：

【原始采集数据】
{raw_data}

请完成以下分析：
1. 行业市场规模和增长趋势
2. 竞争格局分析（波特五力模型）
3. 公司在行业中的定位和竞争优势
4. 行业发展趋势和机遇挑战
5. 给出行业评分（0-100）""",
        expected_output="行业分析报告，含评分和竞争分析",
        agent=None,
    )


def create_analysis_coordination_task(tasks_config: dict | None = None) -> Task:
    """创建分析协调任务"""
    if tasks_config and "analysis_coordination" in tasks_config:
        return Task(
            config=tasks_config["analysis_coordination"],
            agent=None,
        )
    return Task(
        description="""整合所有分析结果，形成最终的综合分析报告：
        1. 汇总基本面、风险、行业三个维度的评分
        2. 计算加权综合评分
        3. 分析各维度的一致性
        4. 给出综合投资建议""",
        expected_output="综合分析报告，含综合评分和投资建议",
        agent=None,
    )
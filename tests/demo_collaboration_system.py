# tests/demo_collaboration_system.py
"""
协作系统演示脚本 - 基础功能
展示智能体间的通信和任务分配功能
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.tools.communication_tools import (
    global_communication_hub, MessageType, MessagePriority,
    get_communication_tool, generate_communication_summary
)
from src.tasks.dynamic_task_allocation import (
    get_task_allocator, AgentCapability, TaskComplexity,
    AgentProfile, DynamicTask
)
from src.tools.collaboration_tools import (
    get_task_orchestration_tool,
    CollaborationOptimizer
)
from datetime import datetime
import json
import time


def demo_basic_communication():
    """演示基本通信功能"""
    print("=" * 60)
    print("演示1: 基本智能体通信")
    print("=" * 60)

    market_tool = get_communication_tool("市场研究员")
    financial_tool = get_communication_tool("财务分析师")
    technical_tool = get_communication_tool("技术分析师")

    print("1. 市场研究员向财务分析师发送数据请求...")
    result1 = market_tool._run(
        "send_message",
        receiver="财务分析师",
        message_type="information_request",
        subject="请求苹果公司财务数据",
        content={
            "required_data": ["营收", "利润", "毛利率"],
            "time_period": "最近3年",
            "deadline": "2024-01-15"
        },
        priority="high"
    )
    print(f"   结果: {result1}")

    print("\n2. 市场研究员向技术分析师委托分析任务...")
    result2 = market_tool._run(
        "delegate_task",
        delegatee="技术分析师",
        original_task="苹果公司市场分析",
        delegated_task="技术指标验证",
        reason="需要技术分析验证市场趋势",
        deadline="2024-01-20"
    )
    print(f"   结果: {result2}")

    print("\n3. 财务分析师检查新消息...")
    result3 = financial_tool._run("check_messages")
    print(f"   结果: {result3}")

    print("\n4. 财务分析师响应数据请求...")
    response_content = {
        "financial_data": "已获取苹果公司最近3年财务数据",
        "revenue_growth": "年复合增长率8.5%",
        "profit_margin": "平均毛利率42%",
        "data_quality": "优秀"
    }
    result4 = financial_tool._run(
        "respond_to_message",
        message_id="msg_001",
        response_content=response_content,
        response_type="accept"
    )
    print(f"   结果: {result4}")

    print("\n5. 生成通信报告...")
    report = generate_communication_summary()
    print(f"   总消息数: {report['total_messages']}")
    print(f"   总委托数: {report['total_delegations']}")
    print(f"   通信效率: {report['communication_efficiency']:.2f}")


def demo_task_allocation():
    """演示动态任务分配"""
    print("\n" + "=" * 60)
    print("演示2: 动态任务分配")
    print("=" * 60)

    allocator = get_task_allocator()

    print("1. 注册分析智能体...")
    allocator.register_agent(
        "基本面专家",
        [AgentCapability.FUNDAMENTAL_ANALYSIS, AgentCapability.INDUSTRY_ANALYSIS],
        {AgentCapability.FUNDAMENTAL_ANALYSIS: 0.95, AgentCapability.INDUSTRY_ANALYSIS: 0.85},
        max_workload=100.0
    )

    allocator.register_agent(
        "技术专家",
        [AgentCapability.TECHNICAL_ANALYSIS, AgentCapability.QUANTITATIVE_ANALYSIS],
        {AgentCapability.TECHNICAL_ANALYSIS: 0.90, AgentCapability.QUANTITATIVE_ANALYSIS: 0.80},
        max_workload=80.0
    )

    allocator.register_agent(
        "风险评估师",
        [AgentCapability.RISK_ASSESSMENT, AgentCapability.VALIDATION],
        {AgentCapability.RISK_ASSESSMENT: 0.95, AgentCapability.VALIDATION: 0.75},
        max_workload=60.0
    )

    print("   已注册3个智能体")

    print("\n2. 创建分析任务...")
    tasks = [
        ("苹果公司基本面深度分析", "对苹果公司进行全面的基本面分析，包括商业模式、竞争优势等",
         [AgentCapability.FUNDAMENTAL_ANALYSIS], TaskComplexity.HIGH, 9),
        ("技术指标计算分析", "计算并分析主要技术指标，识别趋势信号",
         [AgentCapability.TECHNICAL_ANALYSIS], TaskComplexity.MEDIUM, 7),
        ("风险评估报告", "识别和评估苹果公司的各类投资风险",
         [AgentCapability.RISK_ASSESSMENT], TaskComplexity.HIGH, 8),
        ("行业对比分析", "将苹果公司与同行业公司进行对比分析",
         [AgentCapability.INDUSTRY_ANALYSIS], TaskComplexity.MEDIUM, 6),
        ("量化模型验证", "使用统计方法验证分析结果的可靠性",
         [AgentCapability.QUANTITATIVE_ANALYSIS], TaskComplexity.HIGH, 8)
    ]

    task_ids = []
    for name, desc, caps, complexity, priority in tasks:
        task_id = allocator.create_task(
            name=name, description=desc,
            required_capabilities=caps,
            complexity=complexity, priority=priority
        )
        task_ids.append(task_id)
        print(f"   已创建任务: {name} (ID: {task_id})")

    print(f"\n3. 开始任务分配...")
    allocated_tasks = allocator.allocate_tasks()

    print(f"   成功分配 {len(allocated_tasks)} 个任务")
    for task_id in allocated_tasks:
        task = None
        for t in allocator.active_tasks.values():
            if t.id == task_id:
                task = t
                break
        if task:
            print(f"   - {task.name} -> {task.assigned_agent}")

    print("\n4. 智能体工作负载:")
    for agent_name in allocator.agent_profiles:
        workload = allocator.get_agent_workload(agent_name)
        print(f"   {agent_name}: {workload['workload_percentage']:.1f}% 负载, "
              f"{workload['active_tasks']} 个活跃任务")

    print("\n5. 模拟任务完成...")
    for i, task_id in enumerate(allocated_tasks[:2]):
        time.sleep(0.5)
        allocator.complete_task(
            task_id=task_id,
            result={
                "status": "completed",
                "quality_score": 0.85 + i * 0.05,
                "completion_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            },
            success=True
        )
        print(f"   任务 {task_id} 已完成")

    print("\n6. 任务分配统计:")
    stats = allocator.get_allocation_statistics()
    print(f"   总任务数: {stats['total_tasks']}")
    print(f"   已完成: {stats['completed_tasks']}")
    print(f"   进行中: {stats['active_tasks']}")
    print(f"   待分配: {stats['pending_tasks']}")


def demo_collaboration_optimization():
    """演示协作优化"""
    print("\n" + "=" * 60)
    print("演示3: 协作效率优化")
    print("=" * 60)

    optimizer = CollaborationOptimizer()
    orchestration_tool = get_task_orchestration_tool("协调员")

    print("1. 分析当前协作状态...")
    analysis = optimizer.analyze_collaboration_patterns()

    print(f"   协作效率分数: {analysis['collaboration_efficiency']:.2f}")
    print(f"   发现瓶颈: {len(analysis['bottlenecks'])} 个")

    if analysis['bottlenecks']:
        print("   瓶颈详情:")
        for bottleneck in analysis['bottlenecks']:
            print(f"     - {bottleneck}")

    print(f"   优化建议: {len(analysis['recommendations'])} 条")
    for rec in analysis['recommendations'][:3]:
        print(f"     - {rec}")

    print("\n2. 执行工作流程优化...")
    optimization = optimizer.optimize_workflow()

    print(f"   优化操作: {len(optimization['optimization_actions'])} 项")
    if optimization['optimization_actions']:
        print("   优化措施:")
        for action in optimization['optimization_actions']:
            print(f"     - {action}")
    else:
        print("   暂无优化操作建议")

    print("\n3. 使用任务编排工具...")
    result = orchestration_tool._run(
        "create_task",
        name="协作优化任务",
        description="测试协作优化后的任务分配",
        capabilities=["fundamental_analysis"],
        complexity="medium",
        priority=7
    )
    print(f"   {result}")

    result = orchestration_tool._run("allocate_tasks")
    print(f"   {result}")

    print("\n4. 优化后效果分析...")
    new_analysis = optimizer.analyze_collaboration_patterns()
    efficiency_improvement = new_analysis['collaboration_efficiency'] - analysis['collaboration_efficiency']
    print(f"   效率提升: {efficiency_improvement:+.3f}")


def main():
    """主演示函数"""
    print("CrewAI 协作系统演示")
    print("展示智能体间的通信、任务分配和协作优化功能")
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    try:
        demo_basic_communication()
        demo_task_allocation()
        demo_collaboration_optimization()

        print("\n" + "=" * 60)
        print("基础演示完成!")
        print("=" * 60)
        print(f"结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("\n本演示展示了:")
        print("✓ 智能体间消息传递和通信")
        print("✓ 任务委托和工作分配")
        print("✓ 动态任务负载均衡")
        print("✓ 协作效率优化分析")

    except Exception as e:
        print(f"\n演示过程中出现错误: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
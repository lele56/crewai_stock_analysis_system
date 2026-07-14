# tests/demo_advanced_collaboration.py
"""
协作系统高级演示脚本
展示集体决策和复杂协作场景
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.tools.communication_tools import generate_communication_summary
from src.tasks.dynamic_task_allocation import (
    get_task_allocator, get_decision_maker, DecisionType
)
from src.tools.collaboration_tools import (
    get_task_orchestration_tool, get_collective_decision_tool,
    create_collaborative_analysis_task, create_investment_decision_committee
)
from datetime import datetime
import time
from collections import Counter


def demo_collective_decision():
    """演示集体决策"""
    print("=" * 60)
    print("演示1: 集体投资决策")
    print("=" * 60)

    decision_maker = get_decision_maker()

    print("1. 组建投资决策委员会...")
    voters = [
        "投资委员会主席",
        "风险管理总监",
        "首席投资经理",
        "研究部主管",
        "合规官"
    ]

    weights = {
        "投资委员会主席": 3.0,
        "风险管理总监": 2.5,
        "首席投资经理": 2.0,
        "研究部主管": 1.5,
        "合规官": 1.0
    }

    vote_id = decision_maker.create_vote(
        topic="苹果公司(AAPL)投资决策",
        options=["强烈买入", "买入", "持有", "卖出", "强烈卖出"],
        voters=voters,
        decision_type=DecisionType.WEIGHTED,
        weights=weights
    )

    print(f"   决策投票已创建 (ID: {vote_id})")
    print(f"   参与者: {', '.join(voters)}")

    print("\n2. 开始投票过程...")
    votes = [
        ("投资委员会主席", "买入", "基于强劲的基本面和市场地位"),
        ("风险管理总监", "持有", "考虑到估值偏高和市场波动风险"),
        ("首席投资经理", "买入", "长期增长潜力依然看好"),
        ("研究部主管", "强烈买入", "新产品线将带来显著增长"),
        ("合规官", "持有", "需要进一步评估监管风险")
    ]

    for voter, option, reason in votes:
        time.sleep(0.8)
        print(f"   {voter} 投票: {option}")
        decision_maker.cast_vote(vote_id, voter, option)

    print("\n3. 投票完成，计算结果...")
    time.sleep(1)

    vote_status = decision_maker.get_vote_status(vote_id)
    print(f"   最终决策: {vote_status['result']}")
    print(f"   置信度: {vote_status['confidence']:.2f}")

    print("\n4. 投票详情统计:")
    final_vote = None
    for vote in decision_maker.vote_history:
        if vote.vote_id == vote_id:
            final_vote = vote
            break

    if final_vote:
        vote_counts = Counter(final_vote.votes.values())
        for option, count in vote_counts.items():
            percentage = (count / len(final_vote.votes)) * 100
            print(f"   {option}: {count} 票 ({percentage:.1f}%)")

    print("\n5. 决策系统统计:")
    stats = decision_maker.get_decision_statistics()
    print(f"   总投票数: {stats['total_votes']}")
    print(f"   平均置信度: {stats['average_confidence']:.2f}")


def demo_complex_collaboration():
    """演示复杂协作场景"""
    print("\n" + "=" * 60)
    print("演示2: 复杂协作场景 - 苹果公司投资分析")
    print("=" * 60)

    print("1. 启动多智能体协作分析...")
    task_ids = create_collaborative_analysis_task(
        company="苹果公司",
        ticker="AAPL",
        analysis_types=["fundamental", "technical", "risk", "quantitative", "industry"]
    )

    print(f"   已创建 {len(task_ids)} 个协作分析任务")

    print("\n2. 组建高级投资决策委员会...")
    committee_id = create_investment_decision_committee("苹果公司", "AAPL")
    print(f"   委员会已组建 (ID: {committee_id})")

    coordinator = get_task_orchestration_tool("项目协调员")

    print("\n3. 项目协调和监控...")
    workload_result = coordinator._run("get_workload")
    print(f"   {workload_result}")

    analysis_result = coordinator._run("analyze_collaboration")
    print(f"   {analysis_result}")

    print("\n4. 高级决策过程...")
    committee_tool = get_collective_decision_tool("投资委员会")

    strategy_vote_id = committee_tool._run(
        "create_strategy_vote",
        strategy_name="苹果公司长期投资策略",
        options=["激进增长策略", "稳健增值策略", "收入策略", "价值投资策略"]
    )
    print(f"   {strategy_vote_id}")

    print("\n5. 最终协作统计...")
    comm_summary = generate_communication_summary()
    allocator = get_task_allocator()
    task_stats = allocator.get_allocation_statistics()
    decision_maker = get_decision_maker()
    decision_stats = decision_maker.get_decision_statistics()

    print(f"   通信活动:")
    print(f"     - 总消息: {comm_summary['total_messages']}")
    print(f"     - 任务委托: {comm_summary['total_delegations']}")
    print(f"     - 协作项目: {comm_summary['active_collaborations']}")

    print(f"   任务执行:")
    print(f"     - 总任务: {task_stats['total_tasks']}")
    print(f"     - 完成率: {task_stats['completed_tasks'] / max(1, task_stats['total_tasks']) * 100:.1f}%")

    print(f"   决策质量:")
    print(f"     - 决策次数: {decision_stats['total_votes']}")
    print(f"     - 平均置信度: {decision_stats['average_confidence']:.2f}")

    print("\n   协作系统演示完成!")


def main():
    """主演示函数"""
    print("CrewAI 协作系统高级演示")
    print("展示集体决策和复杂协作场景")
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    try:
        demo_collective_decision()
        demo_complex_collaboration()

        print("\n" + "=" * 60)
        print("高级演示完成!")
        print("=" * 60)
        print(f"结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("\n本演示展示了:")
        print("✓ 集体决策和投票机制")
        print("✓ 多智能体协作工作流程")
        print("✓ 复杂投资分析场景")

    except Exception as e:
        print(f"\n演示过程中出现错误: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
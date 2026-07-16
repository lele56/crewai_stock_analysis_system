# tests/test_collective_decision.py
from src.tasks.collective_decision_maker import (
    CollectiveDecisionMaker,
    create_investment_decision_vote,
    get_decision_maker,
)
from src.tasks.task_dataclasses import DecisionType, VotingRecord


class TestCollectiveDecisionMaker:
    def test_init(self):
        dm = CollectiveDecisionMaker()
        assert dm.decision_type == DecisionType.WEIGHTED
        assert len(dm.history) == 0

    def test_cast_vote(self):
        dm = CollectiveDecisionMaker()
        vote = dm.cast_vote("测试分析师", "买入", 0.85, "基本面良好")
        assert isinstance(vote, VotingRecord)
        assert vote.voter == "测试分析师"
        assert vote.vote == "买入"
        assert vote.confidence == 0.85

    def test_decide_weighted(self):
        dm = CollectiveDecisionMaker(decision_type=DecisionType.WEIGHTED)
        votes = [
            dm.cast_vote("分析师A", "买入", 0.8),
            dm.cast_vote("分析师B", "强烈买入", 0.9),
            dm.cast_vote("分析师C", "持有", 0.7),
        ]
        result = dm.decide(votes)
        assert "result" in result
        assert "confidence" in result
        assert result["voter_count"] == 3
        assert result["result"] in ["买入", "强烈买入"]

    def test_decide_majority(self):
        dm = CollectiveDecisionMaker(decision_type=DecisionType.MAJORITY)
        votes = [
            dm.cast_vote("A", "买入", 0.8),
            dm.cast_vote("B", "买入", 0.7),
            dm.cast_vote("C", "持有", 0.6),
        ]
        result = dm.decide(votes)
        assert result["result"] == "买入"

    def test_decide_unanimous_all_agree(self):
        dm = CollectiveDecisionMaker(decision_type=DecisionType.UNANIMOUS)
        votes = [
            dm.cast_vote("A", "买入", 0.8),
            dm.cast_vote("B", "买入", 0.7),
        ]
        result = dm.decide(votes)
        assert result["result"] == "买入"
        assert result["confidence"] == 1.0

    def test_decide_unanimous_disagree(self):
        dm = CollectiveDecisionMaker(decision_type=DecisionType.UNANIMOUS)
        votes = [
            dm.cast_vote("A", "买入", 0.8),
            dm.cast_vote("B", "持有", 0.7),
        ]
        result = dm.decide(votes)
        assert result["confidence"] < 1.0

    def test_decide_empty_votes(self):
        dm = CollectiveDecisionMaker()
        result = dm.decide([])
        assert result["result"] == "持有"
        assert result["confidence"] == 0.0
        assert result["voter_count"] == 0

    def test_history_kept(self):
        dm = CollectiveDecisionMaker()
        votes = [create_investment_decision_vote("test", 50, 0.5)]
        dm.decide(votes)
        assert len(dm.history) == 1

    def test_clear_history(self):
        dm = CollectiveDecisionMaker()
        votes = [create_investment_decision_vote("test", 50, 0.5)]
        dm.decide(votes)
        dm.clear_history()
        assert len(dm.history) == 0


class TestConvenienceFunctions:
    def test_create_investment_decision_vote_high_score(self):
        vote = create_investment_decision_vote("test", 90, 0.8)
        assert vote.vote == "强烈买入"
        assert vote.confidence == 0.8

    def test_create_investment_decision_vote_low_score(self):
        vote = create_investment_decision_vote("test", 10, 0.8)
        assert vote.vote == "强烈卖出"

    def test_global_singleton(self):
        dm1 = get_decision_maker()
        dm2 = get_decision_maker()
        assert dm1 is dm2

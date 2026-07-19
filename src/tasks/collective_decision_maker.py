# src/tasks/collective_decision_maker.py
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, field
import logging
from typing import Any
from uuid import uuid4

from .task_dataclasses import DecisionType, VotingRecord

logger = logging.getLogger(__name__)


@dataclass
class CollectiveDecisionMaker:
    """集体决策器"""

    decision_type: DecisionType = DecisionType.WEIGHTED
    minimum_confidence: float = 0.3
    history: list[dict] = field(default_factory=list)

    def cast_vote(self, voter: str, vote: str, confidence: float, reasoning: str = "") -> VotingRecord:
        """投出一票"""
        return VotingRecord(
            voter=voter,
            vote=vote,
            confidence=confidence,
            reasoning=reasoning,
        )

    def decide(self, votes: list[VotingRecord]) -> dict[str, Any]:
        """根据投票结果做出决策 — 策略分发"""
        if not votes:
            return {
                "vote_id": str(uuid4())[:8],
                "result": "持有",
                "confidence": 0.0,
                "decision_type": self.decision_type.value,
                "voter_count": 0,
                "voting_details": [],
            }

        vote_counts = Counter(v.vote for v in votes)
        weighted: dict[str, float] = {}
        for v in votes:
            weighted[v.vote] = weighted.get(v.vote, 0) + v.confidence

        strategy = self._get_decide_strategy()
        result, confidence = strategy(votes, vote_counts, weighted, self)

        decision = {
            "vote_id": str(uuid4())[:8],
            "result": result,
            "confidence": round(min(confidence, 1.0), 4),
            "decision_type": self.decision_type.value,
            "voter_count": len(votes),
            "voting_details": [{"voter": v.voter, "vote": v.vote, "confidence": v.confidence} for v in votes],
        }

        self.history.append(decision)
        return decision

    def _get_decide_strategy(self) -> Callable[..., tuple[str, float]]:
        """获取决策策略函数"""
        return _DECIDE_STRATEGIES.get(self.decision_type, _decide_weighted)

    def get_history(self) -> list[dict]:
        """获取决策历史"""
        return self.history

    def clear_history(self) -> None:
        """清空决策历史"""
        self.history.clear()


_global_decision_maker: CollectiveDecisionMaker | None = None


def get_decision_maker() -> CollectiveDecisionMaker:
    """获取全局决策器实例"""
    global _global_decision_maker
    if _global_decision_maker is None:
        _global_decision_maker = CollectiveDecisionMaker()
    return _global_decision_maker


# ── 评分 → 投票建议映射 ──────────────────────────
_VOTE_SCORE_THRESHOLDS = (
    (80, "强烈买入"),
    (60, "买入"),
    (40, "持有"),
    (20, "卖出"),
)


# ── 决策策略函数 ─────────────────────────────────

def _decide_weighted(
    votes: list[Any],
    vote_counts: Counter,
    weighted: dict[str, float],
    maker: "CollectiveDecisionMaker",
) -> tuple[str, float]:
    """加权投票策略"""
    result = max(weighted, key=weighted.get)
    total_weight = sum(v.confidence for v in votes)
    confidence = weighted[result] / total_weight if total_weight > 0 else 0.0
    return result, confidence


def _decide_majority(
    votes: list[Any],
    vote_counts: Counter,
    weighted: dict[str, float],
    maker: "CollectiveDecisionMaker",
) -> tuple[str, float]:
    """多数投票策略"""
    result = vote_counts.most_common(1)[0][0]
    confidence = vote_counts[result] / len(votes)
    return result, confidence


def _decide_unanimous(
    votes: list[Any],
    vote_counts: Counter,
    weighted: dict[str, float],
    maker: "CollectiveDecisionMaker",
) -> tuple[str, float]:
    """一致同意策略"""
    if len(vote_counts) == 1:
        return list(vote_counts.keys())[0], 1.0
    return max(weighted, key=weighted.get), 0.3


_DECIDE_STRATEGIES = {
    DecisionType.WEIGHTED: _decide_weighted,
    DecisionType.MAJORITY: _decide_majority,
    DecisionType.UNANIMOUS: _decide_unanimous,
}


def create_investment_decision_vote(voter: str, score: float, confidence: float, reasoning: str = "") -> VotingRecord:
    """根据评分创建投资决策投票 — 阈值查表"""
    for threshold, action in _VOTE_SCORE_THRESHOLDS:
        if score >= threshold:
            return VotingRecord(voter=voter, vote=action, confidence=confidence, reasoning=reasoning)
    return VotingRecord(voter=voter, vote="强烈卖出", confidence=confidence, reasoning=reasoning)


def create_vote(voter: str, vote: str, confidence: float, reasoning: str = "") -> VotingRecord:
    """兼容别名 - 供旧测试使用"""
    return VotingRecord(voter=voter, vote=vote, confidence=confidence, reasoning=reasoning)


def get_decision_statistics(self: CollectiveDecisionMaker) -> dict[str, Any]:
    """统计决策历史 - 供旧测试使用"""
    if not self.history:
        return {"total_decisions": 0, "result_distribution": {}, "average_confidence": 0.0, "recent_decisions": []}

    from collections import Counter

    results = [d["result"] for d in self.history]
    counts = Counter(results)
    avg_conf = sum(d["confidence"] for d in self.history) / len(self.history)

    return {
        "total_decisions": len(self.history),
        "result_distribution": dict(counts),
        "average_confidence": round(avg_conf, 4),
        "recent_decisions": self.history[-5:],
    }


CollectiveDecisionMaker.get_decision_statistics = get_decision_statistics
# src/tasks/task_dataclasses.py
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from uuid import uuid4


class AgentCapability(Enum):
    """Agent能力类型"""

    FUNDAMENTAL_ANALYSIS = "fundamental_analysis"
    TECHNICAL_ANALYSIS = "technical_analysis"
    QUANTITATIVE_ANALYSIS = "quantitative_analysis"
    RISK_ASSESSMENT = "risk_assessment"
    INDUSTRY_ANALYSIS = "industry_analysis"
    MARKET_ANALYSIS = "market_analysis"
    DATA_COLLECTION = "data_collection"
    REPORTING = "reporting"
    DECISION_MAKING = "decision_making"


class TaskComplexity(Enum):
    """任务复杂度"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TaskStatus(Enum):
    """任务状态"""

    PENDING = "pending"
    ASSIGNED = "assigned"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"


class DecisionType(Enum):
    """决策类型"""

    UNANIMOUS = "unanimous"
    MAJORITY = "majority"
    WEIGHTED = "weighted"
    CONSENSUS = "consensus"


@dataclass
class VotingRecord:
    """投票记录"""

    voter: str
    vote: str
    confidence: float
    reasoning: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class DynamicTask:
    """动态任务"""

    name: str
    description: str
    required_capabilities: list[AgentCapability]
    complexity: TaskComplexity = TaskComplexity.MEDIUM
    priority: int = 1
    dependencies: list[str] = field(default_factory=list)
    estimated_duration: int = 60
    id: str = field(default_factory=lambda: str(uuid4())[:8])
    assigned_agent: str | None = None
    status: TaskStatus = TaskStatus.PENDING
    started_at: str | None = None
    completed_at: str | None = None
    result: dict | None = None

    def __lt__(self, other: "DynamicTask") -> bool:
        return self.priority > other.priority

    def __gt__(self, other: "DynamicTask") -> bool:
        return self.priority > other.priority


@dataclass
class AgentProfile:
    """Agent 画像"""

    name: str
    capabilities: list[AgentCapability]
    capability_scores: dict[AgentCapability, float] = field(default_factory=dict)
    max_workload: float = 100.0
    current_workload: float = 0.0
    availability: bool = True
    success_rate: float = 0.8
    task_history: list[str] = field(default_factory=list)

    def calculate_fitness(self, required_capabilities: list[AgentCapability], complexity: TaskComplexity) -> float:
        """计算Agent与任务的匹配度"""
        if not all(cap in self.capabilities for cap in required_capabilities):
            return 0.0
        score = sum(self.capability_scores.get(cap, 0.5) for cap in required_capabilities)
        score /= max(len(required_capabilities), 1)
        complexity_multiplier = {
            TaskComplexity.LOW: 1.0,
            TaskComplexity.MEDIUM: 0.9,
            TaskComplexity.HIGH: 0.75,
            TaskComplexity.CRITICAL: 0.6,
        }
        score *= complexity_multiplier.get(complexity, 0.9)
        if self.current_workload >= self.max_workload:
            return 0.0
        workload_factor = 1.0 - (self.current_workload / self.max_workload)
        score *= max(workload_factor, 0.1)
        return score
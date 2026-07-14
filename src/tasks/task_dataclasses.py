# src/tasks/task_dataclasses.py
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional
from uuid import uuid4
from datetime import datetime


class AgentCapability(Enum):
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
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TaskStatus(Enum):
    PENDING = "pending"
    ASSIGNED = "assigned"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"


class DecisionType(Enum):
    UNANIMOUS = "unanimous"
    MAJORITY = "majority"
    WEIGHTED = "weighted"
    CONSENSUS = "consensus"


@dataclass
class VotingRecord:
    voter: str
    vote: str
    confidence: float
    reasoning: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class DynamicTask:
    name: str
    description: str
    required_capabilities: List[AgentCapability]
    complexity: TaskComplexity = TaskComplexity.MEDIUM
    priority: int = 1
    dependencies: List[str] = field(default_factory=list)
    estimated_duration: int = 60
    id: str = field(default_factory=lambda: str(uuid4())[:8])
    assigned_agent: Optional[str] = None
    status: TaskStatus = TaskStatus.PENDING
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    result: Optional[Dict] = None

    def __lt__(self, other):
        return self.priority > other.priority


@dataclass
class AgentProfile:
    name: str
    capabilities: List[AgentCapability]
    capability_scores: Dict[AgentCapability, float] = field(default_factory=dict)
    max_workload: float = 100.0
    current_workload: float = 0.0
    availability: bool = True
    success_rate: float = 0.8
    task_history: List[str] = field(default_factory=list)

    def calculate_fitness(self, required_capabilities: List[AgentCapability],
                          complexity: TaskComplexity) -> float:
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
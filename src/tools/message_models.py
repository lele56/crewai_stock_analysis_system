# src/tools/message_models.py
"""智能体消息模型 - 消息类型、优先级、消息体和任务委托的数据结构"""
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import uuid


class MessageType(Enum):
    """消息类型枚举"""
    TASK_DELEGATION = "task_delegation"
    INFORMATION_REQUEST = "information_request"
    INFORMATION_SHARE = "information_share"
    COLLABORATION_INVITE = "collaboration_invite"
    STATUS_UPDATE = "status_update"
    ERROR_REPORT = "error_report"
    DECISION_REQUEST = "decision_request"
    FEEDBACK = "feedback"


class MessagePriority(Enum):
    """消息优先级"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4


@dataclass
class Message:
    """智能体间通信消息"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    sender: str = ""
    receiver: str = ""
    message_type: MessageType = MessageType.INFORMATION_SHARE
    priority: MessagePriority = MessagePriority.NORMAL
    subject: str = ""
    content: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    requires_response: bool = False
    response_deadline: Optional[str] = None
    attachments: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'id': self.id, 'sender': self.sender, 'receiver': self.receiver,
            'message_type': self.message_type.value, 'priority': self.priority.value,
            'subject': self.subject, 'content': self.content, 'timestamp': self.timestamp,
            'requires_response': self.requires_response, 'response_deadline': self.response_deadline,
            'attachments': self.attachments, 'metadata': self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Message':
        """从字典创建消息"""
        return cls(
            id=data['id'], sender=data['sender'], receiver=data['receiver'],
            message_type=MessageType(data['message_type']),
            priority=MessagePriority(data['priority']),
            subject=data['subject'], content=data['content'],
            timestamp=data['timestamp'], requires_response=data['requires_response'],
            response_deadline=data.get('response_deadline'),
            attachments=data.get('attachments', []),
            metadata=data.get('metadata', {})
        )


@dataclass
class TaskDelegation:
    """任务委托记录"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    delegator: str = ""
    delegatee: str = ""
    original_task: str = ""
    delegated_task: str = ""
    reason: str = ""
    deadline: Optional[str] = None
    status: str = "pending"
    progress: float = 0.0
    feedback: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    updated_at: str = field(default_factory=lambda: datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
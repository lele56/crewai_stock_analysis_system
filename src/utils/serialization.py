# src/utils/serialization.py
"""JSON 序列化工具——递归转换不可序列化对象为字符串"""

import json
from typing import Any


def make_serializable(obj: Any) -> Any:
    """递归转换不可序列化对象为字符串"""
    if isinstance(obj, dict):
        return {k: make_serializable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [make_serializable(v) for v in obj]
    if hasattr(obj, "raw"):
        return make_serializable(obj.raw)
    try:
        json.dumps(obj)
        return obj
    except (TypeError, ValueError):
        return str(obj)
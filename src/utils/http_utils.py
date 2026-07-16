# src/utils/http_utils.py
"""HTTP工具模块
提供增强的HTTP请求功能，包含重试机制、连接错误处理等
"""

from collections.abc import Callable
import logging
import random
import time
from typing import Any, Never

import httpx
from httpx import ConnectError, ReadError, RemoteProtocolError

from src.config import Config

logger = logging.getLogger(__name__)


class EnhancedHTTPClient:
    """增强型HTTP客户端，支持重试、连接错误处理等高级功能"""

    def __init__(
        self,
        max_retries: int = 3,
        retry_backoff_factor: float = 0.5,
        retry_statuses: tuple = (429, 500, 502, 503, 504),
        timeout: int = 30,
        headers: dict[str, str] | None = None,
        base_url: str | None = None,
        **kwargs: Any,
    ) -> None:
        """初始化增强型HTTP客户端

        Args:
            max_retries: 最大重试次数
            retry_backoff_factor: 退避因子，用于指数退避算法
            retry_statuses: 需要重试的HTTP状态码
            timeout: 请求超时时间（秒）
            headers: 默认请求头
            base_url: 基础URL
            **kwargs: 其他传递给httpx.Client的参数
        """
        self.max_retries = max_retries
        self.retry_backoff_factor = retry_backoff_factor
        self.retry_statuses = retry_statuses
        self.timeout = timeout
        self.base_url = base_url

        # 创建基础客户端配置
        client_kwargs = {"timeout": timeout, "headers": headers or {}, **kwargs}

        if base_url:
            client_kwargs["base_url"] = base_url

        # 创建HTTP客户端
        self.client = httpx.Client(**client_kwargs)

    def _calculate_backoff(self, attempt: int) -> float:
        """计算重试之间的退避时间"""
        # 基础退避时间 = 退避因子 * (2 ** 尝试次数)
        base_backoff = self.retry_backoff_factor * (2**attempt)
        # 添加随机抖动，避免多个请求同时重试
        jitter = random.uniform(0.5, 1.5)
        return base_backoff * jitter

    def request(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        """发送HTTP请求，支持自动重试

        Args:
            method: HTTP方法（GET, POST等）
            url: 请求URL
            **kwargs: 其他传递给httpx.Client.request的参数

        Returns:
            httpx.Response: HTTP响应

        Raises:
            httpx.HTTPError: 如果请求最终失败
        """
        # 确保超时设置
        if "timeout" not in kwargs:
            kwargs["timeout"] = self.timeout

        last_exception = None

        for attempt in range(self.max_retries + 1):  # +1 因为第一次尝试不算重试
            try:
                response = self.client.request(method, url, **kwargs)

                # 检查是否需要重试
                if response.status_code in self.retry_statuses and attempt < self.max_retries:
                    wait_time = self._calculate_backoff(attempt)
                    logger.warning(
                        f"请求失败 (状态码: {response.status_code})，"
                        f"{wait_time:.2f}秒后重试 ({attempt + 1}/{self.max_retries})"
                    )
                    time.sleep(wait_time)
                    continue

                # 对于其他错误状态码，直接抛出异常
                response.raise_for_status()

                # 请求成功
                return response

            except (ConnectError, ReadError, RemoteProtocolError) as e:
                # 处理连接相关的错误，特别是WinError 10054（连接被重置）
                last_exception = e
                error_msg = str(e)

                # 识别WinError 10054错误
                if "10054" in error_msg or "远程主机强迫关闭了一个现有的连接" in error_msg:
                    error_type = "连接被重置"
                elif "timed out" in error_msg:
                    error_type = "连接超时"
                else:
                    error_type = "连接错误"

                if attempt < self.max_retries:
                    wait_time = self._calculate_backoff(attempt)
                    logger.warning(
                        f"{error_type}: {error_msg}，{wait_time:.2f}秒后重试 ({attempt + 1}/{self.max_retries})"
                    )
                    time.sleep(wait_time)
                else:
                    logger.error(f"{error_type}，已达到最大重试次数: {error_msg}")
                    raise

            except Exception as e:
                # 处理其他异常
                last_exception = e
                if attempt < self.max_retries:
                    wait_time = self._calculate_backoff(attempt)
                    logger.warning(f"请求异常: {str(e)}，{wait_time:.2f}秒后重试 ({attempt + 1}/{self.max_retries})")
                    time.sleep(wait_time)
                else:
                    logger.error(f"请求异常，已达到最大重试次数: {str(e)}")
                    raise

        # 这一行理论上不会执行到，但为了代码完整性保留
        if last_exception:
            raise last_exception
        return None

    def get(self, url: str, **kwargs: Any) -> httpx.Response:
        """发送GET请求"""
        return self.request("GET", url, **kwargs)

    def post(self, url: str, **kwargs: Any) -> httpx.Response:
        """发送POST请求"""
        return self.request("POST", url, **kwargs)

    def put(self, url: str, **kwargs: Any) -> httpx.Response:
        """发送PUT请求"""
        return self.request("PUT", url, **kwargs)

    def delete(self, url: str, **kwargs: Any) -> httpx.Response:
        """发送DELETE请求"""
        return self.request("DELETE", url, **kwargs)

    def close(self) -> None:
        """关闭HTTP客户端"""
        self.client.close()

    def __enter__(self) -> "EnhancedHTTPClient":
        """支持上下文管理器协议"""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object | None,
    ) -> None:
        """支持上下文管理器协议"""
        self.close()


def create_openai_client() -> EnhancedHTTPClient:
    """创建配置了OpenAI API的增强型HTTP客户端

    Returns:
        EnhancedHTTPClient: 配置好的HTTP客户端
    """
    # 从环境变量获取OpenAI配置
    api_key = Config.LLM_API_KEY
    base_url = Config.LLM_BASE_URL or "https://api.openai.com/v1"

    if not api_key:
        logger.error("未设置OPENAI_API_KEY环境变量")
        raise ValueError("未设置OPENAI_API_KEY环境变量")

    # 设置请求头
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    # 创建并返回增强型HTTP客户端
    return EnhancedHTTPClient(
        max_retries=3,
        retry_backoff_factor=1.0,
        retry_statuses=(429, 500, 502, 503, 504),
        timeout=60,  # OpenAI API可能需要较长时间
        headers=headers,
        base_url=base_url,
        # 增加连接池大小以支持并发请求
        limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
    )


def with_retry(max_retries: int = 3, backoff_factor: float = 0.5) -> Callable:
    """为函数添加重试装饰器

    Args:
        max_retries: 最大重试次数
        backoff_factor: 退避因子

    Returns:
        Callable: 装饰器函数
    """

    def decorator(func: Callable) -> Callable:
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e

                    # 识别是否为连接错误
                    is_connection_error = isinstance(e, (ConnectError, ReadError, RemoteProtocolError)) or (
                        hasattr(e, "args") and e.args and "10054" in str(e.args[0])
                    )

                    if is_connection_error and attempt < max_retries:
                        wait_time = backoff_factor * (2**attempt) * random.uniform(0.5, 1.5)
                        logger.warning(
                            f"连接错误: {str(e)}，在 {wait_time:.2f}秒后重试"
                            f" ({attempt + 1}/{max_retries}) - 函数: {func.__name__}"
                        )
                        time.sleep(wait_time)
                    else:
                        # 如果不是连接错误或已达到最大重试次数，抛出异常
                        logger.error(f"函数执行失败: {str(e)} - 函数: {func.__name__}")
                        raise

            # 这一行理论上不会执行到，但为了代码完整性保留
            if last_exception:
                raise last_exception
            return None

        # 保留原函数的元数据
        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        wrapper.__module__ = func.__module__

        return wrapper

    return decorator


# 使用示例
if __name__ == "__main__":
    # 独立运行时配置日志
    # 示例1: 使用增强型HTTP客户端
    with EnhancedHTTPClient(max_retries=3) as client:
        try:
            response = client.get("https://httpbin.org/status/503")
            logger.info(f"响应状态码: {response.status_code}")
        except Exception as e:
            logger.error(f"请求失败: {e}")

    @with_retry
    def example_function() -> Never:
        """示例函数 - 模拟连接错误"""
        raise ConnectError("模拟连接错误")

    try:
        example_function()
    except Exception as e:
        logger.error(f"装饰器测试 - 最终失败: {e}")

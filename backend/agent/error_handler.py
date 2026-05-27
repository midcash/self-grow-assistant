"""错误处理器 — 故障分类 + 断路器 + 优雅降级

参考 2026 生产级实践:
- 错误分类: ModelError / NetworkError / PluginError / InternalError
- 断路器: 连续失败 → 暂时摘除
- 降级策略: 切换备选方案或跳过
"""

import asyncio
import logging
import time
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class ErrorType(str, Enum):
    MODEL = "model"            # 模型返回异常
    NETWORK = "network"        # 网络超时/不可达
    PLUGIN = "plugin"          # 插件内部错误
    INTERNAL = "internal"      # 系统内部错误
    CONFIG = "config"          # 配置错误


class FallbackAction(str, Enum):
    RETRY = "retry"            # 重试
    RETRY_WITH_BACKOFF = "retry_backoff"  # 指数退避重试
    SWITCH_FALLBACK = "switch_fallback"   # 切换备选方案
    SKIP = "skip"              # 跳过
    ABORT = "abort"            # 中止


class CircuitBreaker:
    """断路器"""

    def __init__(self, name: str, failure_threshold: int = 3,
                 recovery_timeout: float = 60.0):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = 0.0
        self.last_success_time = 0.0
        self.state = "closed"  # closed / open / half_open

    def success(self) -> None:
        self.failure_count = 0
        self.last_success_time = time.time()
        self.state = "closed"

    def failure(self) -> None:
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = "open"
            logger.warning(f"Circuit breaker '{self.name}' OPEN ({self.failure_count} failures)")

    def allow_request(self) -> bool:
        if self.state == "closed":
            return True
        if self.state == "open":
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "half_open"
                logger.info(f"Circuit breaker '{self.name}' -> half_open")
                return True
            return False
        # half_open: allow one probe
        return True


class ErrorHandler:
    """错误处理器

    特性:
    - 错误分类 (ModelError / NetworkError / PluginError / InternalError)
    - 断路器保护
    - 指数退避重试
    - 降级策略
    """

    def __init__(self):
        self._breakers: dict[str, CircuitBreaker] = {}
        self._fallbacks: dict[str, str] = {}  # capability -> fallback capability

    # === 断路器管理 ===

    def get_breaker(self, name: str) -> CircuitBreaker:
        if name not in self._breakers:
            self._breakers[name] = CircuitBreaker(name=name)
        return self._breakers[name]

    def register_fallback(self, capability: str, fallback_capability: str) -> None:
        """注册降级链路"""
        self._fallbacks[capability] = fallback_capability

    # === 错误分类 ===

    def classify(self, error: Exception) -> ErrorType:
        """自动分类错误类型"""
        name = type(error).__name__.lower()
        msg = str(error).lower()

        if any(k in name for k in ("timeout", "connection", "network", "httpx")):
            return ErrorType.NETWORK
        if any(k in msg for k in ("api", "model", "rate limit", "token")):
            return ErrorType.MODEL
        if any(k in name for k in ("attribute", "type", "value", "key")):
            return ErrorType.CONFIG
        if "plugin" in name:
            return ErrorType.PLUGIN
        return ErrorType.INTERNAL

    # === 处理策略 ===

    def get_action(self, error_type: ErrorType, attempt: int = 0) -> FallbackAction:
        """根据错误类型和重试次数返回处理策略"""
        if error_type == ErrorType.NETWORK:
            if attempt < 3:
                return FallbackAction.RETRY_WITH_BACKOFF
            return FallbackAction.SWITCH_FALLBACK
        if error_type == ErrorType.MODEL:
            if attempt < 2:
                return FallbackAction.RETRY
            return FallbackAction.SWITCH_FALLBACK
        if error_type == ErrorType.PLUGIN:
            return FallbackAction.SKIP
        if error_type == ErrorType.CONFIG:
            return FallbackAction.ABORT
        return FallbackAction.RETRY

    # === 重试执行 ===

    async def execute_with_retry(self, name: str, coro_factory,
                                  max_retries: int = 3,
                                  base_delay: float = 1.0) -> Any:
        """带断路器 + 指数退避的执行器

        Args:
            name: 操作名称 (用于断路器)
            coro_factory: 异步函数工厂 (每次重试创建新的)
            max_retries: 最大重试次数
            base_delay: 基础延迟秒数
        """
        breaker = self.get_breaker(name)

        for attempt in range(max_retries):
            if not breaker.allow_request():
                logger.error(f"Circuit breaker '{name}' open, request blocked")
                raise RuntimeError(f"Circuit breaker '{name}' is open")

            try:
                result = await coro_factory()
                breaker.success()
                return result
            except Exception as e:
                breaker.failure()
                error_type = self.classify(e)
                action = self.get_action(error_type, attempt)

                logger.warning(
                    f"Attempt {attempt + 1}/{max_retries} for '{name}' failed: "
                    f"{error_type.value} - {e}. Action: {action.value}"
                )

                if action == FallbackAction.ABORT:
                    raise
                if action == FallbackAction.SKIP:
                    return None
                if action == FallbackAction.SWITCH_FALLBACK:
                    fallback = self._fallbacks.get(name)
                    if fallback:
                        logger.info(f"Switching to fallback '{fallback}' for '{name}'")
                        raise FallbackTriggeredError(name, fallback)
                    raise
                if action == FallbackAction.RETRY_WITH_BACKOFF:
                    delay = base_delay * (2 ** attempt)
                    await asyncio.sleep(delay)
                # RETRY: immediate retry

        logger.error(f"All {max_retries} retries exhausted for '{name}'")
        raise RuntimeError(f"Operation '{name}' failed after {max_retries} attempts")


class FallbackTriggeredError(Exception):
    """触发降级链路"""
    def __init__(self, source: str, fallback: str):
        self.source = source
        self.fallback = fallback
        super().__init__(f"Falling back from '{source}' to '{fallback}'")

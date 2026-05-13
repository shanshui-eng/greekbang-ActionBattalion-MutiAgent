"""统一 LLM 调用客户端.

支持 DeepSeek / Qwen / OpenAI 三种模型提供商，通过环境变量切换。
使用 httpx 直接调用 OpenAI 兼容 API，不依赖 openai SDK。

用法:
    from pipeline.model_client import quick_chat

    reply = quick_chat("什么是 RAG？")
    print(reply)

环境变量:
    LLM_PROVIDER   — 提供商: deepseek (默认) / qwen / openai
    LLM_API_KEY    — API 密钥 (也可用 {PROVIDER}_API_KEY)
    LLM_MODEL      — 模型名称 (可选，使用提供商默认模型)
"""

import asyncio
import logging
import os
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

# ── 提供商配置 ────────────────────────────────────

PROVIDER_CONFIGS = {
    "deepseek": {
        "base_url": "https://api.deepseek.com/v1",
        "default_model": "deepseek-chat",
        "env_key": "DEEPSEEK_API_KEY",
        "pricing_input": 0.27,
        "pricing_output": 1.10,
    },
    "qwen": {
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "default_model": "qwen-plus",
        "env_key": "QWEN_API_KEY",
        "pricing_input": 0.50,
        "pricing_output": 2.00,
    },
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "default_model": "gpt-4o",
        "env_key": "OPENAI_API_KEY",
        "pricing_input": 2.50,
        "pricing_output": 10.00,
    },
}

# ── 数据结构 ──────────────────────────────────────


@dataclass
class Usage:
    """Token 用量统计.

    Attributes:
        prompt_tokens: 输入消耗的 token 数.
        completion_tokens: 输出生成的 token 数.
        total_tokens: 总 token 数.
    """

    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


@dataclass
class LLMResponse:
    """统一 LLM 响应.

    Attributes:
        content: 模型返回的文本内容.
        usage: Token 用量统计.
        model: 实际使用的模型名称.
        finish_reason: 结束原因 (stop / length / content_filter).
    """

    content: str
    usage: Usage
    model: str
    finish_reason: str = "stop"


# ── 抽象基类 ──────────────────────────────────────


class LLMProvider(ABC):
    """LLM 提供商的抽象接口."""

    @abstractmethod
    def chat(self, messages: list[dict[str, str]], **kwargs) -> LLMResponse:
        """发送同步聊天请求.

        Args:
            messages: 消息列表，每条含 role 和 content.
            **kwargs: 额外参数 (temperature, max_tokens 等).

        Returns:
            LLMResponse 包含回复内容和用量统计.
        """
        ...

    @abstractmethod
    async def achat(self, messages: list[dict[str, str]], **kwargs) -> LLMResponse:
        """发送异步聊天请求.

        Args:
            messages: 消息列表.
            **kwargs: 额外参数.

        Returns:
            LLMResponse 包含回复内容和用量统计.
        """
        ...


# ── OpenAI 兼容实现 ───────────────────────────────


class OpenAICompatibleProvider(LLMProvider):
    """OpenAI 兼容 API 的通用实现.

    适用于任何兼容 OpenAI chat/completions 端点的服务，
    包括 DeepSeek、Qwen (DashScope)、OpenAI 自身。

    Attributes:
        base_url: API 基础 URL.
        api_key: 认证密钥.
        model: 默认模型名称.
        timeout: HTTP 请求超时秒数.
    """

    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        timeout: float = 60.0,
    ) -> None:
        """初始化提供商.

        Args:
            base_url: API 基础 URL (如 https://api.deepseek.com/v1).
            api_key: 认证密钥.
            model: 默认模型名称.
            timeout: 请求超时秒数.
        """
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout = timeout

    def _build_payload(
        self, messages: list[dict[str, str]], **kwargs
    ) -> dict:
        """构建请求体."""
        payload: dict = {
            "model": kwargs.pop("model", self.model),
            "messages": messages,
        }
        for key in ("temperature", "max_tokens", "top_p", "stream", "stop"):
            if key in kwargs:
                payload[key] = kwargs.pop(key)
        payload.update(kwargs)
        return payload

    def _parse_response(self, data: dict, model: str) -> LLMResponse:
        """解析 API 响应为 LLMResponse."""
        choice = data["choices"][0]
        usage_raw = data.get("usage", {})
        usage = Usage(
            prompt_tokens=usage_raw.get("prompt_tokens", 0),
            completion_tokens=usage_raw.get("completion_tokens", 0),
            total_tokens=usage_raw.get("total_tokens", 0),
        )
        return LLMResponse(
            content=choice["message"]["content"],
            usage=usage,
            model=data.get("model", model),
            finish_reason=choice.get("finish_reason", "stop"),
        )

    def chat(self, messages: list[dict[str, str]], **kwargs) -> LLMResponse:
        """发送同步聊天请求.

        Args:
            messages: 消息列表.
            **kwargs: 额外参数传递给 API.

        Returns:
            LLMResponse 包含回复内容和用量统计.

        Raises:
            httpx.HTTPError: HTTP 层错误.
        """
        payload = self._build_payload(messages, **kwargs)
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        logger.debug("POST %s model=%s", url, payload["model"])
        response = httpx.post(
            url,
            json=payload,
            headers=headers,
            timeout=self.timeout,
        )
        response.raise_for_status()
        return self._parse_response(response.json(), payload["model"])

    async def achat(
        self, messages: list[dict[str, str]], **kwargs
    ) -> LLMResponse:
        """发送异步聊天请求.

        Args:
            messages: 消息列表.
            **kwargs: 额外参数.

        Returns:
            LLMResponse 包含回复内容和用量统计.

        Raises:
            httpx.HTTPError: HTTP 层错误.
        """
        payload = self._build_payload(messages, **kwargs)
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        logger.debug("POST %s model=%s", url, payload["model"])
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                url,
                json=payload,
                headers=headers,
            )
        response.raise_for_status()
        return self._parse_response(response.json(), payload["model"])


# ── Token 估算 ────────────────────────────────────


def estimate_tokens(text: str) -> int:
    """粗略估算文本的 token 数量.

    英文约 4 字符/token，CJK 字符约 1.5 字符/token。
    不依赖 tiktoken，适用于成本预估场景。

    Args:
        text: 输入文本.

    Returns:
        估算的 token 数量.
    """
    if not text:
        return 0
    cjk = 0
    latin = 0
    for ch in text:
        if "一" <= ch <= "鿿" or "぀" <= ch <= "ゟ":
            cjk += 1
        else:
            latin += 1
    return int(cjk / 1.5 + latin / 4.0)


def calculate_cost(
    prompt_tokens: int,
    completion_tokens: int,
    provider: str,
) -> float:
    """计算 LLM 调用的美元成本.

    Args:
        prompt_tokens: 输入 token 数.
        completion_tokens: 输出 token 数.
        provider: 提供商名称 (deepseek / qwen / openai).

    Returns:
        USD 成本.
    """
    cfg = PROVIDER_CONFIGS.get(provider, PROVIDER_CONFIGS["deepseek"])
    input_cost = (prompt_tokens / 1_000_000) * cfg["pricing_input"]
    output_cost = (completion_tokens / 1_000_000) * cfg["pricing_output"]
    return round(input_cost + output_cost, 6)


# ── 带重试的调用 ──────────────────────────────────

RETRYABLE_STATUSES = {429, 500, 502, 503, 504}


def chat_with_retry(
    provider: LLMProvider,
    messages: list[dict[str, str]],
    retries: int = 3,
    backoff_base: float = 1.0,
    **kwargs,
) -> LLMResponse:
    """带指数退避重试的聊天请求.

    在以下情况重试: 网络错误、超时、5xx 状态码、429 限流。
    4xx 错误（除 429）不重试，直接抛出。

    Args:
        provider: LLMProvider 实例.
        messages: 消息列表.
        retries: 最大重试次数 (不含首次).
        backoff_base: 退避基数秒数，第 n 次重试延迟 base * 2^n.
        **kwargs: 传递给 provider.chat().

    Returns:
        LLMResponse 包含回复内容和用量统计.

    Raises:
        httpx.HTTPStatusError: 不可重试的 HTTP 错误.
        httpx.HTTPError: 重试耗尽后的网络错误.
    """
    last_exc: Exception | None = None
    for attempt in range(retries + 1):
        try:
            return provider.chat(messages, **kwargs)
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code not in RETRYABLE_STATUSES:
                raise
            last_exc = exc
            logger.warning(
                "HTTP %d on attempt %d/%d",
                exc.response.status_code,
                attempt + 1,
                retries + 1,
            )
        except (httpx.ConnectError, httpx.ReadError, httpx.TimeoutException) as exc:
            last_exc = exc
            logger.warning(
                "Network error on attempt %d/%d: %s",
                attempt + 1,
                retries + 1,
                exc,
            )
        if attempt < retries:
            delay = backoff_base * (2 ** attempt)
            logger.info("Retrying in %.1fs...", delay)
            time.sleep(delay)
    raise last_exc  # type: ignore[misc]


# ── 工厂函数 ──────────────────────────────────────


def get_provider(
    provider_name: str | None = None,
    api_key: str | None = None,
    model: str | None = None,
) -> OpenAICompatibleProvider:
    """从环境变量创建 LLM 提供商实例.

    优先级: 参数 > 环境变量 > 默认值.

    Args:
        provider_name: 提供商名称，默认取 LLM_PROVIDER 环境变量或 "deepseek".
        api_key: API 密钥，默认取 {PROVIDER}_API_KEY 或 LLM_API_KEY.
        model: 模型名，默认取 LLM_MODEL 环境变量或提供商的默认模型.

    Returns:
        OpenAICompatibleProvider 实例.

    Raises:
        ValueError: 提供商名称未知或 API 密钥缺失.
    """
    name = provider_name or os.getenv("LLM_PROVIDER", "deepseek").lower()
    if name not in PROVIDER_CONFIGS:
        raise ValueError(
            f"未知提供商 '{name}'，可选: {list(PROVIDER_CONFIGS)}"
        )
    cfg = PROVIDER_CONFIGS[name]
    key = api_key or os.getenv("LLM_API_KEY") or os.getenv(cfg["env_key"])
    if not key:
        raise ValueError(
            f"未找到 API 密钥，请设置 LLM_API_KEY 或 {cfg['env_key']} 环境变量"
        )
    selected_model = model or os.getenv("LLM_MODEL") or cfg["default_model"]
    return OpenAICompatibleProvider(
        base_url=cfg["base_url"],
        api_key=key,
        model=selected_model,
    )


# ── 便捷函数 ──────────────────────────────────────


def quick_chat(
    prompt: str,
    system: str | None = None,
    provider: str | None = None,
    **kwargs,
) -> str:
    """一句话调用 LLM，返回回复文本.

    Args:
        prompt: 用户提示词.
        system: 系统提示词 (可选).
        provider: 提供商名称 (可选，默认取环境变量).
        **kwargs: 额外参数 (temperature, max_tokens 等).

    Returns:
        模型回复的文本内容.

    Example:
        >>> reply = quick_chat("用一句话解释 RAG")
        >>> print(reply)
    """
    messages: list[dict[str, str]] = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    llm = get_provider(provider_name=provider)
    response = chat_with_retry(llm, messages, **kwargs)
    cost = calculate_cost(
        response.usage.prompt_tokens,
        response.usage.completion_tokens,
        provider or os.getenv("LLM_PROVIDER", "deepseek"),
    )
    logger.info(
        "tokens: %d in + %d out = %d total, cost: $%.6f",
        response.usage.prompt_tokens,
        response.usage.completion_tokens,
        response.usage.total_tokens,
        cost,
    )
    return response.content


# ── 自测 ──────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    print("=" * 50)
    print("  model_client 自测")
    print("=" * 50)

    # 1. 检查环境变量
    provider_name = os.getenv("LLM_PROVIDER", "deepseek")
    api_key = os.getenv("LLM_API_KEY") or os.getenv(
        PROVIDER_CONFIGS.get(provider_name, {}).get("env_key", "")
    )
    if not api_key:
        print(f"[SKIP] 未设置 API 密钥，跳过真实调用测试")
        print(f"  请设置 LLM_API_KEY 或 {PROVIDER_CONFIGS.get(provider_name, {}).get('env_key', '???')}")
    else:
        # 2. 创建 provider
        llm = get_provider()
        print(f"  提供商: {provider_name}")
        print(f"  模型:   {llm.model}")
        print()

        # 3. 同步调用
        print("  [1/3] 同步 chat() ...")
        resp = llm.chat([{"role": "user", "content": "你好，请用一句话介绍你自己"}])
        print(f"  reply: {resp.content}")
        print(f"  usage: {resp.usage}")
        cost = calculate_cost(
            resp.usage.prompt_tokens,
            resp.usage.completion_tokens,
            provider_name,
        )
        print(f"  cost:  ${cost:.6f}")
        print()

        # 4. 带重试调用
        print("  [2/3] chat_with_retry() ...")
        resp2 = chat_with_retry(
            llm,
            [{"role": "user", "content": "什么是大语言模型？请用一句话回答"}],
            temperature=0.3,
        )
        print(f"  reply: {resp2.content}")
        print(f"  retry: model={resp2.model}, finish={resp2.finish_reason}")
        print()

        # 5. 便捷调用
        print("  [3/3] quick_chat() ...")
        reply3 = quick_chat("用一句话解释什么是 Agent")
        print(f"  reply: {reply3}")
        print()

    # 6. Token 估算 (不依赖 API)
    print("  Token 估算测试:")
    samples = [
        ("Hello, how are you?", "纯英文"),
        ("什么是大语言模型？请详细解释一下。", "中文"),
        ("AI Agent 是一种能够自主感知环境并执行动作的智能体。LLM 作为 Agent 的大脑。", "混合"),
    ]
    for text, label in samples:
        tokens = estimate_tokens(text)
        print(f"  [{label}] {tokens:4d} tokens ← {len(text)} chars: {text[:40]}...")

    print()

    # 7. 成本对比
    print("  成本对比 (100K input + 10K output tokens):")
    for name in ("deepseek", "qwen", "openai"):
        cost = calculate_cost(100_000, 10_000, name)
        cfg = PROVIDER_CONFIGS[name]
        print(f"  {name:10s}  ${cost:.4f}  (in=${cfg['pricing_input']}/M, out=${cfg['pricing_output']}/M)")

    print()
    print("=" * 50)
    print("  自测完成")
    print("=" * 50)

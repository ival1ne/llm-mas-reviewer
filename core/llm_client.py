import os
from typing import Any

from dotenv import load_dotenv

load_dotenv()


def _build_langchain_llm(**kwargs: Any):
    try:
        from langchain_openai import ChatOpenAI
    except ImportError as exc:
        raise ImportError(
            "LangChain dependencies are missing. Install langchain-openai first."
        ) from exc

    return ChatOpenAI(
        api_key=os.getenv("OPENAI_API_KEY", "lm-studio"),
        base_url=os.getenv("OPENAI_BASE_URL"),
        model=os.getenv("OPENAI_MODEL", "qwen2.5-coder"),
        temperature=kwargs.get("temperature", 0.2),
        max_tokens=kwargs.get("max_tokens", 2000),
        timeout=kwargs.get("timeout", 120),
        max_retries=kwargs.get("max_retries", 1),
    )


def call_llm(
    prompt: str,
    *,
    max_tokens: int = 2000,
    temperature: float = 0.2,
    timeout: int = 120,
) -> str:
    llm = _build_langchain_llm(
        max_tokens=max_tokens,
        temperature=temperature,
        timeout=timeout,
    )
    response = llm.invoke(prompt)
    return response.content if isinstance(response.content, str) else str(response.content)

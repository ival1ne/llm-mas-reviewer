import os

from dotenv import load_dotenv

load_dotenv()


def _build_langchain_llm():
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
        temperature=0.2,
        max_tokens=2000,
    )


def call_llm(prompt: str) -> str:
    llm = _build_langchain_llm()
    response = llm.invoke(prompt)
    return response.content if isinstance(response.content, str) else str(response.content)

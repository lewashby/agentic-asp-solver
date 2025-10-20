from langchain_openai import ChatOpenAI
from asper.config import ASPSystemConfig


def build_llm(config: ASPSystemConfig) -> ChatOpenAI:
    """Construct and return a chat LLM instance based on the ASP system config.

    Minimal error mapping: raise RuntimeError with code prefix for simple handling.
    Codes: AUTH, MODEL_NOT_FOUND, TEMPORARY, UNKNOWN.
    """
    try:
        return ChatOpenAI(
            model=config.model_name,
            temperature=config.temperature,
            base_url=config.base_url,
            api_key=config.api_key,
        )
    except Exception as e:
        message = str(e)
        lowered = message.lower()
        if any(x in lowered for x in ["unauthorized", "invalid api key", "401", "403"]):
            code = "AUTH"
        else:
            code = "UNKNOWN"
        raise RuntimeError(f"{code}: {message}")



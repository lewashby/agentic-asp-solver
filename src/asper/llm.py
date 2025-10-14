from langchain_openai import ChatOpenAI

from asper.config import ASPSystemConfig


def build_llm(config: ASPSystemConfig):
    """Construct and return a chat LLM instance based on the ASP system config.

    For now, this uses ChatOpenAI directly. Future providers can be routed here.
    """
    return ChatOpenAI(
        model=config.model_name,
        temperature=config.temperature,
        base_url=config.base_url,
        api_key=config.api_key,
    )



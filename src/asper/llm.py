"""LLM initialization for ASP solver."""

from langchain_openai import ChatOpenAI

from asper.config import ASPSystemConfig


def build_llm(config: ASPSystemConfig) -> ChatOpenAI:
    """Construct and return a chat LLM instance based on the ASP system config.
    
    Args:
        config: System configuration with LLM settings
        
    Returns:
        Initialized ChatOpenAI instance
    """
    return ChatOpenAI(
            model="config.model_name",
            temperature=config.temperature,
            base_url=config.base_url,
            api_key=config.api_key,
        )

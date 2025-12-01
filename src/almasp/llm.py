"""LLM initialization for Agentic ASP solver."""

from langchain_openai import ChatOpenAI
from langchain_ollama import ChatOllama
from pydantic import SecretStr

from almasp.config import ASPSystemConfig
from almasp.utils import get_logger

logger = get_logger()

def build_llm(config: ASPSystemConfig) -> ChatOpenAI | ChatOllama:
    """Construct and return a chat LLM instance based on the ASP system config.

    Args:
        config: System configuration with LLM settings

    Returns:
        Configured ChatOpenAI or ChatOllama instance with reasoning support
    """

    # Build LLM based on specified type
    # ChatOllama
    if config.provider == "ollama":
        logger.info(
            f"Initializing ChatOllama with model={config.model_name}, "
            f"temperature={config.temperature}, reasoning={config.reasoning}"
        )
        return ChatOllama(
            model=config.model_name,
            temperature=config.temperature,
            reasoning=config.reasoning,
        )
    
    # ChatOpenAI
    else:
        if config.reasoning not in (False, None, "false"):
            logger.warning(
                f"Reasoning parameter ({config.reasoning}) is set but not used "
                "for ChatOpenAI in this implementation. Ignoring reasoning setting."
            )
        
        logger.info(
            f"Initializing ChatOpenAI with model={config.model_name}, "
            f"temperature={config.temperature}, base_url={config.base_url}"
        )
        llm = ChatOpenAI(
            model=config.model_name,
            temperature=config.temperature,
            base_url=config.base_url,
            api_key=SecretStr(config.api_key),
        )
        # if config.reasoning:
        #     effort = config.reasoning if isinstance(config.reasoning, str) else "medium"
        #     llm.reasoning = {"effort": effort, "summary": None}
        #     llm.output_version = "responses/v1"
    return llm


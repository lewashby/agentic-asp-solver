

from pydantic import BaseModel, Field


class ASPSystemConfig(BaseModel):
    """Configuration for the ASP system"""
    
    # LLM configuration
    model_name: str = "gpt-oss:20b"
    temperature: float = 0.0
    base_url: str = "http://localhost:11434/v1"  # Ollama default
    api_key: str = "ollama"  # Ollama doesn't need real key
    
    # MCP Server configuration
    mcp_server_config: dict = Field(default_factory=dict)
    
    # System behavior
    max_iterations: int = 5
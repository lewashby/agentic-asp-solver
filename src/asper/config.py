import os
from typing import Optional
from pydantic import BaseModel, Field, field_validator
from pathlib import Path

class MCPServerConfig(BaseModel):
    """MCP Server configuration."""
    
    command: str
    args: list[str] = Field(default_factory=list)
    transport: str = "stdio"
    
    @field_validator('args', mode='before')
    @classmethod
    def parse_args(cls, v):
        """Parse args from string or list."""
        if isinstance(v, str):
            return [arg.strip() for arg in v.split(',') if arg.strip()]
        return v

class ASPSystemConfig(BaseModel):
    """Configuration for the ASP system"""
    
    # LLM configuration
    model_name: str = "gpt-oss:20b"
    temperature: float = 0.0
    base_url: str = "http://localhost:11434/v1"  # Ollama default
    api_key: str = "ollama"  # Ollama doesn't need real key

    #Prompts
    solver_prompt_file: Optional[Path] = None
    validator_prompt_file: Optional[Path] = None
    
    # MCP Server configuration
    mcp_servers: dict[str, MCPServerConfig] = Field(default_factory=dict)
    
    # System behavior
    max_iterations: int = 5

    @classmethod
    def from_env(cls, **overrides) -> "ASPSystemConfig":
        """Load configuration from environment variables with optional overrides.
        
        Args:
            **overrides: Any configuration values to override from environment
            
        Returns:
            ASPSystemConfig instance with values from env and overrides
            
        Raises:
            ValueError: If required environment variables are missing
        """
        # Check for required MCP configuration
        if not os.getenv("MCP_SOLVER_COMMAND"):
            raise ValueError(
                "MCP_SOLVER_COMMAND not found in environment.\n"
                "Please set it in your .env file (e.g., MCP_SOLVER_COMMAND=uv)"
            )
        
        if not os.getenv("MCP_SOLVER_ARGS"):
            raise ValueError(
                "MCP_SOLVER_ARGS not found in environment.\n"
                "Please set it in your .env file with the absolute path to mcp-solver.\n"
                "Example: MCP_SOLVER_ARGS=--directory,/absolute/path/to/mcp-solver,run,mcp-solver-asp"
            )
        
        # Parse MCP args from environment
        mcp_args_env = os.getenv("MCP_SOLVER_ARGS", "")
        mcp_args = [arg.strip() for arg in mcp_args_env.split(',') if arg.strip()]
        
        if not mcp_args:
            raise ValueError(
                "MCP_SOLVER_ARGS is empty.\n"
                "Please set it with the correct format: --directory,/path/to/mcp-solver,run,mcp-solver-asp"
            )
        
        # Build base configuration from environment
        config_dict = {
            "model_name": os.getenv("MODEL_NAME", "gpt-oss:20b"),
            "temperature": float(os.getenv("TEMPERATURE", "0.0")),
            "base_url": os.getenv("OPENAI_BASE_URL", "http://localhost:11434/v1"),
            "api_key": os.getenv("OPENAI_API_KEY", "ollama"),
            "max_iterations": int(os.getenv("MAX_ITERATIONS", "5")),
            "mcp_servers": {
                "mcp-solver": MCPServerConfig(
                    command=os.getenv("MCP_SOLVER_COMMAND", "uv"),
                    args=mcp_args,
                    transport=os.getenv("MCP_SOLVER_TRANSPORT", "stdio")
                )
            }
        }
        
        # Apply overrides (filter out None values)
        filtered_overrides = {k: v for k, v in overrides.items() if v is not None}
        config_dict.update(filtered_overrides)
        
        return cls(**config_dict)
    
    def get_mcp_server(self, name: str = "mcp-solver") -> MCPServerConfig:
        """Get MCP server configuration by name.
        
        Args:
            name: Server name (default: "mcp-solver")
            
        Returns:
            MCPServerConfig for the requested server
            
        Raises:
            KeyError: If server name not found
        """
        if name not in self.mcp_servers.keys():
            raise KeyError(f"MCP server '{name}' not found in configuration")
        return self.mcp_servers[name]
"""Configuration models for ASP system and MCP server integration.

Defines MCPServerConfig and ASPSystemConfig with environment-based loading,
validation, and access to model, prompt, and MCP solver settings.
"""

import os
from pathlib import Path

from pydantic import BaseModel, Field, field_validator


class MCPServerConfig(BaseModel):
    """MCP Server configuration for stdio-based tool integration.

    Attributes:
        command: Executable command (e.g., 'uv')
        args: List of arguments (e.g., ['--directory', '/path', 'run', 'mcp-solver-asp'])
        transport: Communication protocol (default: 'stdio')
    """

    command: str
    args: list[str] = Field(default_factory=list)
    transport: str = "stdio"

    @field_validator("args", mode="before")
    @classmethod
    def parse_args(cls, v):
        """Parse args from comma-separated string or list.

        Args:
            v: String or list of arguments

        Returns:
            List of argument strings
        """
        if isinstance(v, str):
            return [arg.strip() for arg in v.split(",") if arg.strip()]
        return v


class ASPSystemConfig(BaseModel):
    """Configuration for the ASP multi-agent system.

    Attributes:
        chat_model_type: Chat model type ('openai' or 'ollama', default: 'ollama')
        model_name: LLM model identifier (default: 'gpt-oss:20b')
        temperature: Sampling temperature (default: 0.0)
        base_url: OpenAI-compatible API endpoint (default: Ollama)
        api_key: API key (default: 'ollama' for local models)
        reasoning: Reasoning level for reasoning models ('low', 'medium', 'high', or bool)
        solver_prompt_file: Optional custom solver prompt file path
        validator_prompt_file: Optional custom validator prompt file path
        mcp_servers: Dictionary of MCP server configurations by name
        max_iterations: Maximum solver-validator loop iterations (default: 5)
    """

    # LLM configuration
    chat_model_type: str = "ollama"  # 'openai' or 'ollama'
    model_name: str = "gpt-oss:20b"
    temperature: float = 0.0
    base_url: str = "http://localhost:11434/v1"  # Ollama default
    api_key: str = "ollama"  # Ollama doesn't need real key
    reasoning: str | bool = False # 'low', 'medium', 'high', True, or False

    # Prompts
    solver_prompt_file: Path | None = None
    validator_prompt_file: Path | None = None

    # MCP Server configuration
    mcp_servers: dict[str, MCPServerConfig] = Field(default_factory=dict)

    # System behavior
    max_iterations: int = 5

    @field_validator("chat_model_type")
    @classmethod
    def validate_chat_model_type(cls, v):
        """Validate chat_model_type is either 'openai' or 'ollama'.

        Args:
            v: Chat model type string

        Returns:
            Validated chat model type

        Raises:
            ValueError: If chat_model_type is not 'openai' or 'ollama'
        """
        if v.lower() not in ["openai", "ollama"]:
            raise ValueError("chat_model_type must be 'openai' or 'ollama'")
        return v.lower()

    @field_validator("reasoning")
    @classmethod
    def validate_reasoning(cls, v):
        """Validate reasoning is a boolean or 'low', 'medium', 'high'.

        Args:
            v: Reasoning level

        Returns:
            Validated reasoning value

        Raises:
            ValueError: If reasoning is invalid
        """
        if isinstance(v, bool):
            return v
        if isinstance(v, str):
            lower_v = v.lower()
            if lower_v == "true":
                return True
            if lower_v == "false":
                return False
            if v.lower() in ["low", "medium", "high"]:
                return v.lower()
            raise ValueError(
                "reasoning must be a boolean, 'low', 'medium', 'high', 'true', or 'false'"
            )

    @classmethod
    def from_env(cls, **overrides) -> "ASPSystemConfig":
        """Load configuration from environment variables with optional overrides.

        Reads MCP_SOLVER_COMMAND, MCP_SOLVER_ARGS (required), MODEL_NAME,
        OPENAI_BASE_URL, OPENAI_API_KEY, TEMPERATURE, and MAX_ITERATIONS.

        Args:
            **overrides: Configuration values to override from environment

        Returns:
            ASPSystemConfig instance with values from env and overrides

        Raises:
            ValueError: If MCP_SOLVER_COMMAND or MCP_SOLVER_ARGS are missing or invalid
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
        mcp_args = [arg.strip() for arg in mcp_args_env.split(",") if arg.strip()]

        if not mcp_args:
            raise ValueError(
                "MCP_SOLVER_ARGS is empty.\n"
                "Please set it with the correct format: --directory,/path/to/mcp-solver,run,mcp-solver-asp"
            )

        # Build base configuration from environment
        config_dict = {
            "chat_model_type": os.getenv("CHAT_MODEL_TYPE", "ollama"),
            "model_name": os.getenv("MODEL_NAME", "gpt-oss:20b"),
            "temperature": float(os.getenv("TEMPERATURE", "0.0")),
            "base_url": os.getenv("OPENAI_BASE_URL", "http://localhost:11434/v1"),
            "api_key": os.getenv("OPENAI_API_KEY", "ollama"),
            "reasoning": os.getenv("REASONING_LEVEL", False),
            "max_iterations": int(os.getenv("MAX_ITERATIONS", "5")),
            "mcp_servers": {
                "mcp-solver": MCPServerConfig(
                    command=os.getenv("MCP_SOLVER_COMMAND", "uv"),
                    args=mcp_args,
                    transport=os.getenv("MCP_SOLVER_TRANSPORT", "stdio"),
                )
            },
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
            KeyError: If server name not found in mcp_servers
        """
        if name not in self.mcp_servers.keys():
            raise KeyError(f"MCP server '{name}' not found in configuration")
        return self.mcp_servers[name]

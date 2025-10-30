"""MCP Client management for Agentic ASP solver."""

from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from asper.config import ASPSystemConfig, MCPServerConfig
from asper.exceptions import MCPError, classify_exception


class MCPClientManager:
    """Manages MCP client lifecycle and tool loading."""

    def __init__(self, config: ASPSystemConfig):
        """Initialize MCP client manager.

        Args:
            config: System configuration containing MCP server settings
        """
        self.config = config
        self._validate_configuration()

    def _validate_configuration(self) -> None:
        """Validate MCP server configuration.

        Raises:
            MCPError: If configuration is invalid
        """
        try:
            server_config = self.config.get_mcp_server("mcp-solver")
        except KeyError:
            raise MCPError(
                "MCP server 'mcp-solver' not found in configuration. "
                "Please check your .env file has MCP_SOLVER_COMMAND and MCP_SOLVER_ARGS set."
            )

        # Check command is not empty
        if not server_config.command or not server_config.command.strip():
            raise MCPError(
                "MCP_SOLVER_COMMAND is empty. Please set it in your .env file "
                "(e.g., MCP_SOLVER_COMMAND=uv)"
            )

        # Check if command exists in PATH
        import shutil

        if not shutil.which(server_config.command):
            raise MCPError(
                f"Command '{server_config.command}' not found in PATH. "
                f"Please install it or check your MCP_SOLVER_COMMAND setting. "
                f"For 'uv', install with: pip install uv"
            )

        # Validate directory path if present in args
        self._validate_directory_arg(server_config.args)

    def _validate_directory_arg(self, args: list[str]) -> None:
        """Validate --directory argument if present.

        Args:
            args: List of command arguments

        Raises:
            MCPError: If directory path is invalid
        """
        for i, arg in enumerate(args):
            if arg == "--directory" and i + 1 < len(args):
                directory_path = args[i + 1]
                dir_path = Path(directory_path)

                if not dir_path.exists():
                    raise MCPError(
                        f"MCP solver directory not found: {directory_path}\n"
                        f"Please check MCP_SOLVER_ARGS in your .env file.\n"
                        f"The path must be absolute (e.g., /home/user/mcp-solver or C:/dev/mcp-solver)"
                    )

                if not dir_path.is_dir():
                    raise MCPError(
                        f"MCP solver path is not a directory: {directory_path}\n"
                        f"Please provide the path to the mcp-solver folder."
                    )

                # Check if pyproject.toml exists (indicates it's the right directory)
                pyproject = dir_path / "pyproject.toml"
                if not pyproject.exists():
                    raise MCPError(
                        f"Directory {directory_path} doesn't appear to be an mcp-solver installation.\n"
                        f"No pyproject.toml found. Did you clone the mcp-solver repository here?\n"
                        f"Expected: git clone https://github.com/szeider/mcp-solver.git"
                    )

    @asynccontextmanager
    async def get_session(
        self, server_name: str = "mcp-solver"
    ) -> AsyncIterator[ClientSession]:
        """Context manager for MCP session.

        Args:
            server_name: Name of the MCP server to connect to

        Yields:
            Initialized ClientSession

        Raises:
            MCPError: If session initialization fails

        Example:
            async with manager.get_session() as session:
                tools = await load_mcp_tools(session)
        """
        try:
            async with self.get_stdio_client(server_name) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    yield session
        except MCPError:
            raise
        except Exception as e:
            raise classify_exception(e)

    def _create_server_params(
        self, server_config: MCPServerConfig
    ) -> StdioServerParameters:
        """Create StdioServerParameters from configuration.

        Args:
            server_config: MCP server configuration

        Returns:
            StdioServerParameters for the server
        """
        return StdioServerParameters(
            command=server_config.command, args=server_config.args
        )

    @asynccontextmanager
    async def get_stdio_client(
        self, server_name: str = "mcp-solver"
    ) -> AsyncIterator[tuple]:
        """Get raw stdio client for advanced usage.

        Args:
            server_name: Name of the MCP server

        Yields:
            Tuple of (read, write) streams
        """
        server_config = self.config.get_mcp_server(server_name)
        server_params = self._create_server_params(server_config)

        async with stdio_client(server_params) as (read, write):
            yield (read, write)

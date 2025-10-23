"""MCP connection tests.
"""

import os
import pytest
from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

load_dotenv()

pytestmark = pytest.mark.anyio


@pytest.fixture
def skip_if_no_mcp():
    """Skip test if MCP is not configured."""
    if not os.getenv("MCP_SOLVER_COMMAND") or not os.getenv("MCP_SOLVER_ARGS"):
        pytest.skip("MCP not configured - set MCP_SOLVER_COMMAND and MCP_SOLVER_ARGS")


@pytest.fixture
def mcp_server_params():
    """Get MCP server parameters from environment."""
    command = os.getenv("MCP_SOLVER_COMMAND", "")
    args_str = os.getenv("MCP_SOLVER_ARGS", "")
    args = [arg.strip() for arg in args_str.split(',') if arg.strip()]
    
    return StdioServerParameters(command=command, args=args)


class TestMCPConnection:
    """Test MCP server connection."""
    
    async def test_stdio_client_connects(self, skip_if_no_mcp, mcp_server_params):
        """Test stdio client can connect to MCP server."""
        async with stdio_client(mcp_server_params) as (read, write):
            assert read is not None
            assert write is not None
    
    async def test_session_initializes(self, skip_if_no_mcp, mcp_server_params):
        """Test MCP session can be initialized."""
        async with stdio_client(mcp_server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                # If we get here without exception, initialization succeeded
                assert True
    
    async def test_list_tools(self, skip_if_no_mcp, mcp_server_params):
        """Test MCP server provides tools."""
        async with stdio_client(mcp_server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.list_tools()
                
                assert len(result.tools) > 0, "MCP server should provide at least one tool"
    
    async def test_expected_tools_available(self, skip_if_no_mcp, mcp_server_params):
        """Test that expected ASP solver tools are available."""
        expected_tools = ["add_item", "replace_item", "remove_item", "solve_model", "get_model", "clear_model"]
        
        async with stdio_client(mcp_server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.list_tools()
                
                tool_names = [t.name for t in result.tools]
                
                missing_tools = [t for t in expected_tools if t not in tool_names]
                assert len(missing_tools) == 0, f"Missing expected tools: {missing_tools}"


class TestMCPToolsLoad:
    """Test MCP tools can be loaded for use."""
    
    async def test_load_mcp_tools(self, skip_if_no_mcp, mcp_server_params):
        """Test loading MCP tools with langchain adapter."""
        from langchain_mcp_adapters.tools import load_mcp_tools
        
        async with stdio_client(mcp_server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools = await load_mcp_tools(session)
                
                assert len(tools) > 0, "Should load at least one tool"
    
    async def test_tools_have_names(self, skip_if_no_mcp, mcp_server_params):
        """Test that loaded tools have proper names."""
        from langchain_mcp_adapters.tools import load_mcp_tools
        
        async with stdio_client(mcp_server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools = await load_mcp_tools(session)
                
                for tool in tools:
                    assert hasattr(tool, 'name'), "Tool should have a name"
                    assert tool.name, "Tool name should not be empty"


class TestMCPServerInfo:
    """Test MCP server information."""
    
    async def test_server_info(self, skip_if_no_mcp, mcp_server_params):
        """Test getting server information."""
        async with stdio_client(mcp_server_params) as (read, write):
            async with ClientSession(read, write) as session:
                result = await session.initialize()
                
                # Server should provide some info
                assert result is not None
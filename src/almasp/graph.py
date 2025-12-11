"""LangGraph workflow definition for Agentic ASP solver."""

from langchain_core.tools import BaseTool
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langchain.agents import create_agent
from langgraph.types import RetryPolicy
from langchain_core.runnables.config import RunnableConfig
from langchain.agents.middleware import AgentMiddleware
from langchain_core.messages import ToolMessage

from almasp.config import ASPSystemConfig
from almasp.llm import build_llm
from almasp.mcp_client import MCPClientManager
from almasp.prompts import PromptManager
from almasp.state import ASPState
from almasp.workflow import should_continue, solver_node, validator_node

class AsyncMiddleware(AgentMiddleware):
    """Async middleware wrapper for tool calls."""
    async def awrap_tool_call(self, request, handler):
        """Handle tool execution errors with custom messages."""
        try:
            return await handler(request)
        except Exception as e:
            # Return a custom error message to the model
            return ToolMessage(
                content=f"An error occurred invoking the tool. Please try differently. ({str(e)})",
                tool_call_id=request.tool_call["id"]
            )


async def create_asp_system(
    llm,
    tools: list[BaseTool],
    solver_prompt: str | None = None,
    validator_prompt: str | None = None,
) -> CompiledStateGraph:
    """Create and compile the ASP multi-agent system graph.

    Args:
        llm: Language model instance
        tools: List of MCP tools to use
        solver_prompt: Optional custom solver prompt (uses default if None)
        validator_prompt: Optional custom validator prompt (uses default if None)

    Returns:
        Compiled LangGraph application
    """

    # Use provided prompts or fall back to defaults
    final_solver_prompt = solver_prompt or PromptManager.SOLVER.default_content
    final_validator_prompt = validator_prompt or PromptManager.VALIDATOR.default_content

    # Create ReAct agents
    solver_agent = create_agent(
        llm,
        tools=tools,
        middleware=[AsyncMiddleware()],
        system_prompt=final_solver_prompt,
    )

    # Validator only needs solve_model and add_item tools
    validator_tools = [
        tool for tool in tools if tool.name in ["get_model", "solve_model"]
    ]

    validator_agent = create_agent(
        llm,
        tools=validator_tools,
        middleware=[AsyncMiddleware()],
        system_prompt=final_validator_prompt,
    )

    # Create wrapper functions for nodes
    async def solver_node_wrapper(state):
        return await solver_node(state, solver_agent)

    async def validator_node_wrapper(state):
        return await validator_node(state, validator_agent)

    # Create parent state graph
    workflow = StateGraph(ASPState)

    # Add nodes with retry policy
    workflow.add_node("solver", solver_node_wrapper, retry_policy=RetryPolicy())
    workflow.add_node("validator", validator_node_wrapper, retry_policy=RetryPolicy())

    # Add edges
    workflow.add_edge(START, "solver")
    workflow.add_edge("solver", "validator")
    workflow.add_conditional_edges(
        "validator", should_continue, {"solver": "solver", "end": END}
    )

    # Compile with checkpointing
    memory = InMemorySaver()
    app = workflow.compile(checkpointer=memory)

    return app


async def _create_agents_graph(config: RunnableConfig):
    """Graph factory for LangGraph Studio/Dev.

    This function is called by LangGraph Studio and must accept
    exactly one RunnableConfig parameter.

    Args:
        config: Runtime configuration from LangGraph

    Returns:
        Compiled graph ready for execution
    """
    # Extract configurable values
    configurable = {}
    if isinstance(config, dict):
        configurable = config.get("configurable", {})
    elif hasattr(config, "configurable"):
        configurable = config.configurable or {}

    # Build system configuration from environment with overrides
    system_config = ASPSystemConfig.from_env(
        model_name=configurable.get("model_name"),
        max_iterations=configurable.get("max_iterations"),
    )

    # Load MCP tools using the client manager
    mcp_manager = MCPClientManager(system_config)

    async with mcp_manager.get_session("mcp-solver") as session:
        from langchain_mcp_adapters.tools import load_mcp_tools

        tools = await load_mcp_tools(session)

        # Build LLM
        llm = build_llm(system_config)

        # Create and return the graph
        app = await create_asp_system(llm, tools)
        return app

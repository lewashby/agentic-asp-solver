import os
from langgraph.checkpoint.memory import InMemorySaver
from langchain_core.tools import BaseTool
from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, START, END
from langgraph.types import RetryPolicy, RunnableConfig
from langgraph.prebuilt import create_react_agent, ToolNode
from langchain_mcp_adapters.tools import load_mcp_tools
from langchain_mcp_adapters.client import MultiServerMCPClient

from asper.config import ASPSystemConfig
from asper.llm import build_llm
from asper.state import ASPState
from asper.prompts import SOLVER_SYSTEM_PROMPT, VALIDATOR_SYSTEM_PROMPT
from asper.workflow import should_continue, solver_node, validator_node


async def create_asp_system(
    llm,
    tools: list[BaseTool],
    solver_prompt: str | None = None,
    validator_prompt: str | None = None,
):
    """Create and compile the ASP multi-agent system graph."""

    tool_error_message="An error occurred invoking the tool. Please try differently."
    
    # Create ReAct agents
    solver_agent = create_react_agent(
        llm,
        tools=ToolNode(tools=tools, handle_tool_errors=tool_error_message),
        prompt=solver_prompt or SOLVER_SYSTEM_PROMPT
    )
    
    validator_agent = create_react_agent(
        llm,
        tools=ToolNode(tools=[tool for tool in tools if tool.name in ["solve_model", "add_item"]], handle_tool_errors=tool_error_message),
        prompt=validator_prompt or VALIDATOR_SYSTEM_PROMPT
    )

    async def solver_node_wrapper(state):
        return await solver_node(state, solver_agent)

    async def validator_node_wrapper(state):
        return await validator_node(state, validator_agent)
    
    # Create parent state graph
    workflow = StateGraph(ASPState)
    
    # Add nodes (async wrappers ensure coroutines are awaited)
    workflow.add_node("solver", solver_node_wrapper, retry_policy=RetryPolicy())
    workflow.add_node("validator", validator_node_wrapper, retry_policy=RetryPolicy())
    
    # Add edges
    workflow.add_edge(START, "solver")
    workflow.add_edge("solver", "validator")
    workflow.add_conditional_edges(
        "validator",
        should_continue,
        {
            "solver": "solver",
            "end": END
        }
    )
    
    # Compile with checkpointing
    memory = InMemorySaver()
    app = workflow.compile(checkpointer=memory)
    
    return app


async def _create_agents_graph(config: RunnableConfig):
    """
    Graph factory for LangGraph Studio/Dev. Must accept exactly one RunnableConfig.

    It builds an internal ASPSystemConfig from environment or configurable overrides
    and returns the compiled graph (Runnable).
    """
    configurable = (config or {}).get("configurable", {}) if isinstance(config, dict) else getattr(config, "configurable", {})

    # Resolve configuration from env with optional overrides from RunnableConfig.configurable
    model_name = configurable.get("model_name") or os.getenv("MODEL_NAME") or ASPSystemConfig().model_name
    base_url = os.getenv("OPENAI_BASE_URL", ASPSystemConfig().base_url)
    api_key = os.getenv("OPENAI_API_KEY", ASPSystemConfig().api_key)
    max_iterations = int(configurable.get("max_iterations") or os.getenv("MAX_ITERATIONS", str(ASPSystemConfig().max_iterations)))

    mcp_args_env = os.getenv("MCP_SOLVER_ARGS", "")
    mcp_args = [arg for arg in mcp_args_env.split(',') if arg] if mcp_args_env else []
    mcp_server_config = {
        "mcp-solver": {
            "command": os.getenv("MCP_SOLVER_COMMAND"),
            "args": mcp_args,
            "transport": os.getenv("MCP_SOLVER_TRANSPORT"),
        }
    }

    system_config = ASPSystemConfig(
        model_name=model_name,
        base_url=base_url,
        api_key=api_key,
        mcp_server_config=mcp_server_config,
        max_iterations=max_iterations,
    )

    # Load MCP tools and build the app
    mcp_client = MultiServerMCPClient(system_config.mcp_server_config)
    async with mcp_client.session("mcp-solver") as session:
        tools = await load_mcp_tools(session)
        llm = build_llm(system_config)
        app = await create_asp_system(llm, tools)
        return app


async def solve_asp_problem(
    problem_description: str,
    config: ASPSystemConfig,
    *,
    solver_prompt: str | None = None,
    validator_prompt: str | None = None,
) -> dict:
    """
    Main function to solve an ASP problem using the multi-agent system
    
    Args:
        problem_description: Natural language description of the problem
        config: System configuration
        
    Returns:
        dict with final ASP code, validation status, and history
    """
    # Create the system
    mcp_client = MultiServerMCPClient(config.mcp_server_config)
    async with mcp_client.session("mcp-solver") as session:
        tools = await load_mcp_tools(session)
        llm = build_llm(config)
        app = await create_asp_system(llm, tools, solver_prompt=solver_prompt, validator_prompt=validator_prompt)
        
        # Initial state
        initial_state = ASPState(
            messages=[HumanMessage(content=problem_description)],
            problem_description=problem_description,
            max_iterations=config.max_iterations
        )
        
        try:
            # Run the graph
            final_state = await app.ainvoke(
                initial_state.model_dump(),
                config={"configurable": {"thread_id": "asp-solver-session"}, "recursion_limit": 50},
            )
            
            # Prepare result
            result = {
                "success": final_state["is_validated"],
                "asp_code": final_state["asp_code"],
                "iterations": final_state["iteration_count"],
                "messages_history": final_state["messages"],
                "validation_history": final_state["validation_history"],
                "message": final_state.get("last_feedback", "")
            }
            
            if not final_state["is_validated"]:
                result["message"] = f"Max iterations ({config.max_iterations}) reached. Best attempt returned."
            
            return result
            
        except Exception as e:
            # Handle error
            print(f"Generic error: {e}")
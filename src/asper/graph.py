
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver
from langchain_core.tools import BaseTool
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import create_react_agent
from langchain_mcp_adapters.tools import load_mcp_tools
from langchain_mcp_adapters.client import MultiServerMCPClient

from asper.config import ASPSystemConfig
from asper.state import ASPState
from asper.prompts import SOLVER_SYSTEM_PROMPT, VALIDATOR_SYSTEM_PROMPT
from asper.react_agent import should_continue, solver_node, validator_node


async def create_asp_system(config: ASPSystemConfig, tools: list[BaseTool]):
    """
    Create the complete ASP multi-agent system
    """
    
    # Initialize LLM
    llm = ChatOpenAI(
        model=config.model_name,
        temperature=config.temperature,
        base_url=config.base_url,
        api_key=config.api_key
    )
    
    # Create ReAct agents
    solver_agent = create_react_agent(
        llm,
        tools=tools,
        prompt=SOLVER_SYSTEM_PROMPT
    )
    
    validator_agent = create_react_agent(
        llm,
        tools=tools,
        prompt=VALIDATOR_SYSTEM_PROMPT
    )

    async def solver_node_wrapper(state):
        return await solver_node(state, solver_agent)

    async def validator_node_wrapper(state):
        return await validator_node(state, validator_agent)
    
    # Create parent state graph
    workflow = StateGraph(ASPState)
    
    # Add nodes (async wrappers ensure coroutines are awaited)
    workflow.add_node("solver", solver_node_wrapper)
    workflow.add_node("validator", validator_node_wrapper)
    
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


async def solve_asp_problem(
    problem_description: str,
    config: ASPSystemConfig
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
        app = await create_asp_system(config, tools)
        
        # Initial state
        initial_state = ASPState(
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
                "validation_history": final_state["validation_history"],
                "message": final_state.get("last_feedback", "")
            }
            
            if not final_state["is_validated"]:
                result["message"] = f"Max iterations ({config.max_iterations}) reached. Best attempt returned."
            
            return result
            
        except Exception as e:
            # Handle error
            print(f"Generic error: {e}")
"""Workflow nodes and control flow for the ASP solver-validator loop.

Implements solver_node (generates/improves ASP code), validator_node (tests and
provides feedback), should_continue routing, and helper functions for message
creation and agent invocation with token/tool usage tracking.
"""

from typing import Literal

from anyio import ClosedResourceError
from langchain_core.messages import AnyMessage, HumanMessage
from langgraph.graph.state import CompiledStateGraph

from almasp.state import ASPState
from almasp.utils import analyze_asp_code, get_logger
from langchain_core.runnables import RunnableConfig

logger = get_logger()

def get_default_graph_config(
    thread_id: str = "1",
    recursion_limit: int = 100,
) -> RunnableConfig:
    return RunnableConfig(
        {
            "configurable": {"thread_id": thread_id},
            "recursion_limit": recursion_limit,
        },
    )


async def call_agent(history: list[AnyMessage], agent: CompiledStateGraph) -> dict:
    """Invoke a ReAct agent and collect messages plus usage statistics.

    Streams agent execution, logs tool calls and LLM invocations with token counts,
    and aggregates input/output/total tokens and tool call counts.

    Args:
        history: Message history to pass to the agent
        agent: Compiled LangGraph agent to invoke

    Returns:
        Dictionary with 'messages' (list of new messages) and 'statistics' (token/tool usage)

    Raises:
        RuntimeError: If model not found (404 error)
    """
    messages = []
    stats = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0, "tool_calls": 0}
    try:
        logger.debug("Starting agent astream with %d history messages", len(history))
        async for chunk in agent.astream(
            {"messages": history},
            config=get_default_graph_config(),
            stream_mode="updates",
        ):
            if not chunk:
                continue
            node_name = next(iter(chunk.keys()))
            node_output = chunk[node_name]

            if "messages" in node_output:
                for msg in node_output["messages"]:
                    if node_name == "tools":
                        operation_name = msg.name
                        stats["tool_calls"] += 1
                        outcome = (
                            "failed"
                            if "Failed" in getattr(msg, "content", "")
                            or "Error" in getattr(msg, "content", "")
                            else "success"
                        )
                        logger.info(
                            "%s %s operation %s", node_name, operation_name, outcome
                        )
                    else:
                        usage = getattr(
                            msg, "usage_metadata", None
                        ) or msg.response_metadata.get("token_usage", {})
                        input_tokens = usage.get("input_tokens") or usage.get(
                            "prompt_tokens", 0
                        )
                        output_tokens = usage.get("output_tokens") or usage.get(
                            "completion_tokens", 0
                        )
                        total_tokens = usage.get("total_tokens", 0)
                        if hasattr(msg, "tool_calls") and msg.tool_calls:
                            for operation in msg.tool_calls:
                                operation_name = operation.get("name")
                                logger.info(
                                    "%s called tool: %s ---- Input Tokens: %s | Output Tokens: %s | Total Tokens: %s",
                                    node_name,
                                    operation_name,
                                    input_tokens,
                                    output_tokens,
                                    total_tokens,
                                )
                        else:
                            logger.info(
                                "%s called LLM ---- Input Tokens: %s | Output Tokens: %s | Total Tokens: %s",
                                node_name,
                                input_tokens,
                                output_tokens,
                                total_tokens,
                            )
                        stats["input_tokens"] += input_tokens
                        stats["output_tokens"] += output_tokens
                        stats["total_tokens"] += total_tokens
                    messages.append(msg)
            else:
                logger.debug(
                    "%s produced a non-message update: %s",
                    node_name,
                    list(node_output.keys()),
                )
        logger.debug("Agent astream completed with %d messages", len(messages))
    except Exception as e:
        msg = str(e)
        lowered = msg.lower()
        logger.error("Agent stream raised exception: %s", msg)
        if ("404" in lowered or "not found" in lowered) and "model" in lowered:
            raise RuntimeError(f"MODEL_NOT_FOUND: {msg}")
        else:
            raise

    return {"messages": messages, "statistics": stats}


def create_solver_message(
    state: ASPState, is_first_iteration: bool
) -> list[AnyMessage]:
    """Create focused message for solver agent.

    First iteration: presents the problem description.
    Later iterations: includes validator feedback and current ASP code.

    Args:
        state: Current ASP workflow state
        is_first_iteration: Whether this is the initial solver call

    Returns:
        List of messages to send to solver agent
    """
    if is_first_iteration:
        content = f"""Problem to solve:

{state.problem_description}

Please create an ASP encoding for this problem using the MCP Solver tools.
Build the encoding step by step and test it with solve_model when ready."""
        return [HumanMessage(content=content)]
    else:
        messages = state.messages
        content = f"""A validator expert in Answer Set Programming provided this feedback on your ASP code:

{state.last_feedback if state.last_feedback else "The code do not model correctly the problem."}
{f"\n\nCurrent ASP code state:\n{state.asp_code}\n\n" if state.asp_code else ""}
Please address the feedback and improve the encoding using the MCP Solver tools."""

        messages.append(HumanMessage(content=content))
        return messages


def create_validator_message(state: ASPState) -> list[AnyMessage]:
    """Create focused message for validator agent.

    Includes original problem and current ASP code for validation.

    Args:
        state: Current workflow state

    Returns:
        List containing a single HumanMessage for the validator
    """
    content = f"""Original problem:
{state.problem_description}

Call get_model to obtain the current ASP code to validate it against the problem requirements.
Use solve_model to test it and provide clear feedback on whether it's correct."""
    return [HumanMessage(content=content)]


async def solver_node(state: ASPState, solver_agent: CompiledStateGraph) -> dict:
    """Solver agent node - generates or improves ASP code.

    Invokes the solver ReAct agent with problem description (first iteration)
    or validator feedback (subsequent iterations).

    Args:
        state: Current workflow state
        solver_agent: Compiled solver agent graph

    Returns:
        State updates: incremented iteration_count, new messages, asp_code,
        reset validation flags, and accumulated statistics
    """
    logger.info("Solver iteration %d starting", state.iteration_count + 1)

    is_first = state.iteration_count == 0
    messages = create_solver_message(state, is_first)

    # Invoke the solver ReAct agent
    try:
        result = await call_agent(messages, solver_agent)

        return {
            "iteration_count": state.iteration_count + 1,
            "messages": result["messages"],
            "asp_code": result["messages"][-1].content,
            "is_validated": False,
            "last_feedback": "",
            "statistics": result["statistics"],
        }
    except ClosedResourceError as e:
        logger.error("Solver node failed due to closed MCP connection: %s", str(e))
        return {
            "error_code": "MCP_CONNECTION_CLOSED",
        }
    except RuntimeError as e:
        # Model not found error from call_agent
        logger.error("Solver agent failed: %s", str(e))
        return {
            "error_code": "RUNTIME_ERROR",
        }


async def validator_node(state: ASPState, validator_agent: CompiledStateGraph) -> dict:
    """Validate ASP code against problem requirements.

    Test the current ASP code using MCP tools and determine PASS/FAIL.
    Skip validation if no code is present.

    Args:
        state: Current workflow state
        validator_agent: Compiled validator agent graph

    Returns:
        State updates: is_validated flag, last_feedback, validation_history,
        and accumulated statistics
    """
    message = create_validator_message(state)
    logger.info("Validator evaluating iteration %d", state.iteration_count)

    if state.error_code:
        logger.info("Validator skipped due to existing error: %s", state.error_code)
        return {
            "is_validated": False,
            "messages": state.messages,
            "last_feedback": "Validation skipped due to existing error in workflow.",
        }
    
    try:
        result = await call_agent(message, validator_agent)

        # Extract validation result from the agent's response
        agent_response = result["messages"][-1].content

        # Determine if validation passed
        is_valid = "VALIDATION PASSED" in agent_response.upper()
        logger.info("Validation result: %s", "PASSED" if is_valid else "FAILED")

        if is_valid:
            postprocessed_asp_code, unused_heads = analyze_asp_code(state.asp_code)
            logger.info("Validator found and commented out %d unused rules", len(unused_heads))

        return {
            "is_validated": is_valid,
            "last_feedback": agent_response,
            "asp_code": postprocessed_asp_code if is_valid else state.asp_code,
            "validation_history": result["messages"],
            "statistics": result["statistics"],
        }
    except ClosedResourceError as e:
        logger.error("Validator node failed due to closed MCP connection: %s", str(e))
        return {
            "error_code": "MCP_CONNECTION_CLOSED",
        }
    except RuntimeError as e:
        logger.error("Validator agent failed: %s", str(e))
        return {
            "error_code": "RUNTIME_ERROR",
        }


def should_continue(state: ASPState) -> Literal["solver", "end"]:
    """Determine if we should continue iterating or end.

    Routing logic:
    - If validated: end
    - If max_iterations reached: end
    - Otherwise: continue to solver

    Args:
        state: Current workflow state

    Returns:
        'solver' to continue iteration or 'end' to finish
    """
    if state.error_code:
        logger.info("Stopping due to error: %s", state.error_code)
        return "end"

    # If validated, we're done
    if state.is_validated:
        logger.info(
            "Stopping: solution validated at iteration %d", state.iteration_count
        )
        return "end"

    # If max iterations reached, end with best attempt
    if state.iteration_count >= state.max_iterations:
        logger.info("Stopping: reached max iterations (%d)", state.max_iterations)
        return "end"

    # Otherwise, go back to solver for improvements
    logger.debug(
        "Continuing to next solver iteration (%d -> %d)",
        state.iteration_count,
        state.iteration_count + 1,
    )
    return "solver"

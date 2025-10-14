from typing import Literal
import logging
from langgraph.graph.state import CompiledStateGraph
from langchain_core.messages import AnyMessage, HumanMessage
from asper.state import ASPState

logger = logging.getLogger(__name__)


async def call_agent(history: list[AnyMessage], agent: CompiledStateGraph) -> dict:
     messages = []
     try:
          logger.debug("Starting agent astream with %d history messages", len(history))
          async for chunk in agent.astream({"messages": history}, stream_mode="updates"):
               if not chunk:
                    continue
               node_name = next(iter(chunk.keys()))
               node_output = chunk[node_name]
               if "messages" in node_output:
                    for msg in node_output["messages"]:
                         if hasattr(msg, "tool_calls") and msg.tool_calls:
                              for operation in msg.tool_calls:
                                   operation_name = operation.get("name")
                                   logger.info("%s called tool: %s", node_name, operation_name)
                         else:
                              if node_name == "tools":
                                   outcome = "failed" if "Failed" in getattr(msg, "content", "") else "success"
                                   logger.info("%s tool operation %s", node_name, outcome)
                         messages.append(msg)
               else:
                    logger.debug("%s produced a non-message update: %s", node_name, list(node_output.keys()))
     except Exception as e:
          msg = str(e)
          lowered = msg.lower()
          logger.exception("Agent stream raised exception: %s", msg)
          if ("404" in lowered or "not found" in lowered) and "model" in lowered:
               raise RuntimeError(f"MODEL_NOT_FOUND: {msg}")
          else:
               raise
     logger.debug("Agent astream completed with %d messages", len(messages))
     return {"messages": messages}

def create_solver_message(state: ASPState, is_first_iteration: bool) -> list[AnyMessage]:
     """Create focused message for solver agent"""
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
     """Create focused message for validator agent"""
     content = f"""Original problem:
{state.problem_description}

ASP code to validate:

{f"{state.asp_code}" if state.asp_code else "No code yet"}

Please validate this ASP code against the problem requirements.
Use solve_model to test it and provide clear feedback on whether it's correct."""
     return [HumanMessage(content=content)]

async def solver_node(state: ASPState, solver_agent: CompiledStateGraph) -> dict:
     """
     Solver agent node - generates or improves ASP code
     """
     logger.info("Solver iteration %d starting", state.iteration_count + 1)

     is_first = state.iteration_count == 0
     messages = create_solver_message(state, is_first)

     # Invoke the solver ReAct agent
     result = await call_agent(messages, solver_agent)

     return {
          "iteration_count": state.iteration_count + 1,
          "messages": result["messages"],
          "asp_code": result["messages"][-1].content,
          "is_validated": False,
          "last_feedback": ""
     }

async def validator_node(state: ASPState, validator_agent: CompiledStateGraph) -> dict:
     """
     Validator agent node - validates ASP code
     """
     message = create_validator_message(state)
     logger.info("Validator evaluating iteration %d", state.iteration_count)

     if state.asp_code == "":
          logger.warning("Validator skipped: no ASP code present yet")
          return {
               "is_validated": False,
               "messages": state.messages,
               "last_feedback": "No Answer Set Programming (ASP) code was provided. Please call get_model for obtaining the full ASP encoding."
          }

     # Invoke the validator ReAct agent
     result = await call_agent(message, validator_agent)

     # Extract validation result from the agent's response
     agent_response = result["messages"][-1].content

     # Determine if validation passed
     is_valid = "VALIDATION PASSED" in agent_response.upper()
     logger.info("Validation result: %s", "PASSED" if is_valid else "FAILED")

     return {
          "is_validated": is_valid,
          "last_feedback": agent_response,
          "validation_history": result["messages"]
     }

def should_continue(state: ASPState) -> Literal["solver", "end"]:
     """
     Determine if we should continue iterating or end
     """
     # If validated, we're done
     if state.is_validated:
          logger.info("Stopping: solution validated at iteration %d", state.iteration_count)
          return "end"

     # If max iterations reached, end with best attempt
     if state.iteration_count >= state.max_iterations:
          logger.info("Stopping: reached max iterations (%d)", state.max_iterations)
          return "end"

     # Otherwise, go back to solver for improvements
     logger.debug("Continuing to next solver iteration (%d -> %d)", state.iteration_count, state.iteration_count + 1)
     return "solver"
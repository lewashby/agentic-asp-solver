from typing import Literal
from langgraph.graph.state import CompiledStateGraph
from langchain_core.messages import AnyMessage, HumanMessage
from asper.state import ASPState

async def call_agent(history: list[AnyMessage], agent: CompiledStateGraph) -> dict:
     messages = []
     async for chunk in agent.astream({"messages": history}, stream_mode="updates"):
          if chunk:
               node_name = next(iter(chunk.keys()))
               node_output = chunk[node_name]
               if "messages" in node_output:
                    for msg in node_output["messages"]:
                         if hasattr(msg, "tool_calls") and msg.tool_calls:
                              for operation in msg.tool_calls:
                                   operation_name = operation.get("name")
                                   print(f"Node {node_name} called operation {operation_name}")
                         else:
                              if node_name == "tools":
                                   outcome = "failed" if "Failed" in msg.content else "success"
                                   print(f"Node {node_name} operation {outcome}")
                         messages.append(msg)
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
     print("\n###### Called Solver Agent ######\n")

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
     print("\n###### Called Validator Agent ######\n")

     if state.asp_code == "":
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
          return "end"

     # If max iterations reached, end with best attempt
     if state.iteration_count >= state.max_iterations:
          return "end"

     # Otherwise, go back to solver for improvements
     return "solver"
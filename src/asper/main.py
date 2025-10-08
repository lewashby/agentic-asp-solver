import os
import asyncio
from dotenv import load_dotenv

load_dotenv()

from asper.config import ASPSystemConfig
from asper.graph import solve_asp_problem


async def main():
    
    config = ASPSystemConfig(
        model_name=os.getenv("MODEL_NAME"),  # or your preferred Ollama model
        base_url=os.getenv("OPENAI_BASE_URL"),
        api_key=os.getenv("OPENAI_API_KEY"),
        mcp_server_config={
            "mcp-solver": {
                "command": os.getenv("MCP_SOLVER_COMMAND"),
                "args": os.getenv("MCP_SOLVER_ARGS").split(','),
                "transport": os.getenv("MCP_SOLVER_TRANSPORT")
            }
        },
        max_iterations=int(os.getenv("MAX_ITERATIONS"))
    )
    
    # Example problem
    problem = """
    Model a graph coloring problem with 4 nodes and the following edges:
    - Node 1 connects to nodes 2 and 3
    - Node 2 connects to nodes 1, 3, and 4
    - Node 3 connects to nodes 1, 2, and 4
    - Node 4 connects to nodes 2 and 3
    
    Find a valid 3-coloring of this graph where adjacent nodes have different colors.
    """
    
    # Solve the problem
    result = await solve_asp_problem(problem, config)
    
    # Display results
    print("=== ASP Multi-Agent System Results ===")
    print(f"\nSuccess: {result['success']}")
    print(f"Iterations: {result['iterations']}")
    print(f"\nFinal ASP Code:\n{result['asp_code']}")
    print(f"\nValidation History:")
    for record in result['validation_history']:
        print(f"{record}")
    print(f"\nFinal Message: {result['message']}")


if __name__ == "__main__":
    asyncio.run(main())    
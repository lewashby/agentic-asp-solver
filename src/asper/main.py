import os
import asyncio
import argparse
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

from asper.config import ASPSystemConfig
from asper.graph import solve_asp_problem
from asper.utils import read_text_file


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Agentic ASP solver CLI")
    parser.add_argument(
        "problem_file",
        type=Path,
        help="Path to a text/markdown file with the problem description",
    )
    parser.add_argument(
        "--solver-prompt",
        type=Path,
        default=None,
        help="Path to a custom solver system prompt file",
    )
    parser.add_argument(
        "--validator-prompt",
        type=Path,
        default=None,
        help="Path to a custom validator system prompt file",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="LLM model name (overrides env or default)",
    )
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=None,
        help="Maximum number of solver/validator iterations",
    )
    return parser

async def main():
    parser = build_arg_parser()
    args = parser.parse_args()

    # Resolve prompts
    solver_prompt = (
        read_text_file(args.solver_prompt) if args.solver_prompt else None
    )
    validator_prompt = (
        read_text_file(args.validator_prompt) if args.validator_prompt else None
    )

    # Configure system
    model_name = args.model or os.getenv("MODEL_NAME")
    max_iterations = args.max_iterations or int(os.getenv("MAX_ITERATIONS", "5"))

    mcp_args_env = os.getenv("MCP_SOLVER_ARGS", "")
    mcp_args = [arg for arg in mcp_args_env.split(',') if arg] if mcp_args_env else []

    config = ASPSystemConfig(
        model_name=model_name,  # or your preferred Ollama model
        base_url=os.getenv("OPENAI_BASE_URL", "http://localhost:11434/v1"),
        api_key=os.getenv("OPENAI_API_KEY", "ollama"),
        mcp_server_config={
            "mcp-solver": {
                "command": os.getenv("MCP_SOLVER_COMMAND"),
                "args": mcp_args,
                "transport": os.getenv("MCP_SOLVER_TRANSPORT"),
            }
        },
        max_iterations=max_iterations,
    )

    # Read problem description
    problem = read_text_file(args.problem_file)

    # Solve the problem (with optional prompt overrides)
    result = await solve_asp_problem(problem, config, solver_prompt=solver_prompt, validator_prompt=validator_prompt)

    # Display results
    print("=== ASP Multi-Agent System Results ===")
    print(f"\nSuccess: {result['success']}")
    print(f"Iterations: {result['iterations']}")
    print(f"\nFinal ASP Code:\n{result['asp_code']}")
    print(f"\nFinal Message: {result['message']}")


def cli() -> None:
    """Console script entrypoint"""
    asyncio.run(main())
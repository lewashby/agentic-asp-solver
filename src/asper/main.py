import os
import asyncio
import argparse
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

from asper.utils import setup_logger
from asper.config import ASPSystemConfig
from asper.graph import solve_asp_problem
from asper.utils import export_solution, read_text_file


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

    # Validate CLI parameters and resolve prompts
    if not args.problem_file or not args.problem_file.exists():
        print(f"Error: Problem file not found: {args.problem_file}")
        raise SystemExit(2)
    if args.solver_prompt and not args.solver_prompt.exists():
        print(f"Error: Solver prompt file not found: {args.solver_prompt}")
        raise SystemExit(2)
    if args.validator_prompt and not args.validator_prompt.exists():
        print(f"Error: Validator prompt file not found: {args.validator_prompt}")
        raise SystemExit(2)
    
    export_solution_path = Path(os.getenv("EXPORT_PATH", "results"))
    logger = setup_logger(args.problem_file, os.getenv("LOG_LEVEL", "INFO").upper(), export_path=export_solution_path)


    # Configure system
    model_name = args.model or os.getenv("MODEL_NAME")
    max_iterations = args.max_iterations or int(os.getenv("MAX_ITERATIONS", "5"))

    mcp_args_env = os.getenv("MCP_SOLVER_ARGS", "")
    mcp_args = [arg for arg in mcp_args_env.split(',') if arg] if mcp_args_env else []

    config = ASPSystemConfig(
        model_name=model_name,  # or your preferred Ollama model
        base_url=os.getenv("OPENAI_BASE_URL", "http://localhost:11434/v1"),
        api_key=os.getenv("OPENAI_API_KEY", "ollama"),
        solver_prompt_file=args.solver_prompt,
        validator_prompt_file=args.validator_prompt,
        mcp_server_config={
            "mcp-solver": {
                "command": os.getenv("MCP_SOLVER_COMMAND"),
                "args": mcp_args,
                "transport": os.getenv("MCP_SOLVER_TRANSPORT"),
            }
        },
        max_iterations=max_iterations,
    )

    # Solve the problem (with optional prompt overrides)
    try:
        result = await solve_asp_problem(args.problem_file, config)

        if result and isinstance(result, dict):
            file = export_solution(
                args.problem_file, 
                {"success": result.get("success", False), 
                "iterations": result.get("iterations", 0), 
                "asp_code": result.get("asp_code", ""), 
                "message": result.get("message", ""),
                "error_code": result.get("error_code", "UNKNOWN"),
                "statistics": result.get("statistics", {})
                },
                export_path=export_solution_path
            )
            logger.info(f"Results saved to file: {file}")
            total_tokens = result["statistics"]["total_tokens"] if result.get("statistics", None) else 0
            tool_calls = result["statistics"]["tool_calls"] if result.get("statistics", {}) else 0
            logger.info(f"Usage: Total tokens - {total_tokens}   Tool calls - {tool_calls}")
        logger.info(f"Logs save to file: {export_solution_path / Path(args.problem_file).with_suffix(".log")}")
    except:
        logger.error(f"Error solving problem: {args.problem_file}")

def cli() -> None:
    """Console script entrypoint"""
    asyncio.run(main())
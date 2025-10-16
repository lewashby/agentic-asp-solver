import asyncio
import argparse
import os
from pathlib import Path
from typing import Iterable

from dotenv import load_dotenv

from asper.config import ASPSystemConfig
from asper.graph import solve_asp_problem
from asper.utils import export_solution, read_text_file, setup_logger


load_dotenv()


def find_problem_files(root: Path, years: list[str] | None = None) -> list[Path]:
    base = root
    if years:
        candidates: Iterable[Path] = [base / f"lpcp-{y}" for y in years]
    else:
        candidates = [p for p in base.iterdir() if p.is_dir() and p.name.startswith("lpcp-")]

    problem_files: list[Path] = []
    for year_dir in candidates:
        if not year_dir.exists() or not year_dir.is_dir():
            continue
        for f in sorted(year_dir.glob("problem-*.md")):
            if f.name in {"problem-1.md", "problem-2.md"}:
                problem_files.append(f)
    return problem_files


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run asper over all LPCP problems")
    parser.add_argument(
        "--root",
        type=Path,
        default=Path("lpcp_problems"),
        help="Root folder containing lpcp-YYYY subfolders",
    )
    parser.add_argument(
        "--years",
        type=str,
        default="",
        help="Comma-separated years to include (e.g., 2022,2023). Empty = all",
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


async def run_for_file(problem_file: Path, config: ASPSystemConfig, solver_prompt: str | None, validator_prompt: str | None) -> None:
    setup_logger(problem_file, os.getenv("LOG_LEVEL", "INFO").upper())
    problem = read_text_file(problem_file)
    if not problem.strip():
        print(f"Skipped empty file: {problem_file}")
        return
    result = await solve_asp_problem(problem, config, solver_prompt=solver_prompt, validator_prompt=validator_prompt)
    export_solution(
        problem_file,
        {
            "success": result.get("success", False),
            "iterations": result.get("iterations", 0),
            "asp_code": result.get("asp_code", ""),
            "message": result.get("message", ""),
            "error_code": result.get("error_code", "UNKNOWN"),
        },
    )


async def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()

    if not args.root.exists() or not args.root.is_dir():
        print(f"Error: Root folder not found: {args.root}")
        raise SystemExit(2)
    if args.solver_prompt and not args.solver_prompt.exists():
        print(f"Error: Solver prompt file not found: {args.solver_prompt}")
        raise SystemExit(2)
    if args.validator_prompt and not args.validator_prompt.exists():
        print(f"Error: Validator prompt file not found: {args.validator_prompt}")
        raise SystemExit(2)

    solver_prompt = read_text_file(args.solver_prompt) if args.solver_prompt else None
    validator_prompt = read_text_file(args.validator_prompt) if args.validator_prompt else None

    model_name = args.model or os.getenv("MODEL_NAME")
    max_iterations = args.max_iterations or int(os.getenv("MAX_ITERATIONS", "5"))

    mcp_args_env = os.getenv("MCP_SOLVER_ARGS", "")
    mcp_args = [arg for arg in mcp_args_env.split(',') if arg] if mcp_args_env else []

    config = ASPSystemConfig(
        model_name=model_name,
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

    years = [y.strip() for y in args.years.split(",") if y.strip()] if args.years else None
    files = find_problem_files(args.root, years)
    if not files:
        print("No problem files found.")
        return

    for pf in files:
        print(f"Running asper for {pf} ...")
        try:
            await run_for_file(pf, config, solver_prompt, validator_prompt)
        except Exception as e:
            print(f"Failed for {pf}: {e}")


def cli() -> None:
    asyncio.run(main())



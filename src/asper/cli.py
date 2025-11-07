"""CLI argument parsing for ASP solver."""

import argparse
from pathlib import Path


def build_cli_parser() -> argparse.ArgumentParser:
    """Build CLI argument parser for main asper command.

    Returns:
        Configured ArgumentParser instance
    """
    parser = argparse.ArgumentParser(
        description="Agentic ASP solver CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  asper problem.md
  asper problem.md --model gpt-oss:20b
  asper problem.md --solver-prompt custom_solver.md --max-iterations 10
        """,
    )

    # Required arguments
    parser.add_argument(
        "problem_file",
        type=Path,
        help="Path to a text/markdown file with the problem description",
    )

    # Optional arguments
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
        help="LLM model name (overrides MODEL_NAME env variable)",
    )

    parser.add_argument(
        "--chat-model-type",
        type=str,
        choices=["openai", "ollama"],
        default=None,
        help="Chat model type: 'openai' or 'ollama' (default: from env or 'ollama')",
    )

    parser.add_argument(
        "--max-iterations",
        type=int,
        default=None,
        help="Maximum number of solver/validator iterations (default: 5)",
    )

    parser.add_argument(
        "--reasoning",
        type=str,
        default=None,
        help="Reasoning level for reasoning models: 'low', 'medium', 'high', 'true', or 'false' (default: from env or 'low')",
    )

    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Logging level (default: INFO)",
    )

    parser.add_argument(
        "--export-path",
        type=Path,
        default=None,
        help="Path to export results (default: results/)",
    )

    return parser


def build_batch_cli_parser() -> argparse.ArgumentParser:
    """Build CLI argument parser for batch processing command.

    Returns:
        Configured ArgumentParser for batch operations
    """
    parser = argparse.ArgumentParser(
        description="Run asper over all LPCP problems",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  asper-batch
  asper-batch --years 2022,2023
  asper-batch --root my_problems/ --model gpt-oss:20b
        """,
    )

    parser.add_argument(
        "--root",
        type=Path,
        default=Path("lpcp_problems"),
        help="Root folder containing lpcp-YYYY subfolders (default: lpcp_problems)",
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
        help="LLM model name (overrides MODEL_NAME env variable)",
    )

    parser.add_argument(
        "--chat-model-type",
        type=str,
        choices=["openai", "ollama"],
        default=None,
        help="Chat model type: 'openai' or 'ollama' (default: from env or 'ollama')",
    )

    parser.add_argument(
        "--max-iterations",
        type=int,
        default=None,
        help="Maximum number of solver/validator iterations (default: 5)",
    )

    parser.add_argument(
        "--reasoning",
        type=str,
        default=None,
        help="Reasoning level for reasoning models: 'low', 'medium', 'high', 'true', or 'false' (default: from env or 'low')",
    )

    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Logging level (default: INFO)",
    )

    return parser


def validate_cli_args(args: argparse.Namespace) -> str | None:
    """Validate CLI arguments and return error message if invalid.

    Args:
        args: Parsed command-line arguments

    Returns:
        Error message string if validation fails, None if valid
    """
    # Check problem file exists
    if hasattr(args, "problem_file"):
        if not args.problem_file.exists():
            return f"Problem file not found: {args.problem_file}"

    # Check root directory for batch mode
    if hasattr(args, "root"):
        if not args.root.exists() or not args.root.is_dir():
            return f"Root folder not found or not a directory: {args.root}"

    # Check solver prompt if provided
    if args.solver_prompt and not args.solver_prompt.exists():
        return f"Solver prompt file not found: {args.solver_prompt}"

    # Check validator prompt if provide
    if args.validator_prompt and not args.validator_prompt.exists():
        return f"Validator prompt file not found: {args.validator_prompt}"

    # Validate max iterations
    if hasattr(args, "max_iterations") and args.max_iterations is not None:
        if args.max_iterations < 1:
            return "Max iterations must be at least 1"

    return None

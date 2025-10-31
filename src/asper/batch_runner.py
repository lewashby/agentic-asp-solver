"""Batch runner for processing multiple LPCP problems."""

import asyncio
import os
from pathlib import Path
from typing import Iterable

from dotenv import load_dotenv

from asper.cli import build_batch_cli_parser, validate_cli_args
from asper.config import ASPSystemConfig
from asper.runner import BatchRunner
from asper.utils import export_solution, reset_logger, setup_logger

load_dotenv()


def find_problem_files(root: Path, years: list[str] | None = None) -> list[Path]:
    """Find all problem files in LPCP directory structure.

    Args:
        root: Root directory containing lpcp-YYYY folders
        years: Optional list of years to filter (e.g., ["2022", "2023"])

    Returns:
        List of problem file paths found
    """
    base = root

    # Determine which year directories to search
    if years:
        candidates: Iterable[Path] = [base / f"lpcp-{y}" for y in years]
    else:
        candidates = [
            p for p in base.iterdir() if p.is_dir() and p.name.startswith("lpcp-")
        ]

    problem_files: list[Path] = []

    for year_dir in candidates:
        if not year_dir.exists() or not year_dir.is_dir():
            continue

        # Find all problem-*.md files in this year
        for f in sorted(year_dir.glob("problem-*.md")):
            problem_files.append(f)

    return problem_files


async def run_for_file(
    problem_file: Path, config: ASPSystemConfig, export_path: Path
) -> None:
    """Run solver for a single file and export results.

    Args:
        problem_file: Path to problem file
        config: System configuration
        export_path: Path to export results
    """
    # Setup logger for this specific file
    logger = setup_logger(
        problem_file, os.getenv("LOG_LEVEL", "INFO").upper(), export_path=export_path
    )

    try:
        # Create runner and solve
        runner = BatchRunner(config, logger)
        result = await runner.runner.solve(problem_file)

        # Export result
        if result:
            output_files = export_solution(
                problem_file, result.to_dict(), export_path=export_path
            )
            logger.info(f"Results saved to: {output_files['json']}")
            if "lp" in output_files:
                logger.info(f"ASP Code saved to: {output_files['lp']}")

            # Log statistics
            if result.statistics:
                logger.info(
                    f"Usage: Total tokens={result.statistics.total_tokens}, "
                    f"Tool calls={result.statistics.tool_calls}"
                )

            # Log outcome
            if result.success:
                logger.info(f"Solved in {result.iterations} iterations")
            else:
                logger.warning(f"Failed: {result.error_code}")
        else:
            logger.error(f"No result returned for {problem_file}")

    except Exception as e:
        logger.error(f"Error processing {problem_file}: {e}")

    finally:
        # Clean up logger handlers
        reset_logger()


async def main() -> None:
    """Execute the main async entry point for batch processing."""
    # Parse arguments
    parser = build_batch_cli_parser()
    args = parser.parse_args()

    # Validate arguments
    validation_error = validate_cli_args(args)
    if validation_error:
        parser.error(validation_error)
        return

    # Setup export path
    export_path = Path(os.getenv("EXPORT_PATH", "results"))

    # Build configuration
    config = ASPSystemConfig.from_env(
        model_name=args.model,
        max_iterations=args.max_iterations,
        solver_prompt_file=args.solver_prompt,
        validator_prompt_file=args.validator_prompt,
        chat_model_type=args.chat_model_type,
        reasoning=args.reasoning,
    )

    # Parse years filter
    years = None
    if args.years:
        years = [y.strip() for y in args.years.split(",") if y.strip()]

    # Find problem files
    problem_files = find_problem_files(args.root, years)

    if not problem_files:
        print("No problem files found.")
        print(f"Searched in: {args.root}")
        if years:
            print(f"Filtered for years: {', '.join(years)}")
        return

    print(f"Found {len(problem_files)} problem files")
    print(
        f"Configuration: model={config.model_name}, max_iterations={config.max_iterations}"
    )
    print("-" * 60)

    # Process each file
    successful = 0
    failed = 0

    for i, problem_file in enumerate(problem_files, 1):
        print(f"\n[{i}/{len(problem_files)}] Processing: {problem_file}")

        try:
            await run_for_file(problem_file, config, export_path)
            successful += 1
        except Exception as e:
            print(f"Error: {e}")
            failed += 1

    # Print summary
    print("\n" + "=" * 60)
    print("BATCH PROCESSING COMPLETE")
    print("=" * 60)
    print(f"Total: {len(problem_files)}")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")
    print(f"Results saved to: {export_path}/")


def cli() -> None:
    """Execute the synchronous CLI entry point for batch processing."""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    except SystemExit:
        raise
    except Exception as e:
        print(f"Fatal error: {e}")
        raise SystemExit(1)


if __name__ == "__main__":
    cli()

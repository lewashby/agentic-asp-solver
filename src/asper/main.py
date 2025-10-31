"""Main entry point for Agentic ASP solver CLI."""

import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv

from asper.cli import build_cli_parser, validate_cli_args
from asper.config import ASPSystemConfig
from asper.runner import ASPRunner
from asper.utils import export_solution, setup_logger

# Load environment variables first
load_dotenv()


async def main() -> None:
    """Run the main async entry point for the CLI."""
    # Parse arguments
    parser = build_cli_parser()
    args = parser.parse_args()

    # Validate arguments
    validation_error = validate_cli_args(args)
    if validation_error:
        parser.error(validation_error)
        return

    # Setup export path
    export_path = args.export_path or Path(os.getenv("EXPORT_PATH", "results"))

    # Setup logging
    logger = setup_logger(args.problem_file, args.log_level, export_path=export_path)

    try:
        # Build configuration from environment and CLI args
        try:
            config = ASPSystemConfig.from_env(
                model_name=args.model,
                max_iterations=args.max_iterations,
                solver_prompt_file=args.solver_prompt,
                validator_prompt_file=args.validator_prompt,
                chat_model_type=args.chat_model_type,
                reasoning=args.reasoning,
            )
        except ValueError as e:
            logger.error(f"Configuration error: {e}")
            print(f"\nConfiguration Error:\n{e}\n")
            print(
                "Please check your .env file and ensure all required variables are set."
            )
            print("See .env.example for reference.")
            return

        logger.info(
            f"Configuration: model={config.model_name}, max_iterations={config.max_iterations}"
        )

        # Create and run solver
        try:
            runner = ASPRunner(config, logger)
        except Exception as e:
            logger.error(f"Failed to initialize runner: {e}")
            return

        result = await runner.solve(args.problem_file)

        # Export results
        if result:
            output_files = export_solution(
                args.problem_file, result.to_dict(), export_path=export_path
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

            # Log final status
            if result.success:
                logger.info(
                    f"Problem solved successfully in {result.iterations} iterations"
                )
            else:
                logger.error(f"Failed to solve problem: {result.error_code}")
                logger.error(f"Message: {result.message}")

        # Log file locations
        log_file = export_path / args.problem_file.with_suffix(".log")
        logger.info(f"Logs saved to: {log_file}")

    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        raise SystemExit(1)


def cli() -> None:
    """Execute the synchronous CLI entry point."""
    try:
        asyncio.run(main())
    except SystemExit:
        raise
    except Exception as e:
        print(f"Fatal error: {e}")
        raise SystemExit(1)


if __name__ == "__main__":
    cli()

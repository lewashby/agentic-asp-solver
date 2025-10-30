"""Main runner for ASP problem solving."""

import logging
from pathlib import Path

from langchain_core.messages import HumanMessage
from langgraph.graph.state import CompiledStateGraph

from asper.config import ASPSystemConfig
from asper.exceptions import ASPException, FileError, classify_exception
from asper.llm import build_llm
from asper.mcp_client import MCPClientManager
from asper.prompts import PromptManager
from asper.result import SolutionResult
from asper.state import ASPState


class ASPRunner:
    """High-level runner for ASP problem solving.

    This class orchestrates the entire solving process including:
    - Loading problem files
    - Creating the agent graph
    - Managing execution
    - Handling errors
    - Returning structured results
    """

    def __init__(self, config: ASPSystemConfig, logger: logging.Logger | None = None):
        """Initialize the ASP runner.

        Args:
            config: System configuration
            logger: Optional logger instance (creates one if not provided)

        Raises:
            MCPError: If MCP configuration is invalid
        """
        self.config = config
        self.logger = logger or logging.getLogger(__name__)

        try:
            self.mcp_manager = MCPClientManager(config)
            self.logger.info("MCP client manager initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize MCP client manager: {e}")
            raise

    async def solve(self, problem_file: Path) -> SolutionResult:
        """Solve an ASP problem from a file.

        This is the main entry point for solving a single problem.

        Args:
            problem_file: Path to file containing problem description

        Returns:
            SolutionResult with outcome and details
        """
        try:
            self.logger.info(f"Starting Agentic ASP solver for: {problem_file}")

            # Load problem
            problem = self._load_problem(problem_file)
            self.logger.info("Problem description loaded successfully")

            # Create initial state
            state = self._create_initial_state(problem)

            # Run with MCP session active for the entire solving process
            async with self.mcp_manager.get_session() as session:
                # Load tools from the active session
                from langchain_mcp_adapters.tools import load_mcp_tools

                tools = await load_mcp_tools(session)
                self.logger.info(f"Loaded {len(tools)} MCP tools")

                # Create the agent graph
                app = await self._create_app_with_tools(tools)
                self.logger.info("Agent graph created successfully")

                # Run the graph (session stays open during execution)
                final_state = await self._run_graph(app, state)

            # Create result from final state
            result = SolutionResult.from_state(
                final_state, success=final_state["is_validated"]
            )

            # Add completion message if max iterations reached
            if not result.success and result.iterations >= self.config.max_iterations:
                result.message = (
                    f"Max iterations ({self.config.max_iterations}) reached. "
                    "Best attempt returned."
                )
                result.error_code = "MAX_ITER"

            self.logger.info(f"Solving completed: {result.get_summary()}")
            return result

        except ASPException as e:
            self.logger.error(f"System error: {e.code} - {e.message}")
            return SolutionResult.from_exception(e)


    def _load_problem(self, path: Path) -> str:
        """Load problem description from file.

        Args:
            path: Path to problem file

        Returns:
            Problem description as string

        Raises:
            FileError: If file doesn't exist or is empty
        """
        if not path.exists():
            raise FileError(f"Problem file not found: {path}")

        try:
            content = path.read_text(encoding="utf-8")
        except Exception as e:
            raise FileError(f"Failed to read problem file: {e}")

        if not content.strip():
            raise FileError(f"Empty problem file: {path}")

        return content

    async def _create_app_with_tools(self, tools):
        """Create the agent graph with provided tools.

        Args:
            tools: List of loaded MCP tools

        Returns:
            Compiled LangGraph application
        """
        from asper.graph import create_asp_system

        # Build LLM
        llm = build_llm(self.config)

        # Load prompts
        solver_prompt = PromptManager.get_solver_prompt(self.config.solver_prompt_file)
        if self.config.solver_prompt_file:
            self.logger.info(
                f"Loaded Solver system prompt: {self.config.solver_prompt_file}"
            )
        else:
            self.logger.info("Loaded default Solver system prompt")
        validator_prompt = PromptManager.get_validator_prompt(
            self.config.validator_prompt_file
        )
        if self.config.validator_prompt_file:
            self.logger.info(
                f"Loaded Validator system prompt: {self.config.validator_prompt_file}"
            )
        else:
            self.logger.info("Loaded default Validator system prompt")

        # Create and return the graph
        return await create_asp_system(
            llm=llm,
            tools=tools,
            solver_prompt=solver_prompt,
            validator_prompt=validator_prompt,
        )

    def _create_initial_state(self, problem: str) -> ASPState:
        """Create initial state for graph execution.

        Args:
            problem: Problem description string

        Returns:
            Initial ASPState
        """
        initial_message = HumanMessage(
            content=(
                "Please read carefully and solve the following problem "
                "using Answer Set Programming (ASP)\n\n"
                f"{problem}"
            )
        )

        return ASPState(
            messages=[initial_message],
            problem_description=problem,
            max_iterations=self.config.max_iterations,
        )

    async def _run_graph(self, app: CompiledStateGraph, state: ASPState) -> dict:
        """Execute the agent graph.

        Args:
            app: Compiled LangGraph application
            state: Initial state

        Returns:
            Final state dictionary

        Raises:
            GraphExecutionError: If graph execution fails
        """
        from asper.exceptions import GraphExecutionError

        try:
            self.logger.info("Starting graph execution")

            final_state = await app.ainvoke(
                state.model_dump(),
                config={
                    "configurable": {"thread_id": "1"},
                    "recursion_limit": 50,
                },
            )

            self.logger.info(
                f"Graph execution completed after {final_state['iteration_count']} iterations"
            )

            return final_state

        except Exception as e:

            # Try to classify the error
            classified = classify_exception(e)

            if isinstance(classified, ASPException):
                self.logger.error(f"Graph execution failed [{classified.code}]: {classified.message}")
                raise classified
            
            if self.logger.isEnabledFor(logging.DEBUG):
                self.logger.debug("Full traceback:", exc_info=True)

            raise GraphExecutionError(f"Execution failed: {e}")


class BatchRunner:
    """Runner for batch processing multiple problems.

    This extends the basic ASPRunner to handle multiple files
    and provide progress tracking.
    """

    def __init__(self, config: ASPSystemConfig, logger: logging.Logger | None = None):
        """Initialize batch runner.

        Args:
            config: System configuration
            logger: Optional logger instance
        """
        self.config = config
        self.logger = logger or logging.getLogger(__name__)
        self.runner = ASPRunner(config, logger)

    async def solve_all(self, problem_files: list[Path]) -> dict[Path, SolutionResult]:
        """Solve multiple problems sequentially.

        Args:
            problem_files: List of problem file paths

        Returns:
            Dictionary mapping file paths to results
        """
        results = {}

        total = len(problem_files)
        self.logger.info(f"Starting batch processing of {total} problems")

        for i, problem_file in enumerate(problem_files, 1):
            self.logger.info(f"Processing {i}/{total}: {problem_file}")

            try:
                result = await self.runner.solve(problem_file)
                results[problem_file] = result

                if result.success:
                    self.logger.info(f"✓ Success after {result.iterations} iterations")
                else:
                    self.logger.warning(f"✗ Failed: {result.error_code}")

            except Exception as e:
                self.logger.error(f"✗ Error processing {problem_file}: {e}")
                results[problem_file] = SolutionResult.from_exception(e)

        # Summary
        successful = sum(1 for r in results.values() if r.success)
        self.logger.info(f"Batch complete: {successful}/{total} successful")

        return results

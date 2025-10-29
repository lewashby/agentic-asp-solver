"""Result structures for Agentic ASP solver system."""

from dataclasses import dataclass, field


@dataclass
class UsageStatistics:
    """Statistics about token usage and tool calls."""

    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    tool_calls: int = 0

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
            "tool_calls": self.tool_calls,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "UsageStatistics":
        """Create from dictionary."""
        return cls(
            input_tokens=data.get("input_tokens", 0),
            output_tokens=data.get("output_tokens", 0),
            total_tokens=data.get("total_tokens", 0),
            tool_calls=data.get("tool_calls", 0),
        )


@dataclass
class SolutionResult:
    """Structured result from Agentic ASP solver execution.

    This encapsulates all information about a solver run including
    success status, generated code, iterations, and diagnostics.
    """

    success: bool
    asp_code: str
    iterations: int
    message: str
    error_code: str | None = None
    statistics: UsageStatistics | None = None
    messages_history: list = field(default_factory=list)
    validation_history: list = field(default_factory=list)
    answer_set: str = ""

    def to_dict(self) -> dict:
        """Convert to dictionary for export/serialization.

        Returns:
            Dictionary representation suitable for JSON export
        """
        return {
            "success": self.success,
            "iterations": self.iterations,
            "asp_code": self.asp_code,
            "message": self.message,
            "error_code": self.error_code or "UNKNOWN" if not self.success else None,
            "statistics": self.statistics.to_dict() if self.statistics else {},
            "answer_set": self.answer_set,
        }

    def to_full_dict(self) -> dict:
        """Convert to full dictionary including histories.

        Returns:
            Complete dictionary with all fields including message histories
        """
        result = self.to_dict()
        result.update(
            {
                "messages_history": self.messages_history,
                "validation_history": self.validation_history,
            }
        )
        return result

    @classmethod
    def from_state(cls, state: dict, success: bool) -> "SolutionResult":
        """Create result from graph state.

        Args:
            state: The final state dictionary from graph execution
            success: Override success status (default: use state's is_validated)

        Returns:
            SolutionResult constructed from state
        """
        if success is None:
            success = state.get("is_validated", False)

        stats_dict = state.get("statistics", {})
        statistics = UsageStatistics.from_dict(stats_dict) if stats_dict else None

        return cls(
            success=success,
            asp_code=state.get("asp_code", ""),
            iterations=state.get("iteration_count", 0),
            message=state.get("last_feedback", ""),
            statistics=statistics,
            messages_history=state.get("messages", []),
            validation_history=state.get("validation_history", []),
            answer_set=state.get("answer_set", ""),
        )

    @classmethod
    def error(cls, code: str, message: str) -> "SolutionResult":
        """Create an error result.

        Args:
            code: Error code
            message: Error message

        Returns:
            SolutionResult representing an error state
        """
        return cls(
            success=False,
            asp_code="",
            iterations=0,
            message=message,
            error_code=code,
            statistics=UsageStatistics(),
        )

    @classmethod
    def from_exception(cls, exception: Exception) -> "SolutionResult":
        """Create error result from an exception.

        Args:
            exception: The exception that occurred

        Returns:
            SolutionResult representing the error
        """
        from asper.exceptions import ASPException, classify_exception

        if isinstance(exception, ASPException):
            return cls.error(exception.code, exception.message)

        classified = classify_exception(exception)
        return cls.error(classified.code, classified.message)

    def is_success(self) -> bool:
        """Check if the result represents a successful execution.

        Returns:
            True if successful, False otherwise
        """
        return self.success

    def has_code(self) -> bool:
        """Check if result contains ASP code.

        Returns:
            True if asp_code is non-empty
        """
        return bool(self.asp_code.strip())

    def get_summary(self) -> str:
        """Get a human-readable summary of the result.

        Returns:
            Summary string
        """
        if self.success:
            return f"Success after {self.iterations} iterations"
        else:
            return f"Failed: {self.error_code or 'UNKNOWN'} - {self.message}"

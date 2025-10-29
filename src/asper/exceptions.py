"""Custom exceptions for Agentic ASP solver system."""


class ASPException(Exception):
    """Base exception for Agentic ASP system.

    All custom exceptions inherit from this class and include
    a code for programmatic error handling.
    """

    def __init__(self, code: str, message: str):
        """Initialize exception.

        Args:
            code: Error code for programmatic handling
            message: Human-readable error message
        """
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")

    def to_dict(self) -> dict:
        """Convert exception to dictionary format.

        Returns:
            Dictionary with code and message
        """
        return {"error_code": self.code, "message": self.message}


class FileError(ASPException):
    """Exception for file-related errors."""

    def __init__(self, message: str):
        """Initialize a FileError exception with a descriptive message.

        Args:
            message: A human-readable description of the file-related error.
        """
        super().__init__("FILE_ERROR", message)


class MCPError(ASPException):
    """Exception for MCP server/client errors."""

    def __init__(self, message: str):
        """Initialize an MCPError exception with a descriptive message.

        Args:
            message: A human-readable description of the MCP-related error.
        """
        super().__init__("MCP_ERROR", message)


class ModelNotFoundError(ASPException):
    """Exception when LLM model is not found."""

    def __init__(self, message: str):
        """Initialize a ModelNotFoundError exception with a descriptive message.

        Args:
            message: A human-readable description of the model not found error.
        """
        super().__init__("MODEL_NOT_FOUND", message)


class AuthError(ASPException):
    """Exception for authentication/authorization errors."""

    def __init__(self, message: str):
        """Initialize an AuthError exception with a descriptive message.

        Args:
            message: A human-readable description of the authentication error.
        """
        super().__init__("AUTH", message)


class GraphExecutionError(ASPException):
    """Exception during graph execution."""

    def __init__(self, message: str):
        """Initialize a GraphExecutionError exception with a descriptive message.

        Args:
            message: A human-readable description of the graph execution error.
        """
        super().__init__("GRAPH_ERROR", message)


class ValidationError(ASPException):
    """Exception during validation phase."""

    def __init__(self, message: str):
        """Initialize a ValidationError exception with a descriptive message.

        Args:
            message: A human-readable description of the validation error.
        """
        super().__init__("VALIDATION_ERROR", message)


class TimeoutError(ASPException):
    """Exception when operation times out."""

    def __init__(self, message: str):
        """Initialize a TimeoutError exception with a descriptive message.

        Args:
            message: A human-readable description of the timeout error.
        """
        super().__init__("TIMEOUT", message)


def classify_exception(error: Exception) -> ASPException:
    """Classify a generic exception into an ASPException.

    Args:
        error: The exception to classify

    Returns:
        Appropriate ASPException subclass
    """
    if isinstance(error, ASPException):
        return error

    message = str(error).lower()

    # Check for authentication errors
    if any(
        keyword in message
        for keyword in ["unauthorized", "invalid api key", "401", "403"]
    ):
        return AuthError(str(error))

    # Check for model not found errors
    if ("404" in message or "not found" in message) and "model" in message:
        return ModelNotFoundError(str(error))

    # Check for file errors
    if any(
        keyword in message
        for keyword in ["file not found", "no such file", "cannot open"]
    ):
        return FileError(str(error))

    # Check for MCP errors
    if "mcp" in message or "server" in message:
        return MCPError(str(error))

    # Default to generic ASPException
    return ASPException("UNKNOWN", str(error))


def _root_cause_message(error: BaseException) -> str:
    """Extract a concise root-cause message from nested exceptions.

    Args:
        error: The exception to analyze

    Returns:
        String representation of the root cause
    """
    try:
        # ExceptionGroup handling
        exceptions_attr = getattr(error, "exceptions", None)
        if isinstance(exceptions_attr, list) and exceptions_attr:
            first = exceptions_attr[0]
            if isinstance(first, BaseException):
                return _root_cause_message(first)

        # Prefer explicit cause
        cause: BaseException | None = getattr(error, "__cause__", None)
        if cause is not None:
            return _root_cause_message(cause)

        # Fallback to context if present
        context: BaseException | None = getattr(error, "__context__", None)
        if context is not None:
            return _root_cause_message(context)

        return str(error)
    except Exception:
        return str(error)

def _root_cause_message(error: Exception) -> str:
    """Extract a concise root-cause message from nested ExceptionGroup/TaskGroup/cause/context."""
    try:
        # ExceptionGroup handling
        if hasattr(error, "exceptions") and isinstance(getattr(error, "exceptions"), list):
            exceptions = getattr(error, "exceptions")
            if exceptions:
                return _root_cause_message(exceptions[0])
        # Prefer explicit cause
        if getattr(error, "__cause__", None):
            return _root_cause_message(error.__cause__)
        # Fallback to context if present
        if getattr(error, "__context__", None):
            return _root_cause_message(error.__context__)
        return str(error)
    except Exception:
        return str(error)
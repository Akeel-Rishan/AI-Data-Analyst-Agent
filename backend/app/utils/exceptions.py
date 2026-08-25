"""Custom exceptions raised by the data analyst application."""


class DataAnalystException(Exception):
    """Base exception for expected application errors."""

    def __init__(self, message: str, status_code: int = 500) -> None:
        """Initialize the exception with a public message and HTTP status."""
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class FileValidationError(DataAnalystException):
    """Indicate that an uploaded file did not pass validation."""

    def __init__(self, message: str) -> None:
        """Initialize a file validation error."""
        super().__init__(message, status_code=400)


class DatasetNotFoundError(DataAnalystException):
    """Indicate that the requested dataset does not exist."""

    def __init__(self, message: str) -> None:
        """Initialize a missing dataset error."""
        super().__init__(message, status_code=404)


class AnalysisError(DataAnalystException):
    """Indicate that data analysis failed."""

    def __init__(self, message: str) -> None:
        """Initialize an analysis error."""
        super().__init__(message, status_code=500)


class LLMError(DataAnalystException):
    """Indicate that an LLM provider request failed."""

    def __init__(self, message: str) -> None:
        """Initialize an LLM service error."""
        super().__init__(message, status_code=503)


class ExecutionError(DataAnalystException):
    """Indicate that generated code execution failed."""

    def __init__(self, message: str) -> None:
        """Initialize a code execution error."""
        super().__init__(message, status_code=500)

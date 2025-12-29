"""Custom error classes."""

from fastapi import HTTPException, status


class AIEOError(HTTPException):
    """Base AIEO error."""

    pass


class ContentTooLargeError(AIEOError):
    """Content exceeds size limits."""

    def __init__(self, message: str):
        super().__init__(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail={
                "error": {
                    "code": "CONTENT_TOO_LARGE",
                    "message": message,
                }
            },
        )


class FetchFailedError(AIEOError):
    """Failed to fetch URL content."""

    def __init__(self, message: str):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": {
                    "code": "FETCH_FAILED",
                    "message": message,
                }
            },
        )


class InvalidRequestError(AIEOError):
    """Invalid request parameters."""

    def __init__(self, message: str):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "code": "INVALID_REQUEST",
                    "message": message,
                }
            },
        )

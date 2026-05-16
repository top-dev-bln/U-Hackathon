from __future__ import annotations

from typing import Any


class AppError(Exception):
    def __init__(self, message: str, status_code: int = 400, details: Any | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.details = details


class BadRequestError(AppError):
    def __init__(self, message: str, details: Any | None = None) -> None:
        super().__init__(message=message, status_code=400, details=details)


class InternalServerError(AppError):
    def __init__(self, message: str, details: Any | None = None) -> None:
        super().__init__(message=message, status_code=500, details=details)


class NotFoundError(AppError):
    def __init__(self, message: str, details: Any | None = None) -> None:
        super().__init__(message=message, status_code=404, details=details)

"""Errors raised by services. app/main.py turns them into HTTP responses,
so services stay independent of FastAPI."""


class ServiceError(Exception):
    status_code = 400

    def __init__(self, detail: str):
        super().__init__(detail)
        self.detail = detail


class NotFound(ServiceError):
    status_code = 404


class Conflict(ServiceError):
    status_code = 409


class Unauthorized(ServiceError):
    """Not logged in, or wrong credentials."""

    status_code = 401


class Forbidden(ServiceError):
    """Logged in, but not allowed."""

    status_code = 403


class TooManyAttempts(ServiceError):
    status_code = 429

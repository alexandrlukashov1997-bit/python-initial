class AppError(Exception):
    status_code = 500

    def __init__(self, message: str = "Internal server error") -> None:
        self.message = message
        super().__init__(message)


class NotFound(AppError):
    status_code = 404

    def __init__(self, message: str = "Not found") -> None:
        super().__init__(message)


class Conflict(AppError):
    status_code = 409

    def __init__(self, message: str = "Conflict") -> None:
        super().__init__(message)


class Unauthorized(AppError):
    status_code = 401

    def __init__(self, message: str = "Unauthorized") -> None:
        super().__init__(message)


class BadRequest(AppError):
    status_code = 400

    def __init__(self, message: str = "Bad request") -> None:
        super().__init__(message)


class Forbidden(AppError):
    status_code = 403

    def __init__(self, message: str = "Forbidden") -> None:
        super().__init__(message)

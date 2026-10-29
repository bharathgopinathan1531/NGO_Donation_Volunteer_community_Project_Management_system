class AppException(Exception):
    """Base class for all domain errors; mapped to HTTP responses centrally."""

    status_code = 400
    code = "bad_request"

    def __init__(self, detail: str = "", *, extra: dict | None = None):
        self.detail = detail or self.__class__.__name__
        self.extra = extra or {}
        super().__init__(self.detail)


class BadRequestError(AppException):
    status_code = 400
    code = "bad_request"


class UnauthorizedError(AppException):
    status_code = 401
    code = "unauthorized"


class ForbiddenError(AppException):
    status_code = 403
    code = "forbidden"


class NotFoundError(AppException):
    status_code = 404
    code = "not_found"


class ConflictError(AppException):
    status_code = 409
    code = "conflict"


class BusinessRuleError(AppException):
    """A request that is well-formed but violates a business rule."""

    status_code = 422
    code = "business_rule_violation"

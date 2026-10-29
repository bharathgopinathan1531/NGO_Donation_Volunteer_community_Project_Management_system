import logging

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.exceptions import AppException

logger = logging.getLogger("app.errors")


def _body(code: str, detail, request: Request, **extra) -> dict:
    return {
        "error": {"code": code, "detail": detail, "request_id": getattr(request.state, "request_id", None), **extra}
    }


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        headers = {"WWW-Authenticate": "Bearer"} if exc.status_code == 401 else None
        return JSONResponse(
            status_code=exc.status_code, content=_body(exc.code, exc.detail, request, **exc.extra), headers=headers
        )

    @app.exception_handler(RequestValidationError)
    async def validation_handler(request: Request, exc: RequestValidationError):
        errors = [
            {"field": ".".join(str(p) for p in e["loc"] if p != "body"), "message": e["msg"]} for e in exc.errors()
        ]
        return JSONResponse(
            status_code=422, content=jsonable_encoder(_body("validation_error", "Request validation failed", request, errors=errors))
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        return JSONResponse(status_code=exc.status_code, content=_body("http_error", exc.detail, request))

    @app.exception_handler(IntegrityError)
    async def integrity_handler(request: Request, exc: IntegrityError):
        logger.warning("Integrity error: %s", exc.orig)
        return JSONResponse(
            status_code=409, content=_body("integrity_error", "The operation conflicts with existing data", request)
        )

    @app.exception_handler(SQLAlchemyError)
    async def db_handler(request: Request, exc: SQLAlchemyError):
        logger.exception("Database error")
        return JSONResponse(status_code=500, content=_body("database_error", "A database error occurred", request))

    @app.exception_handler(Exception)
    async def unhandled_handler(request: Request, exc: Exception):
        logger.exception("Unhandled error")
        return JSONResponse(status_code=500, content=_body("internal_error", "Internal server error", request))

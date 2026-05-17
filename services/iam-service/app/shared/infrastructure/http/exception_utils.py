from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


def register_exception_handlers(
    app: FastAPI,
    mapping: dict[type[Exception], int],
) -> None:
    for exc_type, status_code in mapping.items():

        def _make_handler(code: int):
            async def _handler(request: Request, exc: Exception) -> JSONResponse:
                return JSONResponse(status_code=code, content={"detail": str(exc)})

            return _handler

        app.exception_handler(exc_type)(_make_handler(status_code))

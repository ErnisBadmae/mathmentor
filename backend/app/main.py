from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.adapters.api.routes import router
from app.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="EGE Mentor API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(router, prefix="/api")

    @app.exception_handler(LookupError)
    async def lookup_error_handler(_request: Request, exc: LookupError) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(ValueError)
    async def value_error_handler(_request: Request, exc: ValueError) -> JSONResponse:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    return app


app = create_app()

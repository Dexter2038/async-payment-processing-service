import subprocess
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.v1.payments import router as payments_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Применяем миграции перед стартом
    subprocess.run(["uv", "run", "alembic", "upgrade", "head"])
    yield


app = FastAPI(
    title="Async Payment Processing Service",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.include_router(payments_router, prefix="/api/v1/payments", tags=["payments"])


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    return {"status": "ok", "version": app.version}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)

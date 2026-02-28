from fastapi import FastAPI

from app.api.chat import router as chat_router
from app.api.health import router as health_router

app = FastAPI(title="Standard Assistant API", version="0.1.0")

app.include_router(health_router, prefix="/api/v1", tags=["health"])
app.include_router(chat_router, prefix="/api/v1", tags=["chat"])


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "Standard Assistant backend is running"}

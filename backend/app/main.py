from app.api.auth import router as auth_router
from fastapi import FastAPI

from app.api.chat import router as chat_router
from app.api.files import router as files_router
from app.api.health import router as health_router
from app.api.models import router as model_router
from app.api.users import router as users_router

app = FastAPI(title="Standard Assistant API", version="0.1.0")

app.include_router(health_router, prefix="/api/v1", tags=["health"])
app.include_router(chat_router, prefix="/api/v1", tags=["chat"])
app.include_router(files_router, prefix="/api/v1", tags=["files"])
app.include_router(model_router, prefix="/api/v1", tags=["models"])
app.include_router(auth_router, prefix="/api/v1", tags=["auth"])
app.include_router(users_router, prefix="/api/v1", tags=["users"])


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "Standard Assistant backend is running"}

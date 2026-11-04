
from fastapi import FastAPI
from backend.app.core.config import Settings
from backend.app.api.routes import router

app = FastAPI(
    title=Settings.APP_NAME,
    version=Settings.APP_VERSION,
    description=Settings.APP_DESCRIPTION
)

app.include_router(router, prefix="/api")

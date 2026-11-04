from fastapi import APIRouter
from backend.app.api.auth import router as auth_router
from backend.app.api.organizations import router as organizations_router
from backend.app.api.memberships import router as memberships_router
from backend.app.api.users import router as users_router
from backend.app.api.me import router as me_router

router = APIRouter()
router.include_router(auth_router)
router.include_router(organizations_router)
router.include_router(memberships_router)
router.include_router(users_router)
router.include_router(me_router)

@router.get("/")
def home():
    return {
        "application": "EnterpriseAI",
        "status": "running"
    }


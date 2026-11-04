import re

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.security import hash_password
from backend.app.models.user import User
from backend.app.schemas.user import UserCreate, UserResponse

router = APIRouter(prefix="/users", tags=["Users"])


def _is_email_unique_conflict(error: IntegrityError) -> bool:
    original = error.orig
    message = str(original).lower()
    args = getattr(original, "args", ())

    if args and args[0] == 1062:  # MySQL duplicate entry
        return re.search(r"for key ['`](?:[^'`]+\.)?email['`]", message) is not None
    if "unique constraint failed" in message:
        return "users.email" in message

    pgcode = getattr(original, "pgcode", None)
    constraint = str(getattr(getattr(original, "diag", None), "constraint_name", "")).lower()
    return pgcode == "23505" and "email" in constraint


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(user_data: UserCreate, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )

    user = User(
        name=user_data.name,
        email=str(user_data.email),
        password_hash=hash_password(user_data.password),
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        if _is_email_unique_conflict(error):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account with this email already exists.",
            ) from error
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="A database error occurred.",
        ) from error

    db.refresh(user)
    return user

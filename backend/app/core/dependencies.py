from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from sqlalchemy import select

from backend.app.core.database import get_db
from backend.app.core.security import decode_access_token
from backend.app.models.user import User
from backend.app.models.membership import Membership
from backend.app.models.organization import Organization

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db)
) -> User:

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"}
    )

    if credentials is None:
        raise credentials_exception

    try:
        payload = decode_access_token(credentials.credentials)
        user_id = int(payload["sub"])

    except (ValueError, KeyError, TypeError):
        raise credentials_exception

    user = db.get(User, user_id)

    if user is None:
        raise credentials_exception

    return user


def get_user_membership(
    user_id: int,
    organization_id: int,
    db: Session,
    for_update: bool = False,
) -> Membership | None:

    statement = select(Membership).where(
        Membership.user_id == user_id,
        Membership.organization_id == organization_id
    )
    if for_update:
        statement = statement.with_for_update()

    return db.scalar(statement)


def require_organization_member(
    organization_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Membership:
    organization = db.get(Organization, organization_id)
    if organization is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found.",
        )

    membership = get_user_membership(
        user_id=current_user.id,
        organization_id=organization_id,
        db=db
    )

    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this organization."
        )

    return membership


def require_organization_admin(
    organization_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Membership:
    # Lock the organization row so concurrent role changes/removals cannot
    # simultaneously pass the last-admin check.
    statement = (
        select(Organization)
        .where(Organization.id == organization_id)
        .with_for_update()
    )
    organization = db.scalar(statement)
    if organization is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found.",
        )

    membership = get_user_membership(
        user_id=current_user.id,
        organization_id=organization_id,
        db=db,
        for_update=True,
    )
    if membership is None or membership.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Organization administrator role required.",
        )

    return membership

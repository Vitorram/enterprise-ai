import re

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from backend.app.core.dependencies import (
    get_user_membership,
    require_organization_admin,
    require_organization_member,
)
from backend.app.core.database import get_db
from backend.app.models.membership import Membership
from backend.app.models.user import User
from backend.app.schemas.membership import (
    MembershipCreate,
    MembershipRead,
    MembershipUpdate,
)

router = APIRouter(prefix="/organizations", tags=["Memberships"])


def _is_membership_duplicate(error: IntegrityError) -> bool:
    original = error.orig
    message = str(original).lower()
    args = getattr(original, "args", ())

    if args and args[0] == 1062:  # MySQL duplicate entry
        return "uq_memberships_user_organization" in message
    if "unique constraint failed" in message:
        return (
            "memberships.user_id" in message
            and "memberships.organization_id" in message
        )

    pgcode = getattr(original, "pgcode", None)
    constraint = str(getattr(getattr(original, "diag", None), "constraint_name", "")).lower()
    return pgcode == "23505" and (
        constraint == "uq_memberships_user_organization"
        or re.search(r"memberships.*user.*organization", constraint) is not None
    )


def _commit_membership_change(db: Session) -> None:
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        if _is_membership_duplicate(error):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This user is already a member of the organization.",
            ) from error
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="A database error occurred.",
        ) from error


def _membership_in_organization(
    db: Session,
    organization_id: int,
    user_id: int,
) -> Membership | None:
    statement = (
        select(Membership)
        .options(joinedload(Membership.user))
        .where(
            Membership.organization_id == organization_id,
            Membership.user_id == user_id,
        )
        .with_for_update()
    )
    return db.scalar(statement)


def _admin_count(db: Session, organization_id: int) -> int:
    statement = select(Membership.id).where(
        Membership.organization_id == organization_id,
        Membership.role == "admin",
    ).with_for_update()
    return len(db.scalars(statement).all())


@router.post(
    "/{organization_id}/members",
    response_model=MembershipRead,
    status_code=status.HTTP_201_CREATED,
)
def add_member(
    organization_id: int,
    member_data: MembershipCreate,
    db: Session = Depends(get_db),
    _admin: Membership = Depends(require_organization_admin),
):
    user = db.get(User, member_data.user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    if get_user_membership(user.id, organization_id, db) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This user is already a member of the organization.",
        )

    membership = Membership(
        user_id=user.id,
        organization_id=organization_id,
        role=member_data.role,
        user=user,
    )
    try:
        db.add(membership)
        db.flush()
        response_data = MembershipRead.model_validate(membership)
        db.commit()
    except IntegrityError as error:
        db.rollback()
        if _is_membership_duplicate(error):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This user is already a member of the organization.",
            ) from error
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="A database error occurred.",
        ) from error
    except Exception:
        db.rollback()
        raise
    return response_data


@router.get(
    "/{organization_id}/members",
    response_model=list[MembershipRead],
)
def list_members(
    organization_id: int,
    db: Session = Depends(get_db),
    _member: Membership = Depends(require_organization_member),
):
    statement = (
        select(Membership)
        .options(joinedload(Membership.user))
        .where(Membership.organization_id == organization_id)
        .order_by(Membership.id)
    )
    return db.scalars(statement).all()


@router.patch(
    "/{organization_id}/members/{user_id}",
    response_model=MembershipRead,
)
def update_member(
    organization_id: int,
    user_id: int,
    member_data: MembershipUpdate,
    db: Session = Depends(get_db),
    _admin: Membership = Depends(require_organization_admin),
):
    membership = _membership_in_organization(db, organization_id, user_id)
    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Membership not found.",
        )

    if membership.role == "admin" and member_data.role != "admin":
        if _admin_count(db, organization_id) <= 1:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="The last organization administrator cannot be demoted.",
            )

    membership.role = member_data.role
    response_data = MembershipRead.model_validate(membership)
    _commit_membership_change(db)
    return response_data


@router.delete(
    "/{organization_id}/members/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_member(
    organization_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    _admin: Membership = Depends(require_organization_admin),
):
    membership = _membership_in_organization(db, organization_id, user_id)
    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Membership not found.",
        )

    if membership.role == "admin" and _admin_count(db, organization_id) <= 1:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The last organization administrator cannot be removed.",
        )

    db.delete(membership)
    _commit_membership_change(db)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

import re

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session



from backend.app.core.dependencies import get_current_user, require_organization_member
from backend.app.models.membership import Membership

from backend.app.core.database import get_db
from backend.app.models.organization import Organization
from backend.app.models.user import User
from backend.app.schemas.organization import (
    OrganizationCreate,
    OrganizationRead,
    OrganizationUpdate,
)

router = APIRouter(prefix="/organizations", tags=["Organizations"])


def _is_unique_conflict(error: IntegrityError) -> bool:
    """Recognize unique key errors from the supported MySQL and SQLite drivers."""
    original = error.orig
    message = str(original).lower()
    args = getattr(original, "args", ())

    if args and args[0] == 1062:  # MySQL duplicate entry
        return re.search(r"for key ['`](?:[^'`]+\.)?(?:name|cnpj)['`]", message) is not None
    if "unique constraint failed" in message:
        return "organizations.name" in message or "organizations.cnpj" in message

    pgcode = getattr(original, "pgcode", None)
    constraint = str(getattr(getattr(original, "diag", None), "constraint_name", "")).lower()
    return pgcode == "23505" and ("name" in constraint or "cnpj" in constraint)


def _is_foreign_key_conflict(error: IntegrityError) -> bool:
    original = error.orig
    message = str(original).lower()
    args = getattr(original, "args", ())
    return (
        (bool(args) and args[0] == 1451)  # MySQL parent row is referenced
        or "foreign key constraint failed" in message  # SQLite
        or getattr(original, "pgcode", None) == "23503"  # PostgreSQL
    )


def _raise_integrity_error(db: Session, error: IntegrityError) -> None:
    db.rollback()
    if _is_unique_conflict(error):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An organization with this name or CNPJ already exists.",
        ) from error
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="A database error occurred.",
    ) from error


def _commit_or_raise_conflict(db: Session) -> None:
    try:
        db.commit()
    except IntegrityError as error:
        _raise_integrity_error(db, error)


@router.post("/", response_model=OrganizationRead, status_code=status.HTTP_201_CREATED)
def create_organization(
    organization_data: OrganizationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    organization = Organization(**organization_data.model_dump())
    try:
        db.add(organization)
        db.flush()

        membership = Membership(
            user_id=current_user.id,
            organization_id=organization.id,
            role="admin",
            user=current_user,
            organization=organization,
        )
        db.add(membership)
        db.flush()

        response_data = OrganizationRead.model_validate(organization)
        db.commit()
        return response_data
    except IntegrityError as error:
        _raise_integrity_error(db, error)
    except Exception:
        db.rollback()
        raise


@router.get("/", response_model=list[OrganizationRead])
def list_organizations(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    return (
        db.query(Organization)
        .order_by(Organization.id)
        .offset(skip)
        .limit(limit)
        .all()
    )


@router.get("/{organization_id}", response_model=OrganizationRead)
def get_organization(organization_id: int, db: Session = Depends(get_db)):
    organization = db.get(Organization, organization_id)
    if organization is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found.")
    return organization


@router.put("/{organization_id}", response_model=OrganizationRead)
def update_organization(
    organization_id: int,
    organization_data: OrganizationUpdate,
    db: Session = Depends(get_db),
):
    organization = db.get(Organization, organization_id)
    if organization is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found.")

    for field, value in organization_data.model_dump(exclude_unset=True).items():
        setattr(organization, field, value)

    _commit_or_raise_conflict(db)
    db.refresh(organization)
    return organization


@router.delete("/{organization_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_organization(organization_id: int, db: Session = Depends(get_db)):
    organization = db.get(Organization, organization_id)
    if organization is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found.")

    db.delete(organization)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        if _is_foreign_key_conflict(error):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Organization cannot be deleted while it has associated records.",
            ) from error
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="A database error occurred.",
        ) from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{organization_id}/access")
def check_organization_access(
    organization_id: int,
    membership: Membership = Depends(require_organization_member)
):
    return {
        "organization_id": organization_id,
        "user_id": membership.user_id,
        "role": membership.role,
        "access": "granted"
    }

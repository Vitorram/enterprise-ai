import os
import unittest

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ["SECRET_KEY"] = "unit-test-secret-key-not-for-production-000000000000"
os.environ["ACCESS_TOKEN_EXPIRE_MINUTES"] = "5"

from backend.app.api.memberships import add_member, list_members, remove_member, update_member
from backend.app.api.organizations import create_organization
from backend.app.core.database import Base
from backend.app.core.dependencies import (
    get_user_membership,
    require_organization_admin,
    require_organization_member,
)
from backend.app.models.membership import Membership
from backend.app.models.user import User
from backend.app.schemas.membership import MembershipCreate, MembershipUpdate
from backend.app.schemas.organization import OrganizationCreate


class MembershipTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        cls.session_factory = sessionmaker(
            bind=cls.engine,
            autoflush=False,
            autocommit=False,
        )

    @classmethod
    def tearDownClass(cls):
        Base.metadata.drop_all(bind=cls.engine)
        cls.engine.dispose()

    def setUp(self):
        Base.metadata.drop_all(bind=self.engine)
        Base.metadata.create_all(bind=self.engine)
        self.db = self.session_factory()

    def tearDown(self):
        self.db.close()

    def make_user(self, email: str) -> User:
        user = User(name=email.split("@")[0], email=email, password_hash="test-hash")
        self.db.add(user)
        self.db.commit()
        return user

    def make_organization(self, owner: User, name: str):
        return create_organization(
            OrganizationCreate(name=name),
            self.db,
            owner,
        )

    def admin_membership(self, organization_id: int, user: User) -> Membership:
        return require_organization_admin(
            organization_id,
            current_user=user,
            db=self.db,
        )

    def test_organization_creation_grants_creator_admin_membership(self):
        creator = self.make_user("creator@example.com")

        organization = self.make_organization(creator, "Creator Organization")

        membership = get_user_membership(creator.id, organization.id, self.db)
        self.assertIsNotNone(membership)
        self.assertEqual(membership.role, "admin")

    def test_non_admin_cannot_add_members(self):
        owner = self.make_user("owner@example.com")
        viewer = self.make_user("viewer@example.com")
        organization = self.make_organization(owner, "Authorization Organization")
        self.db.add(
            Membership(
                user_id=viewer.id,
                organization_id=organization.id,
                role="viewer",
            )
        )
        self.db.commit()

        with self.assertRaises(HTTPException) as raised:
            self.admin_membership(organization.id, viewer)
        self.assertEqual(raised.exception.status_code, 403)

    def test_admin_can_add_member_and_duplicates_are_rejected(self):
        owner = self.make_user("owner@example.com")
        invitee = self.make_user("invitee@example.com")
        organization = self.make_organization(owner, "Member Organization")
        admin = self.admin_membership(organization.id, owner)
        request = MembershipCreate(user_id=invitee.id, role="viewer")

        created = add_member(organization.id, request, self.db, admin)
        self.assertEqual(created.user_id, invitee.id)
        self.assertEqual(created.role, "viewer")
        self.assertNotIn("password_hash", created.model_dump())

        with self.assertRaises(HTTPException) as raised:
            add_member(organization.id, request, self.db, admin)
        self.assertEqual(raised.exception.status_code, 409)

        self.db.add(
            Membership(
                user_id=invitee.id,
                organization_id=organization.id,
                role="viewer",
            )
        )
        with self.assertRaises(IntegrityError):
            self.db.commit()
        self.db.rollback()

    def test_last_admin_cannot_be_removed_or_demoted(self):
        owner = self.make_user("owner@example.com")
        organization = self.make_organization(owner, "Last Admin Organization")
        admin = self.admin_membership(organization.id, owner)

        with self.assertRaises(HTTPException) as removal_error:
            remove_member(organization.id, owner.id, self.db, admin)
        self.assertEqual(removal_error.exception.status_code, 409)

        with self.assertRaises(HTTPException) as demotion_error:
            update_member(
                organization.id,
                owner.id,
                MembershipUpdate(role="viewer"),
                self.db,
                admin,
            )
        self.assertEqual(demotion_error.exception.status_code, 409)
        self.assertEqual(
            get_user_membership(owner.id, organization.id, self.db).role,
            "admin",
        )

    def test_membership_access_and_mutation_are_scoped_to_organization(self):
        owner_a = self.make_user("owner-a@example.com")
        owner_b = self.make_user("owner-b@example.com")
        organization_a = self.make_organization(owner_a, "Organization A")
        organization_b = self.make_organization(owner_b, "Organization B")
        member_b = self.make_user("member-b@example.com")
        membership_b = Membership(
            user_id=member_b.id,
            organization_id=organization_b.id,
            role="viewer",
        )
        self.db.add(membership_b)
        self.db.commit()

        with self.assertRaises(HTTPException) as list_error:
            require_organization_member(
                organization_a.id,
                current_user=owner_b,
                db=self.db,
            )
        self.assertEqual(list_error.exception.status_code, 403)

        admin_a = self.admin_membership(organization_a.id, owner_a)
        with self.assertRaises(HTTPException) as mutate_error:
            remove_member(organization_a.id, member_b.id, self.db, admin_a)
        self.assertEqual(mutate_error.exception.status_code, 404)
        self.assertIsNotNone(
            get_user_membership(member_b.id, organization_b.id, self.db)
        )

        listed = list_members(
            organization_b.id,
            self.db,
            require_organization_member(
                organization_b.id,
                current_user=owner_b,
                db=self.db,
            ),
        )
        self.assertEqual({row.organization_id for row in listed}, {organization_b.id})


if __name__ == "__main__":
    unittest.main()

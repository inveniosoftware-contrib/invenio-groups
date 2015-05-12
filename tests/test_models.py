# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2015 CERN.
#
# Invenio is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the
# License, or (at your option) any later version.
#
# Invenio is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Invenio; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place, Suite 330, Boston, MA 02111-1307, USA.


""" Test groups data models. """

from __future__ import absolute_import, print_function, unicode_literals

from invenio.ext.sqlalchemy import db
from invenio.testsuite import InvenioTestCase, make_test_suite, run_test_suite

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import FlushError, NoResultFound


class BaseTestCase(InvenioTestCase):
    """Base test case."""

    def setUp(self):
        """Clear tables."""
        from invenio_groups.models import Group, Membership, GroupAdmin
        from invenio.modules.accounts.models import User

        Group.query.delete()
        Membership.query.delete()
        GroupAdmin.query.delete()
        User.query.delete()
        db.session.commit()

    def tearDown(self):
        """Expunge session."""
        db.session.expunge_all()


class SubscriptionPolicyTestCase(BaseTestCase):
    """Test SubscriptionPolicy class."""

    def test_validate(self):
        """Test policy validation."""
        from invenio_groups.models import SubscriptionPolicy

        self.assertTrue(SubscriptionPolicy.validate(SubscriptionPolicy.OPEN))
        self.assertTrue(SubscriptionPolicy.validate(
            SubscriptionPolicy.APPROVAL))
        self.assertTrue(SubscriptionPolicy.validate(SubscriptionPolicy.CLOSED))
        self.assertFalse(SubscriptionPolicy.validate("INVALID"))

    def test_describe(self):
        """Test policy describe."""
        from invenio_groups.models import SubscriptionPolicy

        self.assertTrue(
            SubscriptionPolicy.describe(SubscriptionPolicy.OPEN))
        self.assertTrue(
            SubscriptionPolicy.describe(SubscriptionPolicy.APPROVAL))
        self.assertTrue(
            SubscriptionPolicy.describe(SubscriptionPolicy.CLOSED))
        self.assertIsNone(SubscriptionPolicy.describe("INVALID"))


class PrivacyPolicyTestCase(BaseTestCase):
    """Test PrivacyPolicy class."""

    def test_validate(self):
        """Test policy validation."""
        from invenio_groups.models import PrivacyPolicy

        self.assertTrue(PrivacyPolicy.validate(PrivacyPolicy.PUBLIC))
        self.assertTrue(PrivacyPolicy.validate(PrivacyPolicy.MEMBERS))
        self.assertTrue(PrivacyPolicy.validate(PrivacyPolicy.ADMINS))
        self.assertFalse(PrivacyPolicy.validate("INVALID"))

    def test_describe(self):
        """Test policy describe."""
        from invenio_groups.models import PrivacyPolicy

        self.assertTrue(PrivacyPolicy.describe(PrivacyPolicy.PUBLIC))
        self.assertTrue(PrivacyPolicy.describe(PrivacyPolicy.MEMBERS))
        self.assertTrue(PrivacyPolicy.describe(PrivacyPolicy.ADMINS))
        self.assertIsNone(PrivacyPolicy.describe("INVALID"))


class MembershipState(BaseTestCase):
    """Test MembershipState class."""

    def test_validate(self):
        """Test policy validation."""
        from invenio_groups.models import MembershipState

        self.assertTrue(MembershipState.validate(
            MembershipState.PENDING_ADMIN))
        self.assertTrue(MembershipState.validate(
            MembershipState.PENDING_USER))
        self.assertTrue(MembershipState.validate(MembershipState.ACTIVE))
        self.assertFalse(MembershipState.validate("INVALID"))


class GroupTestCase(BaseTestCase):
    """Test Group data model api."""

    def test_creation(self):
        """Test creation of groups."""
        from invenio_groups.models import Group, \
            GroupAdmin, Membership, SubscriptionPolicy, PrivacyPolicy

        g = Group.create(name="test")
        self.assertEqual(g.name, 'test')
        self.assertEqual(g.description, '')
        self.assertEqual(g.subscription_policy, SubscriptionPolicy.CLOSED)
        self.assertEqual(g.privacy_policy, PrivacyPolicy.ADMINS)
        self.assertEqual(g.is_managed, False)
        assert g.created
        assert g.modified
        self.assertEqual(GroupAdmin.query.count(), 0)
        self.assertEqual(Membership.query.count(), 0)

        g2 = Group.create(
            name="admintest",
            description="desc",
            subscription_policy=SubscriptionPolicy.OPEN,
            privacy_policy=PrivacyPolicy.PUBLIC,
            is_managed=True,
            admins=[g]
        )
        self.assertEqual(g2.name, 'admintest')
        self.assertEqual(g2.description, 'desc')
        self.assertEqual(g2.subscription_policy, SubscriptionPolicy.OPEN)
        self.assertEqual(g2.privacy_policy, PrivacyPolicy.PUBLIC)
        self.assertEqual(g2.is_managed, True)
        assert g2.created
        assert g2.modified
        self.assertEqual(GroupAdmin.query.count(), 1)
        admin = g2.admins[0]
        self.assertEqual(admin.admin_type, 'Group')
        self.assertEqual(admin.admin_id, g.id)
        self.assertEqual(Membership.query.count(), 0)

    def test_creation_existing_name(self):
        """Test what happens if group with identical name is created."""
        from invenio_groups.models import Group

        g = Group.create(name="test", )
        self.assertRaises(
            IntegrityError,
            Group.create, name="test", admins=[g])

    def test_creation_signals(self):
        """Test signals sent after creation."""
        from invenio_groups.models import Group
        from invenio_groups.signals import group_created

        Group.called = False

        def _receiver(sender=None, group=None):
            Group.called = True
            assert sender == Group
            assert group.name == 'signaltest'

        with group_created.connected_to(_receiver):
            Group.create(name="signaltest")
        assert Group.called

        Group.called = False
        with group_created.connected_to(_receiver):
            self.assertRaises(IntegrityError, Group.create, name="signaltest")
        assert not Group.called

    def test_creation_invalid_data(self):
        """Test what happens if group with invalid data is created."""
        from invenio_groups.models import Group

        self.assertRaises(
            AssertionError,
            Group.create, name="")
        self.assertRaises(
            AssertionError,
            Group.create, name="test", privacy_policy='invalid')
        self.assertRaises(
            AssertionError,
            Group.create, name="test", subscription_policy='invalid')
        self.assertEqual(Group.query.count(), 0)

    def test_delete(self):
        """Test deletion of a group."""
        from invenio_groups.models import Group, GroupAdmin, Membership
        from invenio.modules.accounts.models import User

        g1 = Group.create(name="test1")
        g2 = Group.create(name="test2", admins=[g1])
        u = User(email="test@test.test", password="test")
        db.session.add(u)
        db.session.commit()

        g2.add_member(u)

        # Group is admin of another group, which will be left without admins
        g1.delete()
        self.assertEqual(Group.query.count(), 1)
        self.assertEqual(GroupAdmin.query.count(), 0)
        self.assertEqual(Membership.query.count(), 1)

        g2.delete()
        self.assertEqual(Group.query.count(), 0)
        self.assertEqual(GroupAdmin.query.count(), 0)
        self.assertEqual(Membership.query.count(), 0)

    def test_update(self):
        """."""
        from invenio_groups.models import Group, SubscriptionPolicy, \
            PrivacyPolicy

        g = Group.create(name="test")
        m = g.modified
        g.update(
            name="test-change",
            description="changed",
            subscription_policy=SubscriptionPolicy.OPEN,
            privacy_policy=PrivacyPolicy.MEMBERS,
            is_managed=True,
        )

        self.assertEqual(g.name, 'test-change')
        self.assertEqual(g.description, 'changed')
        self.assertEqual(g.subscription_policy, SubscriptionPolicy.OPEN)
        self.assertEqual(g.privacy_policy, PrivacyPolicy.MEMBERS)
        self.assertTrue(g.is_managed)
        self.assertIsNot(m, g.modified)
        assert g.created

    def test_update_duplicated_names(self):
        """."""
        from invenio_groups.models import Group

        g = Group.create(name="test")
        Group.create(name="test-change")
        self.assertEqual(Group.query.count(), 2)
        self.assertRaises(
            IntegrityError,
            g.update, name="test-change")

    def test_get_by_name(self):
        """Test get by name."""
        from invenio_groups.models import Group

        Group.create(name="test1")
        Group.create(name="test2")

        self.assertEqual(Group.get_by_name("test1").name, "test1")
        self.assertIsNone(Group.get_by_name("invalid"),)

    def test_query_by_names(self):
        """Test query by names."""
        from invenio_groups.models import Group
        from flask.ext.sqlalchemy import BaseQuery

        Group.create(name="test1")
        Group.create(name="test2")
        Group.create(name="test3")

        self.assertRaises(
            AssertionError,
            Group.query_by_names, 'test1')

        self.assertIsInstance(Group.query_by_names(['test']), BaseQuery)
        self.assertEqual(Group.query_by_names(["invalid"]).count(), 0)
        self.assertEqual(Group.query_by_names(["test1"]).count(), 1)
        self.assertEqual(Group.query_by_names(["test2", "invalid"]).count(), 1)
        self.assertEqual(Group.query_by_names(["test1", "test2"]).count(), 2)
        self.assertEqual(Group.query_by_names([]).count(), 0)

    def test_query_by_user(self):
        """."""
        from invenio_groups.models import Group, Membership, \
            GroupAdmin, MembershipState
        from invenio.modules.accounts.models import User

        u1 = User(email="test1@test1.test1", password="test1")
        u2 = User(email="test2@test2.test2", password="test2")
        u3 = User(email="test3@test3.test3", password="test3")
        db.session.add(u1)
        db.session.add(u2)
        db.session.add(u3)
        db.session.commit()
        g1 = Group.create(name="test1", admins=[u1])
        g2 = Group.create(name="test2", admins=[u1])

        g1.add_member(u2, state=MembershipState.PENDING_ADMIN)
        g1.add_member(u3, state=MembershipState.ACTIVE)
        g2.add_member(u2, state=MembershipState.ACTIVE)

        self.assertEqual(Group.query.count(), 2)
        self.assertEqual(GroupAdmin.query.count(), 2)
        self.assertEqual(Membership.query.count(), 3)
        self.assertEqual(Group.query_by_user(u1).count(), 2)
        self.assertEqual(Group.query_by_user(u1, with_pending=True).count(), 2)
        self.assertEqual(Group.query_by_user(u2).count(), 1)
        self.assertEqual(Group.query_by_user(u2, with_pending=True).count(), 2)
        self.assertEqual(Group.query_by_user(u3).count(), 1)
        self.assertEqual(Group.query_by_user(u3, with_pending=True).count(), 1)
        self.assertEqual(Group.query_by_user(
            u3, with_pending=True, eager=[Group.members]).count(), 1)

    def test_add_admin(self):
        """."""
        from invenio_groups.models import Group, GroupAdmin

        a = Group.create(name="admin")
        g = Group.create(name="test")

        obj = g.add_admin(a)

        self.assertIsInstance(obj, GroupAdmin)
        self.assertEqual(GroupAdmin.query.count(), 1)
        self.assertRaises(
            IntegrityError,
            g.add_admin, a)

    def test_remove_admin(self):
        """."""
        from invenio_groups.models import Group, GroupAdmin

        a = Group.create(name="admin")
        g = Group.create(name="test", admins=[a])

        self.assertEqual(GroupAdmin.query.count(), 1)

        g.remove_admin(a)

        self.assertEqual(GroupAdmin.query.count(), 0)
        self.assertRaises(
            NoResultFound,
            g.remove_admin, a)

    def test_add_member(self):
        """."""
        from invenio_groups.models import Group, Membership
        from invenio.modules.accounts.models import User

        g = Group.create(name="test1")
        u = User(email="test@test.test", password="test")
        db.session.add(u)
        db.session.commit()

        obj = g.add_member(u)

        self.assertIsInstance(obj, Membership)
        self.assertEqual(Group.query.count(), 1)
        self.assertEqual(Membership.query.count(), 1)
        self.assertRaises(
            FlushError,
            g.add_member, u)

    def test_remove_member(self):
        """."""
        from invenio_groups.models import Group, Membership
        from invenio.modules.accounts.models import User

        g = Group.create(name="test1")
        u = User(email="test@test.test", password="test")
        db.session.add(u)
        db.session.commit()

        g.add_member(u)

        self.assertEqual(Membership.query.count(), 1)

        g.remove_member(u)

        self.assertEqual(Membership.query.count(), 0)
        self.assertIsNone(g.remove_member(u))

    def test_invite(self):
        """."""
        from invenio_groups.models import Group, Membership, \
            MembershipState
        from invenio.modules.accounts.models import User

        g = Group.create(name="test")
        u = User(email="test", password="test")
        u2 = User(email="test", password="test")
        db.session.add(u)
        db.session.add(u2)
        db.session.commit()

        m = g.invite(u)
        self.assertEqual(Membership.query.count(), 1)
        self.assertEqual(m.state, MembershipState.PENDING_USER)

        a = Group.create(name="admin")
        g2 = Group.create(name="test2", admins=[a])
        self.assertIsNone(g2.invite(u2, admin=g))
        m = g2.invite(u2, admin=a)
        self.assertEqual(Membership.query.count(), 2)
        self.assertEqual(m.state, MembershipState.PENDING_USER)

    def test_subscribe(self):
        """."""
        from invenio_groups.models import Group, SubscriptionPolicy, \
            Membership, MembershipState
        from invenio.modules.accounts.models import User

        g_o = Group.create(name="test_open",
                           subscription_policy=SubscriptionPolicy.OPEN)
        g_a = Group.create(name="test_approval",
                           subscription_policy=SubscriptionPolicy.APPROVAL)
        g_c = Group.create(name="test_closed",
                           subscription_policy=SubscriptionPolicy.CLOSED)
        u = User(email="test", password="test")
        db.session.add(u)
        db.session.commit()

        m_o = g_o.subscribe(u)
        m_c = g_c.subscribe(u)
        m_a = g_a.subscribe(u)

        self.assertIsNone(m_c,)
        self.assertEqual(m_a.state, MembershipState.PENDING_ADMIN)
        self.assertEqual(m_o.state, MembershipState.ACTIVE)
        self.assertEqual(Membership.query.count(), 2)

    def test_is_admin(self):
        """."""
        from invenio_groups.models import Group
        from invenio.modules.accounts.models import User

        g = Group.create(name="test")
        u = User(email="test", password="test")
        db.session.add(u)
        db.session.commit()

        g.add_admin(u)

        self.assertTrue(g.is_admin(u))

        a = Group.create(name="admin")
        g = Group.create(name="test2", admins=[a])
        self.assertTrue(g.is_admin(a))

    def test_is_member(self):
        """."""
        from invenio_groups.models import Group
        from invenio.modules.accounts.models import User

        g = Group.create(name="test")
        u = User(email="test", password="test")
        db.session.add(u)
        db.session.commit()

        g.add_member(u)

        self.assertTrue(g.is_member(u))


class MembershipTestCase(BaseTestCase):
    """Test of membership data model."""

    def test_create(self):
        """."""
        from invenio_groups.models import Group, Membership, \
            MembershipState
        from invenio.modules.accounts.models import User

        g = Group.create(name="test")
        u = User(email="test@test.test", password="test")
        db.session.add(u)
        db.session.commit()

        m = Membership.create(g, u)
        self.assertEqual(m.state, MembershipState.ACTIVE)
        self.assertEqual(m.group.name, g.name)
        self.assertEqual(m.user.id, u.id)
        self.assertRaises(
            FlushError,
            Membership.create, g, u)

    def test_delete(self):
        """."""
        from invenio_groups.models import Group, Membership
        from invenio.modules.accounts.models import User

        g = Group.create(name="test")
        u = User(email="test@test.test", password="test")
        db.session.add(u)
        db.session.commit()

        Membership.create(g, u)
        self.assertEqual(Membership.query.count(), 1)
        Membership.delete(g, u)
        self.assertEqual(Membership.query.count(), 0)
        self.assertIsNone(Membership.delete(g, u))

    def test_get(self):
        """."""
        from invenio_groups.models import Group, Membership
        from invenio.modules.accounts.models import User

        g = Group.create(name="test")
        u = User(email="test@test.test", password="test")
        u2 = User(email="test2@test2.test2", password="test")
        db.session.add(u)
        db.session.add(u2)
        db.session.commit()

        Membership.create(g, u)
        m = Membership.get(g, u)
        m2 = Membership.get(g, u2)

        self.assertEqual(m.group.id, g.id)
        self.assertEqual(m.user.id, u.id)
        self.assertIsNone(m2)

    def test_query_by_user(self):
        """."""
        from invenio_groups.models import Group, Membership, \
            MembershipState
        from invenio.modules.accounts.models import User
        from flask.ext.sqlalchemy import BaseQuery

        g = Group.create(name="test")
        u = User(email="test@test.test", password="test")
        u2 = User(email="test2@test2.test2", password="test2")
        db.session.add(u)
        db.session.add(u2)
        db.session.commit()

        Membership.create(g, u, MembershipState.ACTIVE)

        self.assertIsInstance(Membership.query_by_user(u), BaseQuery)
        self.assertEqual(Membership.query_by_user(u).count(), 1)
        self.assertEqual(Membership.query_by_user(u2).count(), 0)

    def test_query_invitations(self):
        """."""
        from invenio_groups.models import Group, Membership, \
            MembershipState
        from invenio.modules.accounts.models import User
        from flask.ext.sqlalchemy import BaseQuery

        g = Group.create(name="test")
        u1 = User(email="test@test.test", password="test")
        u2 = User(email="test2@test2.test2", password="test2")
        u3 = User(email="test3@test3.test3", password="test3")
        db.session.add_all([u1, u2, u3])
        db.session.commit()
        Membership.create(g, u1, MembershipState.ACTIVE)
        Membership.create(g, u2, MembershipState.PENDING_USER)
        Membership.create(g, u3, MembershipState.PENDING_ADMIN)

        self.assertIsInstance(Membership.query_by_user(u1), BaseQuery)
        self.assertEqual(Membership.query_invitations(u1).count(), 0)
        self.assertEqual(Membership.query_invitations(u2).count(), 1)
        self.assertEqual(Membership.query_invitations(u3).count(), 0)

    def test_query_requests(self):
        """."""
        from invenio_groups.models import Group, Membership, \
            MembershipState
        from invenio.modules.accounts.models import User
        from flask.ext.sqlalchemy import BaseQuery

        a = User(email="admin@admin.admin", password="admin")
        u1 = User(email="test@test.test", password="test")
        u2 = User(email="test2@test2.test2", password="test2")
        db.session.add_all([a, u1, u2])
        db.session.commit()
        g = Group.create(name="test", admins=[a])
        Membership.create(g, u1, MembershipState.PENDING_ADMIN)
        Membership.create(g, u2, MembershipState.PENDING_USER)

        self.assertIsInstance(Membership.query_requests(u1), BaseQuery)
        self.assertEqual(Membership.query_requests(a).count(), 1)

        ad = Group.create(name="admin")
        g2 = Group.create(name="test2", admins=[ad])
        u3 = User(email="test3@test3.test3", password="test3")
        u4 = User(email="test4@test4.test4", password="test4")
        u5 = User(email="test5@test5g.test5", password="test5")
        db.session.add_all([u3, u4, u5])
        db.session.commit()
        Membership.create(ad, u3, MembershipState.ACTIVE)
        Membership.create(g2, u4, MembershipState.PENDING_ADMIN)
        Membership.create(g2, u5, MembershipState.PENDING_USER)

        self.assertEqual(Membership.query_requests(u3).count(), 1)

    def test_query_by_group(self):
        """."""
        from invenio_groups.models import Group, Membership, \
            MembershipState
        from invenio.modules.accounts.models import User
        from flask.ext.sqlalchemy import BaseQuery

        g = Group.create(name="test")
        Group.create(name="test2")
        u = User(email="test@test.test", password="test")
        u2 = User(email="test2@test2.test2", password="test2")
        db.session.add(u)
        db.session.commit()

        Membership.create(g, u, MembershipState.ACTIVE)

        self.assertIsInstance(Membership.query_by_group(g), BaseQuery)
        self.assertEqual(Membership.query_by_group(g).count(), 1)
        self.assertEqual(Membership.query_by_group(u2).count(), 0)

    def test_accept(self):
        """."""
        from invenio_groups.models import Group, Membership, \
            MembershipState
        from invenio.modules.accounts.models import User

        g = Group.create(name="test")
        u = User(email="test@test.test", password="test")
        db.session.add(u)
        db.session.commit()

        m = Membership.create(g, u, MembershipState.PENDING_ADMIN)
        m.accept()

        self.assertEqual(m.state, MembershipState.ACTIVE)

    def test_reject(self):
        """."""
        from invenio_groups.models import Group, Membership
        from invenio.modules.accounts.models import User

        g = Group.create(name="test")
        u = User(email="test@test.test", password="test")
        db.session.add(u)
        db.session.commit()

        m = Membership.create(g, u)
        m.reject()

        self.assertEqual(Membership.query.count(), 0)


class GroupAdminTestCase(BaseTestCase):
    """Test of GroupAdmin data model."""

    def test_create(self):
        """."""
        from invenio_groups.models import Group, GroupAdmin
        a = Group.create(name="admin")
        g = Group.create(name="test")

        ga = GroupAdmin.create(g, a)

        self.assertEqual(ga.admin_type, 'Group')
        self.assertEqual(ga.admin_id, a.id)
        self.assertEqual(ga.group.id, g.id)
        self.assertEqual(GroupAdmin.query.count(), 1)

    def test_delete(self):
        """."""
        from invenio_groups.models import Group, GroupAdmin
        a = Group.create(name="admin")
        g = Group.create(name="test")

        ga = GroupAdmin.create(g, a)

        self.assertEqual(ga.admin_type, 'Group')
        self.assertEqual(ga.admin_id, a.id)
        self.assertEqual(ga.group.id, g.id)
        self.assertEqual(GroupAdmin.query.count(), 1)

        GroupAdmin.delete(g, a)
        self.assertEqual(GroupAdmin.query.count(), 0)

    def test_query_by_group(self):
        """."""
        from invenio_groups.models import Group, GroupAdmin
        from flask.ext.sqlalchemy import BaseQuery

        a = Group.create(name="admin")
        g = Group.create(name="test", admins=[a])
        g2 = Group.create(name="test2")

        self.assertIsInstance(GroupAdmin.query_by_group(g), BaseQuery)
        self.assertEqual(GroupAdmin.query_by_group(g).count(), 1)
        self.assertEqual(GroupAdmin.query_by_group(g2).count(), 0)

    def test_query_by_admin(self):
        """."""
        from invenio_groups.models import Group, GroupAdmin
        from flask.ext.sqlalchemy import BaseQuery

        a = Group.create(name="admin")
        g = Group.create(name="test", admins=[a])

        self.assertIsInstance(GroupAdmin.query_by_admin(a), BaseQuery)
        self.assertEqual(GroupAdmin.query_by_admin(a).count(), 1)
        self.assertEqual(GroupAdmin.query_by_admin(g).count(), 0)

    def test_query_admins_by_group_ids(self):
        """."""
        from invenio_groups.models import Group, GroupAdmin
        from sqlalchemy.orm.query import Query

        a = Group.create(name="admin")
        g = Group.create(name="test", admins=[a])

        self.assertIsInstance(GroupAdmin.query_admins_by_group_ids([g.id]),
                              Query)
        self.assertEqual(
            GroupAdmin.query_admins_by_group_ids([g.id]).count(), 1)
        self.assertEqual(
            GroupAdmin.query_admins_by_group_ids([a.id]).count(), 0)
        self.assertRaises(
            AssertionError,
            GroupAdmin.query_admins_by_group_ids, 'invalid')


TEST_SUITE = make_test_suite(
    SubscriptionPolicyTestCase, PrivacyPolicyTestCase, GroupTestCase,
    MembershipTestCase)

if __name__ == "__main__":
    run_test_suite(TEST_SUITE)

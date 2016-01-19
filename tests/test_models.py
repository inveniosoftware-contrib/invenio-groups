# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2015, 2016 CERN.
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


"""Test groups data models."""

from __future__ import absolute_import, print_function

import pytest
from invenio_db import db
from sqlalchemy import event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import FlushError, NoResultFound


def test_subscription_policy_validate():
    """Test policy validation."""
    from invenio_groups.api import SubscriptionPolicy

    assert SubscriptionPolicy.validate(SubscriptionPolicy.OPEN)
    assert SubscriptionPolicy.validate(SubscriptionPolicy.APPROVAL)
    assert SubscriptionPolicy.validate(SubscriptionPolicy.CLOSED)
    assert not SubscriptionPolicy.validate("INVALID")


def test_subscription_policy_describe():
    """Test policy describe."""
    from invenio_groups.api import SubscriptionPolicy

    assert SubscriptionPolicy.describe(SubscriptionPolicy.OPEN)
    assert SubscriptionPolicy.describe(SubscriptionPolicy.APPROVAL)
    assert SubscriptionPolicy.describe(SubscriptionPolicy.CLOSED)
    assert SubscriptionPolicy.describe("INVALID") is None


def test_privacy_policy_validate():
    """Test policy validation."""
    from invenio_groups.api import PrivacyPolicy

    assert PrivacyPolicy.validate(PrivacyPolicy.PUBLIC)
    assert PrivacyPolicy.validate(PrivacyPolicy.MEMBERS)
    assert PrivacyPolicy.validate(PrivacyPolicy.ADMINS)
    assert not PrivacyPolicy.validate("INVALID")


def test_privacy_policy_describe():
    """Test policy describe."""
    from invenio_groups.api import PrivacyPolicy

    assert PrivacyPolicy.describe(PrivacyPolicy.PUBLIC)
    assert PrivacyPolicy.describe(PrivacyPolicy.MEMBERS)
    assert PrivacyPolicy.describe(PrivacyPolicy.ADMINS)
    assert PrivacyPolicy.describe("INVALID") is None


def test_membership_state_validate():
    """Test policy validation."""
    from invenio_groups.api import MembershipState
    assert MembershipState.validate(MembershipState.PENDING_ADMIN)
    assert MembershipState.validate(MembershipState.PENDING_USER)
    assert MembershipState.validate(MembershipState.ACTIVE)
    assert not MembershipState.validate("INVALID")


def test_group_creation(app):
    """Test creation of groups."""
    with app.app_context():
        from invenio_groups.models import Group, \
            GroupAdmin, Membership, SubscriptionPolicy, PrivacyPolicy

        g = Group.create(name="test")
        assert g.name == 'test'
        assert g.description == ''
        assert g.subscription_policy == SubscriptionPolicy.CLOSED
        assert g.privacy_policy == PrivacyPolicy.ADMINS
        assert not g.is_managed
        assert g.created
        assert g.modified
        assert GroupAdmin.query.count() == 0
        assert Membership.query.count() == 0

        g2 = Group.create(
            name="admintest",
            description="desc",
            subscription_policy=SubscriptionPolicy.OPEN,
            privacy_policy=PrivacyPolicy.PUBLIC,
            is_managed=True,
            admins=[g]
        )
        assert g2.name == 'admintest'
        assert g2.description == 'desc'
        assert g2.subscription_policy == SubscriptionPolicy.OPEN
        assert g2.privacy_policy == PrivacyPolicy.PUBLIC
        assert g2.is_managed
        assert g2.created
        assert g2.modified
        assert GroupAdmin.query.count() == 1
        admin = g2.admins[0]
        assert admin.admin_type == 'Group'
        assert admin.admin_id == g.id
        assert Membership.query.count() == 0


def test_group_creation_existing_name(app):
    """Test what happens if group with identical name is created."""
    with app.app_context():
        from invenio_groups.models import Group

        g = Group.create(name="test", )
        with pytest.raises(IntegrityError):
            Group.create(name="test", admins=[g])


def test_group_creation_signals(app):
    """Test signals sent after creation."""
    with app.app_context():
        from invenio_groups.models import Group

        Group.called = False

        @event.listens_for(Group, 'after_insert')
        def _receiver(mapper, connection, target):
            Group.called = True
            assert isinstance(target, Group)
            assert target.name == 'signaltest'

        Group.create(name="signaltest")
        assert Group.called

        Group.called = False
        with pytest.raises(IntegrityError):
            Group.create(name="signaltest")
        assert not Group.called

        event.remove(Group, 'after_insert', _receiver)


def test_group_creation_invalid_data(app):
    """Test what happens if group with invalid data is created."""
    with app.app_context():
        from invenio_groups.models import Group

        with pytest.raises(AssertionError):
            Group.create(name="")
        with pytest.raises(AssertionError):
            Group.create(name="test", privacy_policy='invalid')
        with pytest.raises(AssertionError):
            Group.create(name="test", subscription_policy='invalid')
        assert Group.query.count() == 0


def test_group_delete(app):
    """Test deletion of a group."""
    with app.app_context():
        from invenio_groups.models import Group, GroupAdmin, Membership
        from invenio_accounts.models import User

        g1 = Group.create(name="test1")
        g2 = Group.create(name="test2", admins=[g1])
        u = User(email="test@test.test", password="test")
        db.session.add(u)
        db.session.commit()

        g2.add_member(u)

        # Group is admin of another group, which will be left without admins
        g1.delete()
        assert Group.query.count() == 1
        assert GroupAdmin.query.count() == 0
        assert Membership.query.count() == 1

        g2.delete()
        assert Group.query.count() == 0
        assert GroupAdmin.query.count() == 0
        assert Membership.query.count() == 0


def test_group_update(app):
    """."""
    with app.app_context():
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

        assert g.name == 'test-change'
        assert g.description == 'changed'
        assert g.subscription_policy == SubscriptionPolicy.OPEN
        assert g.privacy_policy == PrivacyPolicy.MEMBERS
        assert g.is_managed
        assert m is not g.modified
        assert g.created


def test_group_update_duplicated_names(app):
    """."""
    with app.app_context():
        from invenio_groups.models import Group

        g = Group.create(name="test")
        Group.create(name="test-change")
        assert Group.query.count() == 2
        with pytest.raises(IntegrityError):
            g.update(name="test-change")


def test_group_get_by_name(app):
    """Test get by name."""
    with app.app_context():
        from invenio_groups.models import Group

        Group.create(name="test1")
        Group.create(name="test2")

        assert Group.get_by_name("test1").name == "test1"
        assert Group.get_by_name("invalid") is None


def test_group_query_by_names(app):
    """Test query by names."""
    with app.app_context():
        from invenio_groups.models import Group
        from flask.ext.sqlalchemy import BaseQuery

        Group.create(name="test1")
        Group.create(name="test2")
        Group.create(name="test3")

        with pytest.raises(AssertionError):
            Group.query_by_names('test1')

        assert isinstance(Group.query_by_names(['test']), BaseQuery)
        assert Group.query_by_names(["invalid"]).count() == 0
        assert Group.query_by_names(["test1"]).count() == 1
        assert Group.query_by_names(["test2", "invalid"]).count() == 1
        assert Group.query_by_names(["test1", "test2"]).count() == 2
        assert Group.query_by_names([]).count() == 0


def test_group_query_by_user(app):
    """."""
    with app.app_context():
        from invenio_groups.models import Group, Membership, \
            GroupAdmin, MembershipState
        from invenio_accounts.models import User

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

        assert Group.query.count() == 2
        assert GroupAdmin.query.count() == 2
        assert Membership.query.count() == 3
        assert Group.query_by_user(u1).count() == 2
        assert Group.query_by_user(u1, with_pending=True).count() == 2
        assert Group.query_by_user(u2).count() == 1
        assert Group.query_by_user(u2, with_pending=True).count() == 2
        assert Group.query_by_user(u3).count() == 1
        assert Group.query_by_user(u3, with_pending=True).count() == 1
        assert 1 == Group.query_by_user(
            u3, with_pending=True, eager=[Group.members]).count()


def test_group_add_admin(app):
    """."""
    with app.app_context():
        from invenio_groups.models import Group, GroupAdmin

        a = Group.create(name="admin")
        g = Group.create(name="test")

        obj = g.add_admin(a)

        assert isinstance(obj, GroupAdmin)
        assert GroupAdmin.query.count() == 1
        with pytest.raises(IntegrityError):
            g.add_admin(a)


def test_group_remove_admin(app):
    """."""
    with app.app_context():
        from invenio_groups.models import Group, GroupAdmin

        a = Group.create(name="admin")
        g = Group.create(name="test", admins=[a])

        assert GroupAdmin.query.count() == 1

        g.remove_admin(a)

        assert GroupAdmin.query.count() == 0
        with pytest.raises(NoResultFound):
            g.remove_admin(a)


def test_group_add_member(app):
    """."""
    with app.app_context():
        from invenio_groups.models import Group, Membership
        from invenio_accounts.models import User

        g = Group.create(name="test1")
        u = User(email="test@test.test", password="test")
        db.session.add(u)
        db.session.commit()

        obj = g.add_member(u)

        assert isinstance(obj, Membership)
        assert Group.query.count() == 1
        assert Membership.query.count() == 1
        with pytest.raises(FlushError):
            g.add_member(u)


def test_group_remove_member(app):
    """."""
    with app.app_context():
        from invenio_groups.models import Group, Membership
        from invenio_accounts.models import User

        g = Group.create(name="test1")
        u = User(email="test@test.test", password="test")
        db.session.add(u)
        db.session.commit()

        g.add_member(u)

        assert Membership.query.count() == 1

        g.remove_member(u)

        assert Membership.query.count() == 0
        assert g.remove_member(u) is None


def test_group_invite(app):
    """."""
    with app.app_context():
        from invenio_groups.models import Group, Membership, \
            MembershipState
        from invenio_accounts.models import User

        g = Group.create(name="test")
        u = User(email="test@inveniosoftware.org", password="123456")
        u2 = User(email="test2@inveniosoftware.org", password="123456")
        db.session.add(u)
        db.session.add(u2)
        db.session.commit()

        m = g.invite(u)
        assert Membership.query.count() == 1
        assert m.state == MembershipState.PENDING_USER

        a = Group.create(name="admin")
        g2 = Group.create(name="test2", admins=[a])
        assert g2.invite(u2, admin=g) is None
        m = g2.invite(u2, admin=a)
        assert Membership.query.count() == 2
        assert m.state == MembershipState.PENDING_USER


def test_group_subscribe(app):
    """."""
    with app.app_context():
        from invenio_groups.models import Group, SubscriptionPolicy, \
            Membership, MembershipState
        from invenio_accounts.models import User

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

        assert m_c is None
        assert m_a.state == MembershipState.PENDING_ADMIN
        assert m_o.state == MembershipState.ACTIVE
        assert Membership.query.count() == 2


def test_group_is_admin(app):
    """."""
    with app.app_context():
        from invenio_groups.models import Group
        from invenio_accounts.models import User

        g = Group.create(name="test")
        u = User(email="test", password="test")
        db.session.add(u)
        db.session.commit()

        g.add_admin(u)

        assert g.is_admin(u)

        a = Group.create(name="admin")
        g = Group.create(name="test2", admins=[a])
        assert g.is_admin(a)


def test_group_is_member(app):
    """."""
    with app.app_context():
        from invenio_groups.models import Group
        from invenio_accounts.models import User

        g = Group.create(name="test")
        u = User(email="test", password="test")
        db.session.add(u)
        db.session.commit()

        g.add_member(u)

        assert g.is_member(u)


def test_membership_create(app):
    """."""
    with app.app_context():
        from invenio_groups.models import Group, Membership, \
            MembershipState
        from invenio_accounts.models import User

        g = Group.create(name="test")
        u = User(email="test@test.test", password="test")
        db.session.add(u)
        db.session.commit()

        m = Membership.create(g, u)
        assert m.state == MembershipState.ACTIVE
        assert m.group.name == g.name
        assert m.user.id == u.id
        with pytest.raises(FlushError):
            Membership.create(g, u)


def test_membership_delete(app):
    """."""
    with app.app_context():
        from invenio_groups.models import Group, Membership
        from invenio_accounts.models import User

        g = Group.create(name="test")
        u = User(email="test@test.test", password="test")
        db.session.add(u)
        db.session.commit()

        Membership.create(g, u)
        assert Membership.query.count() == 1
        Membership.delete(g, u)
        assert Membership.query.count() == 0
        assert Membership.delete(g, u) is None


def test_membership_get(app):
    """."""
    with app.app_context():
        from invenio_groups.models import Group, Membership
        from invenio_accounts.models import User

        g = Group.create(name="test")
        u = User(email="test@test.test", password="test")
        u2 = User(email="test2@test2.test2", password="test")
        db.session.add(u)
        db.session.add(u2)
        db.session.commit()

        Membership.create(g, u)
        m = Membership.get(g, u)
        m2 = Membership.get(g, u2)

        assert m.group.id == g.id
        assert m.user.id == u.id
        assert m2 is None


def test_membership_query_by_user(app):
    """."""
    with app.app_context():
        from invenio_groups.models import Group, Membership, \
            MembershipState
        from invenio_accounts.models import User
        from flask.ext.sqlalchemy import BaseQuery

        g = Group.create(name="test")
        u = User(email="test@test.test", password="test")
        u2 = User(email="test2@test2.test2", password="test2")
        db.session.add(u)
        db.session.add(u2)
        db.session.commit()

        Membership.create(g, u, MembershipState.ACTIVE)

        assert isinstance(Membership.query_by_user(u), BaseQuery)
        assert Membership.query_by_user(u).count() == 1
        assert Membership.query_by_user(u2).count() == 0


def test_membership_query_invitations(app):
    """."""
    with app.app_context():
        from invenio_groups.models import Group, Membership, \
            MembershipState
        from invenio_accounts.models import User
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

        assert isinstance(Membership.query_by_user(u1), BaseQuery)
        assert Membership.query_invitations(u1).count() == 0
        assert Membership.query_invitations(u2).count() == 1
        assert Membership.query_invitations(u3).count() == 0


def test_membership_query_requests(app):
    """."""
    with app.app_context():
        from invenio_groups.models import Group, Membership, \
            MembershipState
        from invenio_accounts.models import User
        from flask.ext.sqlalchemy import BaseQuery

        a = User(email="admin@admin.admin", password="admin")
        u1 = User(email="test@test.test", password="test")
        u2 = User(email="test2@test2.test2", password="test2")
        db.session.add_all([a, u1, u2])
        db.session.commit()
        g = Group.create(name="test", admins=[a])
        Membership.create(g, u1, MembershipState.PENDING_ADMIN)
        Membership.create(g, u2, MembershipState.PENDING_USER)

        assert isinstance(Membership.query_requests(u1), BaseQuery)
        assert Membership.query_requests(a).count() == 1

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

        assert Membership.query_requests(u3).count() == 1


def test_membership_query_by_group(app):
    """."""
    with app.app_context():
        from invenio_groups.models import Group, Membership, \
            MembershipState
        from invenio_accounts.models import User
        from flask.ext.sqlalchemy import BaseQuery

        g = Group.create(name="test")
        Group.create(name="test2")
        u = User(email="test@test.test", password="test")
        u2 = User(email="test2@test2.test2", password="test2")
        db.session.add(u)
        db.session.add(u2)
        db.session.commit()

        Membership.create(g, u, MembershipState.ACTIVE)
        assert isinstance(Membership.query_by_group(g), BaseQuery)
        assert 1 == Membership.query_by_group(g).count()
        assert 0 == Membership.query_by_user(u2).count()


def test_membership_accept(app):
    """."""
    with app.app_context():
        from invenio_groups.models import Group, Membership, \
            MembershipState
        from invenio_accounts.models import User

        g = Group.create(name="test")
        u = User(email="test@test.test", password="test")
        db.session.add(u)
        db.session.commit()

        m = Membership.create(g, u, MembershipState.PENDING_ADMIN)
        m.accept()

        assert m.state == MembershipState.ACTIVE


def test_membership_reject(app):
    """."""
    with app.app_context():
        from invenio_groups.models import Group, Membership
        from invenio_accounts.models import User

        g = Group.create(name="test")
        u = User(email="test@test.test", password="test")
        db.session.add(u)
        db.session.commit()

        m = Membership.create(g, u)
        m.reject()

        assert Membership.query.count() == 0


def test_group_admin_create(app):
    """."""
    with app.app_context():
        from invenio_groups.models import Group, GroupAdmin
        a = Group.create(name="admin")
        g = Group.create(name="test")

        ga = GroupAdmin.create(g, a)

        assert ga.admin_type == 'Group'
        assert ga.admin_id == a.id
        assert ga.group.id == g.id
        assert GroupAdmin.query.count() == 1


def test_group_admin_delete(app):
    """."""
    with app.app_context():
        from invenio_groups.models import Group, GroupAdmin
        a = Group.create(name="admin")
        g = Group.create(name="test")

        ga = GroupAdmin.create(g, a)

        assert ga.admin_type == 'Group'
        assert ga.admin_id == a.id
        assert ga.group.id == g.id
        assert GroupAdmin.query.count() == 1

        GroupAdmin.delete(g, a)
        assert GroupAdmin.query.count() == 0


def test_group_admin_query_by_group(app):
    """."""
    with app.app_context():
        from invenio_groups.models import Group, GroupAdmin
        from flask.ext.sqlalchemy import BaseQuery

        a = Group.create(name="admin")
        g = Group.create(name="test", admins=[a])
        g2 = Group.create(name="test2")

        assert isinstance(GroupAdmin.query_by_group(g), BaseQuery)
        assert GroupAdmin.query_by_group(g).count() == 1
        assert GroupAdmin.query_by_group(g2).count() == 0


def test_group_admin_query_by_admin(app):
    """."""
    with app.app_context():
        from invenio_groups.models import Group, GroupAdmin
        from flask.ext.sqlalchemy import BaseQuery

        a = Group.create(name="admin")
        g = Group.create(name="test", admins=[a])

        assert isinstance(GroupAdmin.query_by_admin(a), BaseQuery)
        assert GroupAdmin.query_by_admin(a).count() == 1
        assert GroupAdmin.query_by_admin(g).count() == 0


def test_group_admin_query_admins_by_group_ids(app):
    """."""
    with app.app_context():
        from invenio_groups.models import Group, GroupAdmin
        from sqlalchemy.orm.query import Query

        a = Group.create(name="admin")
        g = Group.create(name="test", admins=[a])

        assert isinstance(GroupAdmin.query_admins_by_group_ids([g.id]), Query)
        assert 1 == GroupAdmin.query_admins_by_group_ids([g.id]).count()
        assert 0 == GroupAdmin.query_admins_by_group_ids([a.id]).count()
        with pytest.raises(AssertionError):
            GroupAdmin.query_admins_by_group_ids('invalid')

# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2016 CERN.
#
# Invenio is free software; you can redistribute it
# and/or modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the
# License, or (at your option) any later version.
#
# Invenio is distributed in the hope that it will be
# useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Invenio; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place, Suite 330, Boston,
# MA 02111-1307, USA.
#
# In applying this license, CERN does not
# waive the privileges and immunities granted to it by virtue of its status
# as an Intergovernmental Organization or submit itself to any jurisdiction.


"""Pytest configuration."""

from __future__ import absolute_import, print_function

import os
import shutil
import tempfile

import pytest
from flask import Flask
from flask_babelex import Babel
from flask_breadcrumbs import Breadcrumbs
from flask_menu import Menu
from invenio_accounts import InvenioAccounts
from invenio_accounts.models import User
from invenio_db import InvenioDB, db
from sqlalchemy_utils.functions import create_database, database_exists, \
    drop_database

from invenio_groups import InvenioGroups
from invenio_groups.api import Group


@pytest.fixture
def app(request):
    """Flask application fixture."""
    instance_path = tempfile.mkdtemp()
    app = Flask('testapp', instance_path=instance_path)
    app.config.update(
        LOGIN_DISABLED=False,
        MAIL_SUPPRESS_SEND=True,
        SECRET_KEY='changeme',
        SERVER_NAME='example.com',
        SQLALCHEMY_DATABASE_URI=os.environ.get(
            'SQLALCHEMY_DATABASE_URI', 'sqlite://'),
        TESTING=True,
        WTF_CSRF_ENABLED=False,
    )
    Babel(app)
    Menu(app)
    Breadcrumbs(app)
    InvenioDB(app)
    InvenioAccounts(app)
    InvenioGroups(app)

    with app.app_context():
        if str(db.engine.url) != 'sqlite://' and \
           not database_exists(str(db.engine.url)):
                create_database(str(db.engine.url))
        db.create_all()

    def teardown():
        with app.app_context():
            if str(db.engine.url) != 'sqlite://':
                drop_database(str(db.engine.url))
        shutil.rmtree(instance_path)

    request.addfinalizer(teardown)
    return app


@pytest.fixture
def example_group(app):
    """Create example groups."""
    with app.app_context():
        admin = User(email='test@example.com', password='test_password')
        member = User(email='test2@example.com', password='test_password')
        non_member = User(email='test3@example.com', password='test_password')
        db.session.add(admin)
        db.session.add(member)
        db.session.add(non_member)
        group = Group.create(name='test_group', admins=[admin])
        membership = group.invite(member)
        membership.accept()

        admin_id = admin.id
        member_id = member.id
        non_member_id = non_member.id
        group_id = group.id
        db.session.commit()

    app.get_admin = lambda: User.query.get(admin_id)
    app.get_member = lambda: User.query.get(member_id)
    app.get_non_member = lambda: User.query.get(non_member_id)
    app.get_group = lambda: Group.query.get(group_id)

    return app

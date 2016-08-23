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


"""Minimal Flask application example for development.

Run example development server:

.. code-block:: console

   $ cd examples
   $ flask -a app.py db init
   $ flask -a app.py db create
   $ flask -a app.py fixtures users
   $ flask -a app.py --debug run
"""

from __future__ import absolute_import, print_function

import os

from flask import Flask, current_app
from flask_babelex import Babel
from flask_breadcrumbs import Breadcrumbs
from flask_menu import Menu
from flask_security.utils import encrypt_password
from invenio_accounts import InvenioAccounts, views
from invenio_assets import InvenioAssets
from invenio_db import InvenioDB, db

from invenio_groups import InvenioGroups

# create application's instance directory. Needed for this example only.
current_dir = os.path.dirname(os.path.realpath(__file__))
instance_dir = os.path.join(current_dir, 'app')
if not os.path.exists(instance_dir):
    os.makedirs(instance_dir)

# Create Flask application
app = Flask(__name__, instance_path=instance_dir)
app.config.update(
    ACCOUNTS_USE_CELERY=False,
    MAIL_SUPPRESS_SEND=True,
    SECRET_KEY='changeme',
)
Babel(app)
Menu(app)
Breadcrumbs(app)
InvenioDB(app)
InvenioAssets(app)
accounts = InvenioAccounts(app)
app.register_blueprint(views.blueprint)
InvenioGroups(app)


@app.cli.group()
def fixtures():
    """Command for working with test data."""


@fixtures.command()
def users():
    """Load default users and groups."""
    from invenio_groups.models import Group, Membership, \
        PrivacyPolicy, SubscriptionPolicy

    admin = accounts.datastore.create_user(
        email='admin@inveniosoftware.org',
        password=encrypt_password('123456'),
        active=True,
    )
    reader = accounts.datastore.create_user(
        email='reader@inveniosoftware.org',
        password=encrypt_password('123456'),
        active=True,
    )

    admins = Group.create(name='admins', admins=[admin])
    for i in range(10):
        Group.create(name='group-{0}'.format(i), admins=[admin])
    Membership.create(admins, reader)
    db.session.commit()

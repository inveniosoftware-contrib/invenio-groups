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

"""Invenio-Groups upgrade script."""

from datetime import datetime

from invenio.ext.sqlalchemy import db
from invenio_upgrader.api import op


# Important: Below is only a best guess. You MUST validate which previous
# upgrade you depend on.
depends_on = []


def info():
    """One line upgrade description."""
    return "Separation of groups and accounts modules."


def do_upgrade():
    """Perfrom upgrade."""
    if op.has_table('usergroup'):
        op.rename_table(
            old_table_name='usergroup',
            new_table_name='group'
        )
        with op.batch_alter_table("group") as batch_op:
            batch_op.drop_index('ix_usergroup_name')
            batch_op.create_index('ix_group_name', ['name'], unique=True)
            batch_op.alter_column('name', server_default=None)
            batch_op.add_column(db.Column('is_managed', db.Boolean(),
                                nullable=False, default=False))
            batch_op.alter_column(
                column_name='join_policy',
                new_column_name='privacy_policy',
                type_=db.String(length=1), nullable=False
            )
            batch_op.drop_index('login_method_name')
            batch_op.alter_column(
                column_name='login_method',
                new_column_name='subscription_policy',
                type_=db.String(length=1), nullable=False,
                server_default=None
            )
            batch_op.add_column(db.Column('created', db.DateTime(),
                                nullable=False, default=datetime.now))
            batch_op.add_column(db.Column('modified', db.DateTime(),
                                nullable=False, default=datetime.now,
                                onupdate=datetime.now))
    else:
        op.create_table(
            'group',
            db.Column('id', db.Integer(15, unsigned=True), nullable=False,
                      autoincrement=True),
            db.Column('name', db.String(length=255), nullable=False,
                      unique=True, index=True),
            db.Column('description', db.Text, nullable=True, default=''),
            db.Column('is_managed', db.Boolean(), default=False,
                      nullable=False),
            db.Column('privacy_policy', db.String(length=1), nullable=False),
            db.Column('subscription_policy', db.String(length=1),
                      nullable=False),
            db.Column('created', db.DateTime, nullable=False,
                      default=datetime.now),
            db.Column('modified', db.DateTime, nullable=False,
                      default=datetime.now, onupdate=datetime.now),
            db.PrimaryKeyConstraint('id'),
            mysql_charset='utf8',
            mysql_engine='MyISAM'
        )

    if op.has_table('user_usergroup'):
        op.rename_table(
            old_table_name='user_usergroup',
            new_table_name='groupMEMBER'
        )
        with op.batch_alter_table("groupMEMBER") as batch_op:
            batch_op.drop_index('id_usergroup')
            batch_op.alter_column('id_user', server_default=None)
            batch_op.alter_column(
                column_name='id_usergroup', new_column_name='id_group',
                existing_type=db.Integer(15, unsigned=True),
                nullable=False
            )
            batch_op.create_index('id_group', ['id_group'])
            batch_op.alter_column(
                column_name='user_status', new_column_name='state',
                type_=db.String(length=1), nullable=False
            )
            batch_op.drop_column('user_status_date')
            batch_op.add_column(db.Column('modified', db.DateTime(),
                                nullable=False, default=datetime.now,
                                onupdate=datetime.now))
            batch_op.add_column(db.Column('created', db.DateTime(),
                                nullable=False, default=datetime.now))
    else:
        op.create_table(
            'groupMEMBER',
            db.Column('id_user', db.Integer(15, unsigned=True),
                      nullable=False),
            db.Column('id_group', db.Integer(15, unsigned=True)),
            db.Column('state', db.String(length=1), nullable=False),
            db.Column('created', db.DateTime(), nullable=False,
                      default=datetime.now),
            db.Column('modified', db.DateTime(), nullable=False,
                      default=datetime.now, onupdate=datetime.now),
            db.ForeignKeyConstraint(['id_group'], [u'group.id'], ),
            db.ForeignKeyConstraint(['id_user'], [u'user.id'], ),
            db.PrimaryKeyConstraint('id_user', 'id_group'),
            mysql_charset='utf8',
            mysql_engine='MyISAM'
        )

    op.create_table(
        'groupADMIN',
        db.Column('id', db.Integer(15, unsigned=True), nullable=False,
                  autoincrement=True),
        db.Column('group_id', db.Integer(15, unsigned=True)),
        db.Column('admin_type', db.Unicode(255)),
        db.Column('admin_id', db.Integer),
        db.ForeignKeyConstraint(['group_id'], [u'group.id'], ),
        db.PrimaryKeyConstraint('id', 'group_id'),
        mysql_charset='utf8',
        mysql_engine='MyISAM'
    )

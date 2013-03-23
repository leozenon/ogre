#! /usr/bin/env python

from __future__ import absolute_import

import sys

from flask.ext.script import Manager
from sqlalchemy.exc import IntegrityError

from ogreserver import app, db

manager = Manager(app)

@manager.command
def verify_s3():
    import logging
    logging.basicConfig(filename="boto.log", level=logging.DEBUG)
    from ogreserver.models.datastore import DataStore
    print DataStore.get_missing_books(username="mafro", verify_s3=True)


@manager.command
def create_db():
    "Create the OGRE authentication DB"
    db.create_all()
    print "Database created"


@manager.command
def create_user(username, password, email):
    "Create a new user for OGRE"
    from ogreserver.models.user import User
    user = User(username, password, email)
    db.session.add(user)
    try:
        db.session.commit()
    except IntegrityError:
        print "A user with this email address already exists"
        sys.exit(1)


@manager.command
def rebuild_index():
    "Reindex the entire DB into Whoosh."
    # TODO implement
    pass


@manager.command
def kill():
    "Completely clear the SDB storage. USE WITH CAUTION!"
    import boto.sdb
    import os
    import shutil
    import subprocess
    sdb = boto.sdb.connect_to_region(app.config['AWS_REGION'],
        aws_access_key_id=app.config['AWS_ACCESS_KEY'],
        aws_secret_access_key=app.config['AWS_SECRET_KEY']
    )
    try:
        sdb.delete_domain("ogre_ebooks")
    except boto.exception.SDBResponseError:
        pass
    sdb.create_domain("ogre_ebooks")
    if os.path.exists(app.config['WHOOSH_BASE']):
        shutil.rmtree(app.config['WHOOSH_BASE'])
    if os.path.exists("/tmp/gunicorn-ogre.pid"):
        with open("/tmp/gunicorn-ogre.pid", "r") as f:
            pid = f.read()
        subprocess.call(['kill', '-HUP', pid.strip()])
    print "Killed"


@manager.command
def show():
    import boto.sdb
    import json

    sdb = boto.sdb.connect_to_region(app.config['AWS_REGION'],
        aws_access_key_id=app.config['AWS_ACCESS_KEY'],
        aws_secret_access_key=app.config['AWS_SECRET_KEY']
    )

    rs = sdb.select("ogre_ebooks", "select sdb_key, data from ogre_ebooks")
    for item in rs:
        print json.dumps(json.loads(item['data']), indent=4)


@manager.command
def check_pip():
    import xmlrpclib
    import pip

    pypi = xmlrpclib.ServerProxy('http://pypi.python.org/pypi')
    for dist in pip.get_installed_distributions():
        available = pypi.package_releases(dist.project_name)
        if not available:
            # Try to capitalize pkg name
            available = pypi.package_releases(dist.project_name.capitalize())

        if not available:
            msg = 'no releases at pypi'
        elif available[0] != dist.version:
            msg = '{} available'.format(available[0])
        else:
            msg = 'up to date'
        pkg_info = '{dist.project_name} {dist.version}'.format(dist=dist)
        print '{pkg_info:40} {msg}'.format(pkg_info=pkg_info, msg=msg)

if __name__ == "__main__":
    manager.run()

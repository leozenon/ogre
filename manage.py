#! /usr/bin/env python

from __future__ import absolute_import
from flask.ext.script import Manager

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
    db.create_all()


@manager.command
def create_user(username, password, email):
    from ogreserver.models.user import User
    user = User(username, password, email)
    db.session.add(user)
    db.session.commit()


@manager.command
def create_password_hash(password):
    from ogreserver.models import security
    print security.pwd_context.encrypt(password)


@manager.command
def kill():
    import boto
    sdb = boto.connect_sdb(app.config['AWS_ACCESS_KEY'], app.config['AWS_SECRET_KEY'])
    sdb.delete_domain("ogre_ebooks")
    sdb.create_domain("ogre_ebooks")
    print "Killed"


@manager.command
def show():
    import boto
    import json

    sdb = boto.connect_sdb(app.config['AWS_ACCESS_KEY'], app.config['AWS_SECRET_KEY'])

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

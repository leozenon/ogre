#! /usr/bin/env python

from __future__ import absolute_import

import os
import sys

from flask.ext.script import Manager
from sqlalchemy.exc import IntegrityError, ProgrammingError

from ogreserver import app, db

manager = Manager(app)

# include the sesame manager
from sesame.flask.script import manager as sesame_manager
manager.add_command("sesame", sesame_manager)


@manager.command
def verify_s3():
    import logging
    logging.basicConfig(filename="boto.log", level=logging.DEBUG)
    from ogreserver.models.datastore import DataStore
    print DataStore.get_missing_books(username="mafro", verify_s3=True)


@manager.command
def create_user(username, password, email, test=False):
    """
    Create a new user for OGRE

    test (bool)
        Only check if user has been created; don't actually do anything
    """
    # load a user
    from ogreserver.models.user import User
    user = User.query.filter_by(username=username).first()

    if test is True:
        # only report state in test mode
        if user is None:
            print "User exists"
            sys.exit(1)
        else:
            print "User doesn't exist"
            sys.exit(0)
    else:
        if user is None:
            user = User(username, password, email)
            db.session.add(user)
            try:
                db.session.commit()
            except IntegrityError:
                print "A user with this email address already exists"
                sys.exit(1)
        else:
            print "User {0} already exists".format(username)
            sys.exit(1)


@manager.command
def rebuild_index():
    "Reindex the entire DB into Whoosh."
    # TODO implement
    pass


@manager.command
def init_ogre(test=False):
    """
    Initialize the AWS S3 bucket and SDB endpoints for OGRE.

    test (bool)
        Only check if OGRE has been setup; don't actually do anything
    """

    # init S3
    import boto
    s3 = boto.connect_s3(
        app.config['AWS_ACCESS_KEY'],
        app.config['AWS_SECRET_KEY']
    )

    # check bucket already exists
    aws_setup = False
    for b in s3.get_all_buckets():
        if b.name == app.config['S3_BUCKET']:
            aws_setup = True

    # check mysql DB created
    try:
        from ogreserver.models.user import User
        User.query.first()
        db_setup = True
    except ProgrammingError:
        db_setup = False

    if test is True:
        # only report state in test mode
        if aws_setup is True and db_setup is True:
            print "Already setup"
            sys.exit(0)
        else:
            print "Not setup"
            sys.exit(1)
    else:
        if aws_setup is True and db_setup is True:
            sys.stderr.write("You have already initialized OGRE!\n")
            sys.exit(1)

        # create the local mysql database from our models
        if db_setup is False:
            db.create_all()

        if aws_setup is False:
            try:
                s3.create_bucket(app.config['S3_BUCKET'], location=boto.s3.connection.Location.EU)
            except boto.exception.S3CreateError as e:
                if e.error_code == "BucketAlreadyExists":
                    sys.stderr.write("Bucket name already in use!\n  {0}\n".format(e.error_message))
                else:
                    sys.stderr.write("{0}\n".format(e.error_message))
                sys.exit(1)

            # init SDB
            import boto.sdb
            sdb = boto.sdb.connect_to_region(app.config['AWS_REGION'],
                aws_access_key_id=app.config['AWS_ACCESS_KEY'],
                aws_secret_access_key=app.config['AWS_SECRET_KEY']
            )
            try:
                sdb.create_domain("ogre_ebooks")
            except boto.exception.SDBResponseError as e:
                sys.stderr.write("Failed creating SDB domain!\n  {0}\n".format(e.error_message))
                sys.exit(1)

    print "Succesfully initialized OGRE"


@manager.command
def kill():
    "Completely clear the SDB storage. USE WITH CAUTION!"
    import boto.sdb
    import shutil
    import subprocess

    # TODO add some kind of confirmation here...

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

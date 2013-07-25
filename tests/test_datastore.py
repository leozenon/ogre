import json
import os
import pytest
import shutil
import time


@pytest.fixture
def full_test_setup(request):
    """
    Fixture initialises our setup for a full integration test
    Note the addfinalizer() teardown call at the end of this function
    """
    # delete everything
    _delete_all()

    # create some users and sync their libraries
    delay = _create_user_and_sync(1)
    time.sleep(delay * 2 + 5)

    delay = _create_user_and_sync(2)
    time.sleep(delay * 2 + 5)

    # add a teardown function
    request.addfinalizer(_delete_all)


def _create_user_and_sync(user_id):
    # setup a new user
    user = "user{0}".format(1)
    book_count = _user_create(1)
    conf = _ogreclient_config(1)

    # run a sync from ogreclient
    from ..ogreclient import core
    core.doit("/tmp/ogre-test/{0}".format(user), user, user,
        ogreserver="192.168.1.102:8005",
        ebook_cache_path=conf['ebook_cache_path'],
        ebook_cache_temp_path=conf['ebook_cache_temp_path'],
        ebook_convert_path=conf['ebook_convert_path'],
        calibre_ebook_meta_bin=conf['calibre_ebook_meta_bin']
    )
    return book_count


@pytest.fixture
def flask_app():
    """
    Fixture returns the relative import flask application needed for all tests
    """
    from ..ogreserver import app
    return app


def test_app_config(flask_app):
    """
    Verify all essential config variables have been set
    """
    config_keys = [
        'AWS_ACCESS_KEY',
        'AWS_SECRET_KEY',
        'S3_BUCKET',
        'SECRET_KEY',
        'SQLALCHEMY_DATABASE_URI',
        'WHOOSH_BASE',
        'UPLOADED_EBOOKS_DEST',
        'EBOOK_FORMATS',
        'DOWNLOAD_LINK_EXPIRY'
    ]
    for key in config_keys:
        assert key in flask_app.config
        if isinstance(flask_app.config[key], basestring):
            assert len(flask_app.config[key]) > 0


def test_full(full_test_setup, flask_app):
    """
    Full end-to-end test of Ogreserver and Ogreclient
    """
    # TODO test dont upload exact dupe
    # TODO unit test the S3 and DataStore methods
    # TODO unit test ogreclient caching

    import boto.sdb
    sdb = boto.sdb.connect_to_region(flask_app.config['AWS_REGION'],
        aws_access_key_id=flask_app.config['AWS_ACCESS_KEY'],
        aws_secret_access_key=flask_app.config['AWS_SECRET_KEY']
    )

    # check a book made it to SDB
    found_book = None
    rs = sdb.select("ogre_ebooks", "select sdb_key, data from ogre_ebooks")
    assert len(rs) > 0

    # load the local library for user 1
    books = _get_library(1)
    conf = _ogreclient_config(1)

    # iterate the SDB books and grab a single one
    for item in rs:
        ebook_data = json.loads(item['data'])

        for ebook_path in books:
            with open(ebook_path, "r") as f:
                md5_tup = boto.utils.compute_md5(f)

            if md5_tup[0] == ebook_data['versions']['1']['formats']['epub']['filemd5']:
                found_book = ebook_data
                found_book['local_path'] = ebook_path
                found_book['sdb_key'] = item['sdb_key']
                break

        if found_book is not None:
            # extract meta data
            import subprocess
            meta = subprocess.check_output(
                [conf['calibre_ebook_meta_bin'], found_book['local_path']],
                stderr=subprocess.STDOUT
            )
            authortitle = ebook_data['authortitle'].split(" - ")
            assert authortitle[0] in meta
            assert authortitle[1] in meta
            break

    from ..ogreserver.models.datastore import DataStore

    # verify the file is on S3
    filename = DataStore.generate_filename(
        found_book['authortitle'],
        found_book['versions']['1']['formats']['epub']['filemd5'],
        'epub'
    )

    s3 = boto.connect_s3(flask_app.config['AWS_ACCESS_KEY'], flask_app.config['AWS_SECRET_KEY'])
    bucket = s3.get_bucket(flask_app.config['S3_BUCKET'])
    k = boto.s3.key.Key(bucket)
    k.key = filename

    # check if our file is already up on S3
    assert k.exists()
    k = bucket.get_key(filename)
    metadata = k._get_remote_metadata()
    assert 'x-amz-meta-ogre-key' in metadata
    assert metadata['x-amz-meta-ogre-key'] == found_book['sdb_key']

    # check download URL and automatic expiry
    dl_url = DataStore.get_ebook_url(found_book['sdb_key'])
    import urllib
    assert urllib.urlopen(dl_url).getcode() == 200
    time.sleep(flask_app.config['DOWNLOAD_LINK_EXPIRY'] + 5)
    assert urllib.urlopen(dl_url).getcode() == 403, \
        "S3 download link didn't expire [{0}]".format(dl_url)

    # sync another user and verify the library
    # pg11 is a mobi conversion of the epub
    # pg55 is an exact dupe
    pytest.set_trace()


def _ogreclient_config(num):
    import subprocess
    import tempfile

    # setup some ogreclient config variables
    config_dir = "/tmp/ogre-test/user{0}/config".format(num)
    if not os.path.exists(config_dir):
        os.makedirs(config_dir)
    calibre_ebook_meta_bin = subprocess.check_output(['which', 'ebook-meta']).strip()

    # pass this or the test can't continue
    assert len(calibre_ebook_meta_bin) > 0

    return {
        'config_dir': config_dir,
        'ebook_cache_path': "{0}/ebook_cache".format(config_dir),
        'ebook_cache_temp_path': "{0}/ebook_cache.tmp".format(config_dir),
        'ebook_convert_path': "{0}/egg.epub".format(tempfile.gettempdir()),
        'calibre_ebook_meta_bin': calibre_ebook_meta_bin,
    }


def _user_create(num):
    # create a new user
    from ..ogreserver.models.user import User
    from ..ogreserver import db
    user = User("user{0}".format(num), "user{0}".format(num), "user{0}@test".format(num))
    db.session.add(user)
    db.session.commit()

    # create a small book library
    libpath = "/tmp/ogre-test/user{0}".format(num)
    if not os.path.exists(libpath):
        os.makedirs(libpath)
    book_count = 0
    for root, dirs, files in os.walk("tests/ebooks{0}".format(num)):
        for filename in files:
            shutil.copy(os.path.join(root, filename), os.path.join(libpath, filename))
            book_count += 1
    return book_count


def _get_library(num):
    # get a user's book library
    libpath = "/tmp/ogre-test/user{0}".format(num)
    books = []
    import fnmatch
    for root, dirnames, filenames in os.walk("tests/ebooks"):
        for fn in fnmatch.filter(filenames, "*.epub"):
            books.append(os.path.join(libpath, fn))
            return books
    return books


def _delete_all():
    from ..ogreserver import app, db
    from ..ogreserver.models.user import User

    users = User.query.filter(User.email.endswith("@test")).all()
    for u in users:
        db.session.delete(u)
    db.session.commit()

    # clean up the temp directories
    if os.path.exists("/tmp/ogre-test"):
        shutil.rmtree("/tmp/ogre-test")

    import boto.sdb
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
        import subprocess
        subprocess.call(['kill', '-HUP', pid.strip()])

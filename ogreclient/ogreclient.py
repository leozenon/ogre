from __future__ import division

import getpass
import json
import os
import subprocess
import sys
import tempfile

import urllib
import urllib2
from urllib2 import HTTPError, URLError
from urllib2_file import newHTTPHandler

from utils import compute_md5

PROGBAR_LEN = 30
OGRESERVER = "www.ogre.me.uk"


def doit(ebook_home=None, username=None, password=None):
    # setup the environment
    if ebook_home is None:
        ebook_home = os.getenv("EBOOK_HOME")
        if ebook_home is None or len(ebook_home) == 0:
            print "You must set the $EBOOK_HOME environment variable"
            sys.exit(1)

    if username is None:
        username = os.getenv("EBOOK_USER")
        if username is None or len(username) == 0:
            username = getpass.getuser()
            if username is not None:
                print "$EBOOK_USER is not set. Please enter your username, or press enter to use '%s':" % username
                ri = raw_input()
                if len(ri) > 0:
                    username = ri

        if username is None:
            print "$EBOOK_USER is not set. Please enter your username, or press enter to exit:"
            username = raw_input()
            if len(username) == 0:
                sys.exit(1)

    if password is None:
        password = os.getenv("EBOOK_PASS")
        if password is None or len(password) == 0:
            print "$EBOOK_PASS is not set. Please enter your password, or press enter to exit:"
            password = getpass.getpass()
            if len(password) == 0:
                sys.exit(1)

    # setup a temp path for DRM checks with ebook-convert
    ebook_convert_path = "%s/egg.epub" % tempfile.gettempdir()

    # setup some ebook cache file paths
    config_dir = "%s/%s" % (os.environ.get('XDG_CONFIG_HOME', os.path.expanduser('~/.config')), "ogre")
    ebook_cache_path = "%s/ebook_cache" % config_dir
    ebook_cache_temp_path = "%s/ebook_cache.tmp" % config_dir
    ebook_cache = []

    # create or load the user's database of previously scanned ebooks
    if not os.path.exists(config_dir):
        print "Please note that DRM scanning means the first run of ogreclient will be much slower than subsequent runs."
        os.makedirs(config_dir)
    else:
        if os.path.exists(ebook_cache_path):
            with open(ebook_cache_path, "r") as f:
                ebook_cache = f.read().splitlines()

    try:
        # authenticate the user; retrieve an api_key for subsequent requests
        params = urllib.urlencode({
            'username': username,
            'password': password
        })
        print params
        req = urllib2.Request(url='http://%s/auth' % OGRESERVER, data=params)
        f = urllib2.urlopen(req)
        api_key = f.read()

    except (HTTPError, URLError), e:
        print "Something went wrong, contact tha spodz with..\nCode egg: %s" % e
        sys.exit(1)

    ebooks = []
    errors = []

    # a relatively quick search for all ebooks
    for root, dirs, files in os.walk(ebook_home):
        for filename in files:
            fn, ext = os.path.splitext(filename)
            if ext == ".epub" or ext == ".mobi" or ext == ".azw" or ext == ".pdf":
                filepath = os.path.join(root, filename)
                md5_tup = compute_md5(filepath)
                ebooks.append(
                    (filepath, fn, ext, md5_tup[2], md5_tup[0])
                )

    i = 0
    total = len(ebooks)
    if total == 0:
        print "No ebooks found. Is $EBOOK_HOME set correctly?"
        sys.exit(1)

    print "Scanning ebook meta data and checking DRM.."
    update_progress(0)
    ebooks_dict = {}

    # write good ebooks into the local ogre cache to skip DRM test next run
    with open(ebook_cache_temp_path, "w") as f_ogre_cache:

        # now parse all book meta data; building a complete dataset
        for item in ebooks:
            meta = subprocess.check_output(['ebook-meta', item[0]], stderr=subprocess.STDOUT)

            if meta.find("EPubException") > 0:
                # remove any corrupt
                errors.append(("Corrupt ebook", item[1] + item[2]))
                continue

            # check each ebook path for DRM, if not previously checked
            #if item[0] not in ebook_cache:
                #if test_drm(item[0], item[2][1:]):
                #    print 'okay'
                #else:
                #    print 'bad'
                #try:
                #    drmtest = subprocess.check_output(['ebook-convert', item[0], ebook_convert_path], stderr=subprocess.STDOUT)
                #    if drmtest.find("calibre.ebooks.DRMError") > 0:
                #        # remove any DRM riddled
                #        raise Exception("DRM addled")
                #except (Exception, CalledProcessError) as e:
                #    errors.append(("DRM addled ebook", item[1] + item[2]))
                #    continue

            # parse author/title
            lines = meta.split("\n")
            for line in lines:
                if "Title" in line:
                    title = line[22:]

                if "Author" in line:
                    author = line[22:]
                    cut = author.find(" [")
                    if(cut > -1):
                        author = author[0:cut]

            authortitle = "%s - %s" % (author, title)

            # check for duplicates
            if authortitle in ebooks_dict.keys() and item[2] in ebooks_dict[authortitle].keys():
                # TODO warn user on error stack
                pass
            else:
                # write file path to ogre cache
                f_ogre_cache.write("%s\n" % item[0])

                if authortitle not in ebooks_dict.keys():
                    ebooks_dict[authortitle] = {
                        'path': item[0],
                        'filename': item[1],
                        'format': item[2][1:],
                        'size': item[3],
                        'filemd5': item[4],
                        'owner': username,
                    }
                else:
                    overwrite = False

                    # upload in favoured formats: mobi, azw, pdf, epub
                    if ebooks_dict[authortitle]['format'] == "epub" and item[2][1:] in ('mobi', 'azw', 'pdf'):
                        overwrite = True
                    elif ebooks_dict[authortitle]['format'] == "pdf" and item[2][1:] in ('mobi', 'azw'):
                        overwrite = True
                    elif ebooks_dict[authortitle]['format'] == "awz" and item[2][1:] == "mobi":
                        overwrite = True

                    if overwrite:
                        ebooks_dict[authortitle] = {
                            'path': item[0],
                            'filename': item[1],
                            'format': item[2][1:],
                            'size': item[3],
                            'filemd5': item[4],
                            'owner': username,
                        }

            i += 1
            update_progress(i / total)

    sys.stdout.flush()

    print "\nFound %s ebooks" % len(ebooks_dict)

    # move the temp cache onto the real ogre cache
    statinfo = os.stat(ebook_cache_temp_path)
    if statinfo.st_size > 0:
        os.rename(ebook_cache_temp_path, ebook_cache_path)

    print "Come on sucker, lick my battery"

    if len(errors) > 0:
        print "Sadly, some errors occurred:"
        for e in errors:
            print "\t[%s] %s" % (e[0], e[1])

    try:
        # post the json array of ebook data
        params = urllib.urlencode({
            'ebooks': json.dumps(ebooks_dict),
            'total': total
        })
        req = urllib2.Request(url='http://%s/post/%s' % (OGRESERVER, urllib.quote_plus(api_key)))
        print req.get_full_url()
        req.add_data(params)
        resp = urllib2.urlopen(req)
        data = resp.read()

        response = json.loads(data)

    except ValueError as e:
        print "Something went wrong, contact tha spodz with..\nCode bacon: %s" % e
        sys.exit(1)

    except (HTTPError, URLError) as e:
        print "Something went wrong, contact tha spodz with..\nCode mushroom: %s" % e
        sys.exit(1)

    # print server messages
    for msg in response['messages']:
        if len(msg) == 2:
            print "%s %s" % msg
        else:
            print msg

    if len(response['ebooks_to_upload']) == 0:
        print "Nothing to upload.."
        sys.exit(1)

    elif len(response['ebooks_to_upload']) > 1:
        # grammatically correct messages are nice
        plural = "s"
    else:
        plural = ""

    print "Uploading %s file%s. Go make a brew." % (str(len(response['ebooks_to_upload'])), plural)

    # iterate all user's found books
    for authortitle in ebooks_dict.keys():
        # upload each requested by the server
        for upload in response['ebooks_to_upload']:
            if upload['filemd5'] == ebooks_dict[authortitle]['filemd5']:
                try:
                    f = open(ebooks_dict[authortitle]['path'], "rb")

                    # configure for uploads
                    opener = urllib2.build_opener(newHTTPHandler())

                    # build the post params
                    params = {
                        'sdb_key': upload['sdb_key'],
                        'authortitle': upload['authortitle'].encode("UTF-8"),
                        'filemd5': upload['filemd5'],
                        'version': upload['version'],
                        'format': upload['format'],
                        'ebook': f,
                    }
                    req = opener.open("http://%s/upload/%s" % (OGRESERVER, urllib.quote_plus(api_key)), params)
                    data = req.read()

                    print data

                except (HTTPError, URLError), e:
                    print "Something went wrong, contact tha spodz with..\nCode spinach: %s" % e
                    sys.exit(1)
                except IOError, e:
                    continue
                finally:
                    f.close()

    return


def update_progress(p):
    i = round(p * 100, 1)
    sys.stdout.write("\r[{0}{1}] {2}%".format("#" * int(p * PROGBAR_LEN), " " * (PROGBAR_LEN - int(p * PROGBAR_LEN)), i))


def test_drm(filepath, fmt):
    pass
    #if fmt == "epub":
    #    from epub_input import EPUBInput
    #    epub = EPUBInput()
    #    epub.convert(filepath)

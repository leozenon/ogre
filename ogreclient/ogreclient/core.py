from __future__ import division

import json
import os
import shutil
import subprocess
import sys

import urllib
import urllib2
from urllib2 import HTTPError, URLError
from urllib2_file import newHTTPHandler

from utils import compute_md5
from utils import id_generator
from utils import make_temp_directory
from utils import update_progress


PROGBAR_LEN = 30
OGRESERVER = "ogre.oii.me.uk"

# ranked ebook formats
EBOOK_FORMATS = {
    'mobi': 1,
    'azw3': 2,
    'azw': 3,
    'pdf': 4,
    'epub': 5,
}


def doit(ebook_home, username, password,
         ogreserver=None, config_dir=None, ebook_cache_path=None,
         ebook_cache_temp_path=None, ebook_convert_path=None,
         calibre_ebook_meta_bin=None):

    if ogreserver is not None:
        OGRESERVER = ogreserver

    ebook_cache = []

    # load the user's database of previously scanned ebooks
    if os.path.exists(ebook_cache_path):
        with open(ebook_cache_path, "r") as f:
            ebook_cache = f.read().splitlines()

    try:
        # authenticate the user; retrieve an api_key for subsequent requests
        params = urllib.urlencode({
            'username': username,
            'password': password
        })
        req = urllib2.Request(url='http://{0}/auth'.format(OGRESERVER), data=params)
        print req.get_full_url()
        f = urllib2.urlopen(req)
        api_key = f.read()

    except HTTPError as e:
        if e.getcode() == 403:
            print "Permission denied. This is a private system."
            sys.exit(2)
        else:
            print "Something went wrong, contact tha spodz with..\nCode egg: {0}".format(e)
            sys.exit(1)
    except URLError as e:
        print "Something went wrong, contact tha spodz with..\nCode egg: {0}".format(e)
        sys.exit(1)

    ebooks = []
    errors = []

    # a relatively quick search for all ebooks
    for root, dirs, files in os.walk(ebook_home):
        for filename in files:
            # TODO use timeit; compare to fnmatch.filter
            fn, ext = os.path.splitext(filename)
            if ext[1:] in EBOOK_FORMATS.keys():
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
    update_progress(0, length=PROGBAR_LEN)
    ebooks_dict = {}

    # write good ebooks into the local ogre cache to skip DRM test next run
    with open(ebook_cache_temp_path, "w") as f_ogre_cache:

        # now parse all book meta data; building a complete dataset
        for item in ebooks:
            extracted = subprocess.check_output(
                [calibre_ebook_meta_bin, item[0]], stderr=subprocess.STDOUT
            )

            if extracted.find("EPubException") > 0:
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

            # initialize all the metadata we attempt to extract
            meta = {}
            for prop in ('title', 'author', 'firstname', 'lastname', 'publisher',
                         'published', 'tags', 'isbn', 'asin', 'uri', 'ogre_id', 'dedrm'):
                meta[prop] = None

            for line in extracted.splitlines():
                # extract the simple metadata
                for prop in ('title', 'publisher', 'published'):
                    if line.lower().startswith(prop):
                        meta[prop] = line[line.find(':')+1:].strip()

                if 'Tags' in line:
                    meta['tags'] = line[line.find(':')+1:].strip()

                    # extract the ogre_id which may be embedded into the tags field
                    if 'ogre_id' in meta['tags']:
                        tags = meta['tags'].split(', ')
                        for j in reversed(xrange(len(tags))):
                            if 'ogre_id' in tags[j]:
                                meta['ogre_id'] = tags[j][8:]
                                del(tags[j])
                        meta['tags'] = ', '.join(tags)

                    # extract the DeDRM flag
                    #if 'DeDRM' in meta['tags']:
                    #    import pdb;pdb.set_trace()
                    #    tags = meta['tags'].split(', ')
                    #    for j in reversed(xrange(len(tags))):
                    #        if 'DeDRM' in tags[j]:
                    #            meta['dedrm'] = tags[j][6:]
                    #            del(tags[j])
                    #    meta['tags'] = ', '.join(tags)

                if 'Author' in line:
                    meta['author'] = line[line.find(':')+1:].strip()
                    bracketpos = meta['author'].find('[')
                    if(bracketpos > -1):
                        commapos = meta['author'].find(',', bracketpos)
                        meta['lastname'] = meta['author'][bracketpos+1:commapos]
                        meta['firstname'] = meta['author'][commapos+1:-1].strip()
                        meta['author'] = meta['author'][0:bracketpos].strip()

                if 'Identifiers' in line:
                    identifiers = line[line.find(':')+1:].strip()
                    for ident in identifiers.split(","):
                        if ident.startswith("isbn"):
                            meta['isbn'] = ident[5:].strip()
                        if ident.startswith("mobi-asin"):
                            meta['asin'] = ident[9:].strip()
                        if ident.startswith("uri"):
                            meta['uri'] = ident[3:].strip()
                        if ident.startswith("epubbud"):
                            meta['uri'] = ident[7:].strip()

            # books are indexed by "authortitle" to handle multiple copies of the same book
            authortitle = "{0} - {1}".format(meta['author'], meta['title'])

            # check for duplicates
            if authortitle in ebooks_dict.keys() and item[2] in ebooks_dict[authortitle].keys():
                # TODO warn user on error stack
                pass
            else:
                # write file path to ogre cache
                # TODO move this to where the ogre_id gets confirmed
                f_ogre_cache.write("%s\n" % item[0])

                # another format of same book found
                write = False

                if authortitle in ebooks_dict.keys():
                    # compare the rank of the format already found against this one
                    existing_rank = EBOOK_FORMATS[ebooks_dict[authortitle]['format']]
                    new_rank = EBOOK_FORMATS[item[2][1:]]

                    # lower is better
                    if new_rank < existing_rank:
                        write = True

                    # upload in favoured formats: mobi, azw, pdf, epub
                    #if ebooks_dict[authortitle]['format'] == "epub" and item[2][1:] in ('mobi', 'azw3', 'azw', 'pdf'):
                    #    write = True
                    #elif ebooks_dict[authortitle]['format'] == "pdf" and item[2][1:] in ('mobi', 'azw3', 'azw'):
                    #    write = True
                    #elif ebooks_dict[authortitle]['format'] == "pdf" and item[2][1:] in ('mobi', 'azw3'):
                    #    write = True
                    #elif ebooks_dict[authortitle]['format'] == "awz" and item[2][1:] in ('mobi'):
                    #    write = True
                else:
                    # new book found
                    write = True

                if write:
                    ebooks_dict[authortitle] = {
                        'path': item[0],
                        'filename': item[1],
                        'format': item[2][1:],
                        'size': item[3],
                        'file_md5': item[4],
                        'owner': username,
                    }
                    # merge all the meta data constructed above
                    ebooks_dict[authortitle].update(meta)

            i += 1
            update_progress(float(i) / float(total), length=PROGBAR_LEN)

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
        req = urllib2.Request(
            url='http://{0}/post/{1}'.format(
                OGRESERVER,
                urllib.quote_plus(api_key)
            )
        )
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

    # grammatically correct messages are nice
    plural = "s" if len(response['ebooks_to_upload']) > 1 else ""

    print "Uploading %s file%s. Go make a brew." % (str(len(response['ebooks_to_upload'])), plural)

    # tag each book with ogre supplied ebook_id
    for newbook in response['new_books']:
        # find this book in the scan data
        for authortitle in ebooks_dict.keys():
            if newbook['file_md5'] == ebooks_dict[authortitle]['file_md5']:
                # append ogre's ebook_id to the tags list
                if 'tags' in ebooks_dict[authortitle]:
                    new_tags = "{0}, ogre_id={1}".format(
                        ebooks_dict[authortitle]['tags'], newbook['ebook_id']
                    )
                else:
                    new_tags = "ogre_id={0}".format(newbook['ebook_id'])

                with make_temp_directory() as temp_dir:
                    # copy the ebook to a temp file
                    tmp_name = "{0}.{1}".format(
                        os.path.join(temp_dir, id_generator()), 
                        ebooks_dict[authortitle]['format']
                    )
                    shutil.copy(newbook['path'], tmp_name)
                    # write new tags
                    subprocess.check_output(
                        [calibre_ebook_meta_bin, tmp_name, '--tags', new_tags]
                    )
                    # calculate new MD5
                    md5 = compute_md5(tmp_name)[0]
                    try:
                        # ping ogreserver with the book's new hash
                        req = urllib2.Request(
                            url='http://{0}/confirm/{1}'.format(
                                OGRESERVER,
                                urllib.quote_plus(api_key)
                            )
                        )
                        req.add_data(urllib.urlencode({
                            'file_md5': newbook['file_md5'],
                            'new_md5': md5
                        }))
                        resp = urllib2.urlopen(req)
                        data = resp.read()

                        if data == "ok":
                            # move file back into place
                            shutil.copy(tmp_name, newbook['path'])

                    except (HTTPError, URLError) as e:
                        # TODO
                        pass

    # upload each requested by the server
    for upload in response['ebooks_to_upload']:
        # iterate all user's found books
        for authortitle in ebooks_dict.keys():
            if upload['file_md5'] == ebooks_dict[authortitle]['file_md5']:
                try:
                    f = open(ebooks_dict[authortitle]['path'], "rb")

                    # configure for uploads
                    opener = urllib2.build_opener(newHTTPHandler())

                    # build the post params
                    params = {
                        'ebook_id': upload['ebook_id'],
                        'file_md5': upload['file_md5'],
                        'format': upload['format'],
                        'ebook': f,
                    }
                    req = opener.open(
                        "http://{0}/upload/{1}".format(OGRESERVER, urllib.quote_plus(api_key)), params
                    )
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


def test_drm(filepath, fmt):
    pass
    #if fmt == "epub":
    #    from epub_input import EPUBInput
    #    epub = EPUBInput()
    #    epub.convert(filepath)

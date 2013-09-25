from __future__ import division

import datetime
import json
import os
import shutil
import subprocess
import sys

import urllib
import urllib2
from urllib2 import HTTPError, URLError
from urllib2_file import newHTTPHandler

from utils import capture
from utils import compute_md5
from utils import id_generator
from utils import make_temp_directory
from utils import update_progress
from utils import CliPrinter
from utils import enum


PROGBAR_LEN = 30
OGRESERVER = "ogre.oii.yt"

# ranked ebook formats
EBOOK_FORMATS = {
    'mobi': 1,
    'azw': 2,
    'azw3': 3,
    'azw4': 4,
    'pdf': 5,
    'epub': 6,
    'pdb': 7,
    'azw1': 8,
    'tpz': 9,
}

DRM = enum('unknown', 'decrypted', 'none', 'wrong_key', 'failed', 'corrupt')


ERROR_AUTH = 1
ERROR_BACON = 2
ERROR_MUSHROOM = 4
ERROR_SPINACH = 8
AUTH_DENIED = 16
NO_EBOOKS = 32
NO_UPLOADS = 64

last_error = None

def authenticate(host, username, password):
    global last_error
    try:
        # authenticate the user; retrieve an session_key for subsequent requests
        params = urllib.urlencode({
            'username': username,
            'password': password
        })
        req = urllib2.Request(url='http://{0}/auth'.format(host), data=params)
        f = urllib2.urlopen(req)
        return f.read()

    except HTTPError as e:
        if e.getcode() == 403:
            return AUTH_DENIED
        else:
            last_error = e
            return ERROR_AUTH
    except URLError as e:
        last_error = e
        return ERROR_AUTH


def doit(ebook_home, username, password,
         ogreserver=None, config_dir=None, ebook_cache_path=None,
         ebook_cache_temp_path=None, ebook_convert_path=None,
         calibre_ebook_meta_bin=None, verbose=False, quiet=False):

    global last_error

    if ogreserver is None:
        ogreserver = OGRESERVER

    ebook_cache = []

    # load the user's database of previously scanned ebooks
    if os.path.exists(ebook_cache_path):
        with open(ebook_cache_path, "r") as f:
            data = f.read()
            #ebook_cache = json.loads(data)

    # authenticate user and generate session API key
    ret = authenticate(ogreserver, username, password)
    if ret in (ERROR_AUTH, AUTH_DENIED):
        return ret
    else:
        session_key = ret

    ebooks = []

    prntr = CliPrinter(datetime.datetime.now(), quiet=quiet)

    # let the user know something is happening
    prntr.p("Searching for ebooks.. ", nonl=True)

    # a relatively quick search for all ebooks
    for root, dirs, files in os.walk(ebook_home):
        for filename in files:
            # TODO use timeit; compare to fnmatch.filter
            fn, ext = os.path.splitext(filename)
            if ext[1:] in EBOOK_FORMATS.keys() and fn[0:2] != '._':
                filepath = os.path.join(root, filename)
                md5_tup = compute_md5(filepath)
                ebooks.append(
                    (filepath, fn, ext, md5_tup[2], md5_tup[0])
                )

    i = 0
    total = len(ebooks)
    prntr.p("Discovered {0} files".format(total))
    if total == 0:
        return NO_EBOOKS

    prntr.p("Scanning ebook meta data and checking DRM..")
    #update_progress(0, length=PROGBAR_LEN)
    ebooks_dict = {}
    can_decrypt = None

    try:
        # import DeDRM libs, capturing anything that's shat out on STDOUT
        with capture() as out:
            from dedrm.scriptinterface import decryptepub, decryptpdf, decryptpdb, decryptk4mobi
        can_decrypt = True
    except ImportError:
        can_decrypt = False

    # write good ebooks into the local ogre cache to skip DRM test next run
    with open(ebook_cache_temp_path, "w") as f_ogre_cache:

        # now parse all book meta data; building a complete dataset
        for item in ebooks:
            extracted = subprocess.check_output(
                [calibre_ebook_meta_bin, item[0]], stderr=subprocess.STDOUT
            )

            if extracted.find("EPubException") > 0:
                # remove any corrupt
                if verbose:
                    prntr.e("{0}{1}".format(item[1], item[2]), CliPrinter.CORRUPT)
                continue

            if can_decrypt:
                try:
                    out = ""
                    # attempt to decrypt each book, capturing STDOUT
                    with capture() as out:
                        if item[2] == '.epub':
                            decryptepub(item[0], ebook_convert_path, config_dir)
                        elif item[2] == '.pdb':
                            decryptpdb(item[0], ebook_convert_path, config_dir)
                        elif item[2] in ('.mobi', '.azw', '.azw1', '.azw3', '.azw4', '.tpz'):
                            decryptk4mobi(item[0], ebook_convert_path, config_dir)
                        elif item[2] == '.pdf':
                            decryptpdf(item[0], ebook_convert_path, config_dir)

                    # decryption state of current book
                    state = DRM.unknown

                    if item[2] == '.epub':
                        for line in out:
                            if ' is not DRMed.' in line:
                                state = DRM.none
                                break
                            elif 'Decrypted Adobe ePub' in line:
                                state = DRM.decrypted
                                break
                            elif 'Could not decrypt' in line and 'Wrong key' in line:
                                state = DRM.wrong_key
                                break
                            elif 'Error while trying to fix epub' in line:
                                state = DRM.corrupt
                                break
                    elif item[2] in ('.mobi', '.azw', '.azw1', '.azw3', '.azw4', '.tpz'):
                        for line in out:
                            if 'This book is not encrypted.' in line:
                                state = DRM.none
                                break
                            elif 'Decryption succeeded' in line:
                                state = DRM.decrypted
                                break
                            elif 'DrmException: No key found' in line:
                                state = DRM.wrong_key
                                break
                    elif item[2] == '.pdf':
                        state = DRM.none
                        for line in out:
                            if 'Error serializing pdf' in line:
                                state = DRM.failed
                                break

                    if verbose:
                        if state == DRM.none:
                            prntr.p("{0}".format(item[0]), CliPrinter.NONE)
                        elif state == DRM.decrypted:
                            prntr.p("{0}".format(item[0]), CliPrinter.DEDRM, success=True)
                        elif state == DRM.wrong_key:
                            prntr.e("{0}".format(item[0]), CliPrinter.WRONG_KEY)
                        elif state == DRM.failed:
                            prntr.e("{0}".format(item[0]), CliPrinter.DEDRM,
                                extra=' '.join([l.strip() for l in out])
                            )
                        elif state == DRM.corrupt:
                            prntr.e("{0}".format(item[0]), CliPrinter.CORRUPT)
                        else:
                            prntr.p("{0}\t{1}".format(item[0], out), CliPrinter.UNKNOWN)

                except Exception as e:
                    prntr.e("Fatal Exception on {0}".format(item[0]), excp=e)
                    continue

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
            #update_progress(float(i) / float(total), length=PROGBAR_LEN)

    prntr.p("\nFound {0} ebooks".format(len(ebooks_dict)))

    # move the temp cache onto the real ogre cache
    statinfo = os.stat(ebook_cache_temp_path)
    if statinfo.st_size > 0:
        os.rename(ebook_cache_temp_path, ebook_cache_path)

    prntr.p("Come on sucker, lick my battery")

    try:
        # post the json array of ebook data
        params = urllib.urlencode({
            'ebooks': json.dumps(ebooks_dict),
            'total': total
        })
        req = urllib2.Request(
            url='http://{0}/post/{1}'.format(
                ogreserver,
                urllib.quote_plus(session_key)
            )
        )
        req.add_data(params)
        resp = urllib2.urlopen(req)
        data = resp.read()

        response = json.loads(data)

    except ValueError as e:
        last_error = e
        return ERROR_BACON
    except (HTTPError, URLError) as e:
        last_error = e
        return ERROR_MUSHROOM

    # display server messages
    for msg in response['messages']:
        if len(msg) == 2:
            prntr.p("{0} {1}".format(msg[0], msg[1]), CliPrinter.RESPONSE)
        else:
            prntr.p(msg, CliPrinter.RESPONSE)

    if len(response['ebooks_to_upload']) == 0:
        return NO_UPLOADS

    # grammatically correct messages are nice
    plural = "s" if len(response['ebooks_to_upload']) > 1 else ""

    prntr.p("Uploading {0} file{1}. Go make a brew.".format(len(response['ebooks_to_upload']), plural))

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
                                ogreserver,
                                urllib.quote_plus(session_key)
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
                        "http://{0}/upload/{1}".format(ogreserver, urllib.quote_plus(session_key)), params
                    )
                    data = req.read()

                    prntr.p(data)

                except (HTTPError, URLError), e:
                    last_error = e
                    return ERROR_SPINACH
                except IOError, e:
                    continue
                finally:
                    f.close()

import datetime
import hashlib
import json
import re

import boto
from boto.exception import S3ResponseError

from whoosh.qparser import MultifieldParser, OrGroup

from ogreserver import app, whoosh
from ogreserver.models.user import User


class DataStore():
    def __init__(self, user):
        self.user = user

    def update_library(self, ebooks):
        """
        The core library synchronisation method.
        An array of ebook metadata and file hashes is supplied by each client and synchronised
        against the contents of the Amazon SDB database.
        """
        new_ebook_count = 0
        sdb = boto.connect_sdb(app.config['AWS_ACCESS_KEY'], app.config['AWS_SECRET_KEY'])
        domain = sdb.get_domain("ogre_ebooks")

        lib_updated = False

        for authortitle in ebooks.keys():
            #try:
            # first check if this exact file has been uploaded before
            found_duplicate = False

            if DataStore.check_ebook_exists(ebooks[authortitle]['filemd5']) == True:
                found_duplicate = True
                # TODO any way we can import meta data from this book?

            if found_duplicate == True:
                print "ignoring exact duplicate %s" % authortitle
                continue

            # check for this book by meta data in the library
            bkey = DataStore.build_ebook_key(authortitle)
            b = domain.get_item(bkey)

            if b is None:
                # create this as a new book
                ebook_data = {
                    'authortitle': authortitle,
                    'formats': ebooks[authortitle]['format'],
                    'versions': {},
                    'rating': None,
                    'comments': None,
                }
                # add the first version
                ebook_data['versions']['1'] = self.create_ebook_version_object(1,
                    ebooks[authortitle]['size'],
                    ebooks[authortitle]['format'],
                    ebooks[authortitle]['filemd5']
                )
                new_ebook_count += 1

                self.create_ebook(ebook_data, self.user.username, ebooks[authortitle]['filemd5'])

                lib_updated = True
            else:
                # parse the ebook data
                ebook_data = json.loads(b['data'])

                # reject if this user has uploaded another version of this book before
                for version_id in ebook_data['versions']:
                    if ebook_data['versions'][version_id]['user'] == self.user.username:
                        print "rejecting alternate format of existing book"
                        continue

                # calculate the next highest version number
                version_nums = [int(n) for n in ebook_data['versions'].keys()]
                next_version = max(version_nums) + 1

                # TODO favour mobi format in uploads.. epub after that - dont upload multiple formats of same book
                # test user upload of a mobi, then same user tries to upload epub version
                # then user could upload a re-mobi of that book - which becomes a new version

                # add another version of this ebook
                ebook_data['versions'][next_version] = self.create_ebook_version_object(
                    next_version,
                    ebooks[authortitle]['size'],
                    ebooks[authortitle]['format'],
                    ebooks[authortitle]['filemd5']
                )
                print json.dumps(ebook_data, indent=2)

                new_ebook_count += 1

                # add user to set of owners
                if self.user.username not in b['users']:
                    b.add_value("users", self.user.username)

                # TODO version popularity determines which formats appear on ebook base top-level
                # popularity += 1 for download
                # popularity += 1 for new owner
                # use quality as co-efficient when calculating most popular
                # quality in 5 segments, (-0.5,-0.25,0,0.25,0.5)

                # append to the set of this book's formats
                if ebooks[authortitle]['format'] not in b['formats']:
                    b.add_value("formats", ebooks[authortitle]['format'])

                # write book into SDB
                b['data'] = json.dumps(ebook_data)
                b.save()

                lib_updated = True

            #except Exception as e:
            #    print "[EXCP] %s" % authortitle
            #    print "\t%s: %s" % (type(e), e)

        if lib_updated:
            DataStore.update_library_timestamp()

        return new_ebook_count

    def create_ebook_version_object(self, num, size, fmt, filemd5):
        """
        Create an object to represent a single version of an ebook
        """
        return {
            'version': num,
            'user': self.user.username,
            'size': size,
            'popularity': 1,
            'quality': 0,
            'original_format': fmt,
            'formats': {
                fmt: {
                    'filemd5': filemd5,
                    'uploaded': 0,
                }
            }
        }

    def create_ebook(self, data, creator, hashes):
        """
        Create and store a new ebook entry with it's version info encoded as a json
        object in the 'data' param.
        """
        sdb = boto.connect_sdb(app.config['AWS_ACCESS_KEY'], app.config['AWS_SECRET_KEY'])
        domain = sdb.get_domain("ogre_ebooks")

        key = DataStore.build_ebook_key(data['authortitle'])
        obj = domain.new_item(key)

        obj['data'] = json.dumps(data)
        obj['users'] = creator
        obj['hashes'] = hashes
        obj['all_uploaded'] = "false"
        obj['sdb_key'] = key
        obj.save()

        # add info about this book to the search index
        parts = data['authortitle'].split(" - ")
        writer = whoosh.writer()
        try:
            writer.add_document(sdb_key=unicode(key), author=parts[0], title=parts[1])
            writer.commit()
        except Exception as e:
            print e

        return key


    def list(self):
        return self.search("")

    def search(self, searchstr):
        """
        Search for books using whoosh
        """
        output = []

        qp = MultifieldParser(["author", "title"], whoosh.schema, group=OrGroup)
        query = qp.parse(searchstr)

        with whoosh.searcher() as s:
            results = s.search(query)
            for r in results:
                output.append(r.fields())

        return output


    @staticmethod
    def check_ebook_exists(filemd5):
        """
        Check if this specific version's hash exists in any known ebook
        """
        sdb = boto.connect_sdb(app.config['AWS_ACCESS_KEY'], app.config['AWS_SECRET_KEY'])
        rs = sdb.select("ogre_ebooks", "select itemName() from ogre_ebooks where hashes = '{0}'".format(filemd5))
        return (len(rs) > 0)

    @staticmethod
    def _get_single_ebook(sdb_key, for_update=False):
        """
        Retrieve an ebook from Amazon SDB.
        The for_update parameter alter the return to be a tuple containing the boto
        object which allows you to update and save the ebook
        """
        sdb = boto.connect_sdb(app.config['AWS_ACCESS_KEY'], app.config['AWS_SECRET_KEY'])
        domain = sdb.get_domain("ogre_ebooks")
        b = domain.get_item(sdb_key)
        if b is None:
            raise Exception("Unknown key %s" % sdb_key)
        if for_update:
            return json.loads(b['data']), b
        else:
            return json.loads(b['data'])

    @staticmethod
    def get_rating(sdb_key):
        """
        Get the user rating for this book
        """
        return DataStore._get_single_ebook(sdb_key)['rating']

    @staticmethod
    def get_comments(sdb_key):
        """
        Get the list of comments on this book
        """
        comments = DataStore._get_single_ebook(sdb_key)['comments']
        if comments is None:
            return []
        else:
            return comments

    @staticmethod
    def build_ebook_key(authortitle):
        """
        Generate a key for this ebook from the author and title
        This is used as the ebook's key in Amazon SDB - referred to as sdb_key in code
        """
        return hashlib.md5((authortitle).encode("UTF-8")).hexdigest()

    @staticmethod
    def versions_rank_algorithm(version):
        """
        Generate a score for this version of an ebook

        The quality % score and the popularity score are ratioed together 70:30
        Since popularity is a scalar and can grow indefinitely it's divided
        by our num of total system users
        """
        total_users = User.get_total_users()
        return (version['quality'] * 0.7) + ((float(version['popularity']) / total_users) * 100 * 0.3)

    @staticmethod
    def get_ebook_url(sdb_key, fmt=None, version=None):
        """
        Generate a download URL for the requested ebook

        If a version isn't requested the top-ranked one will be supplied.
        If a format isn't requested one will be served in the order defined in EBOOK_FORMATS
        """
        ebook_data = DataStore._get_single_ebook(sdb_key)

        if version is None:
            # sort this book's versions by quality & popularity
            versions = sorted(ebook_data['versions'].values(),
                key=lambda v: DataStore.versions_rank_algorithm(v),
                reverse=True
            )

            if fmt is None:
                # serve the OGRE preferred format from top-ranked version (versions[0])
                v = versions[0]
                for ebook_fmt in app.config['EBOOK_FORMATS']:
                    if ebook_fmt in v['formats']:
                        fmt = ebook_fmt
                        break
            else:
                # serve the requested format from best version possible
                for v in versions:
                    if fmt in v['formats'].keys():
                        break
        else:
            # get the specific requested version
            v = ebook_data['versions'][version]

            if fmt is None:
                # serve the OGRE preferred format from top-ranked version (versions[0])
                for ebook_fmt in app.config['EBOOK_FORMATS']:
                    if ebook_fmt in v['formats']:
                        fmt = ebook_fmt
                        break
            else:
                # verify requested format is available on requested version
                try:
                    v['formats'][fmt]['filemd5'],
                except KeyError:
                    raise Exception("Requested format not available on requested version.")

        # generate the filename - which is the key on S3
        filename = DataStore.generate_filename(
            ebook_data['authortitle'],
            v['formats'][fmt]['filemd5'],
            fmt
        )

        s3 = boto.connect_s3(app.config['AWS_ACCESS_KEY'], app.config['AWS_SECRET_KEY'])
        return s3.generate_url(app.config['DOWNLOAD_LINK_EXPIRY'], 'GET',
            bucket=app.config['S3_BUCKET'],
            key=filename
        )

    @staticmethod
    def set_uploaded(sdb_key, version, fmt, isit=True):
        """
        Mark an ebook as having been uploaded to S3
        """
        ebook_data, b = DataStore._get_single_ebook(sdb_key, for_update=True)
        if isit == False:
            ebook_data['versions'][version]['formats'][fmt]['uploaded'] = False
        else:
            ebook_data['versions'][version]['formats'][fmt]['uploaded'] = True
        b['data'] = json.dumps(ebook_data)
        b.save()

    @staticmethod
    def set_dedrm_flag(sdb_key, fmt):
        """
        Mark a book as having had DRM removed
        """
        ebook_data, b = DataStore._get_single_ebook(sdb_key, for_update=True)
        ebook_data['formats']['fmt']['dedrm'] = None
        b['data'] = json.dumps(ebook_data)
        b.save()

    @staticmethod
    def store_ebook(sdb_key, filemd5, filename, filepath, version, fmt):
        """
        Store an ebook on S3
        """
        s3 = boto.connect_s3(app.config['AWS_ACCESS_KEY'], app.config['AWS_SECRET_KEY'])
        bucket = s3.get_bucket(app.config['S3_BUCKET'])

        # create a new storage key
        k = boto.s3.key.Key(bucket)
        k.key = filename

        # check if our file is already up on S3
        if k.exists():
            k = bucket.get_key(filename)
            # TODO look for bug in get_metadata()
            metadata = k._get_remote_metadata()
            if 'x-amz-meta-ogre-key' in metadata and metadata['x-amz-meta-ogre-key'] == sdb_key:
                DataStore.set_uploaded(sdb_key, version, fmt)
                return False

        # calculate uploaded file md5
        f = open(filepath, "rb")
        md5_tup = k.compute_md5(f)
        f.close()

        # error check uploaded file
        if filemd5 != md5_tup[0]:
            # TODO logging
            raise S3DatastoreError("Upload failed checksum 1")
        else:
            try:
                # TODO time this and print
                # push file to S3
                k.set_contents_from_filename(filepath,
                    headers={'x-amz-meta-ogre-key': sdb_key},
                    md5=md5_tup,
                )

                # mark ebook as stored
                DataStore.set_uploaded(sdb_key, version, fmt)

            except S3ResponseError:
                # TODO log
                raise S3DatastoreError("Upload failed checksum 2")

        return True

    @staticmethod
    def generate_filename(authortitle, filemd5, fmt):
        """
        Generate the filename for a book on its way to S3
        """
        # TODO transpose unicode
        return "{0}.{1}.{2}".format(re.sub("[^a-zA-Z0-9]", "_", authortitle), filemd5[0:6], fmt)

    @staticmethod
    def get_missing_books(username=None, verify_s3=False):
        """
        Query Amazon SDB for books marked as not uploaded

        The verify_s3 flag enables a further check to be run against S3 to ensure 
        the file is actually there
        """
        sdb = boto.connect_sdb(app.config['AWS_ACCESS_KEY'], app.config['AWS_SECRET_KEY'])

        if username is not None:
            if verify_s3 == True:
                rs = sdb.select("ogre_ebooks", "select sdb_key, data from ogre_ebooks where users = '%s'" % username)
            else:
                rs = sdb.select("ogre_ebooks", "select sdb_key, data from ogre_ebooks where all_uploaded = 'false' and users = '%s'" % username)
        else:
            if verify_s3 == True:
                raise Exception("Can't verify entire library in one go.")
            else:
                rs = sdb.select("ogre_ebooks", "select sdb_key, data from ogre_ebooks where all_uploaded = 'false'")

        output = []

        # flatten for output
        for ebook in rs:
            ebook_data = json.loads(ebook['data'])
            for v in ebook_data['versions']:
                version = ebook_data['versions'][v]
                for fmt in version['formats']:
                    output.append({
                        'sdb_key': ebook['sdb_key'],
                        'authortitle': ebook_data['authortitle'],
                        'filemd5': version['formats'][fmt]['filemd5'], 
                        'version': v,
                        'format': fmt,
                    })

        if verify_s3 == True:
            # connect to S3
            s3 = boto.connect_s3(app.config['AWS_ACCESS_KEY'], app.config['AWS_SECRET_KEY'])
            bucket = s3.get_bucket(app.config['S3_BUCKET'])

            # verify books are on S3
            for b in output:
                filename = DataStore.generate_filename(b['authortitle'], b['filemd5'], b['format'])
                k = boto.s3.key.Key(bucket, filename)
                DataStore.set_uploaded(b['sdb_key'], b['version'], b['format'], k.exists())
                # TODO update rs when verify=True

        return output

    @staticmethod
    def update_library_timestamp():
        """
        Tag the Amazon SDB bucket with timestamp meta data
        """
        sdb = boto.connect_sdb(app.config['AWS_ACCESS_KEY'], app.config['AWS_SECRET_KEY'])
        domain = sdb.get_domain("ogre_ebooks")

        # set library updated timestamp
        meta = domain.get_item("meta")
        if meta == None:
            meta = domain.new_item("meta")

        meta['updated'] = datetime.datetime.utcnow().isoformat()
        meta.save()


class S3DatastoreError(Exception):
    pass

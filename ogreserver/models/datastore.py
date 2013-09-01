import datetime
import hashlib
import json
import re

import rethinkdb as r

import boto
import boto.sdb
from boto.exception import S3ResponseError

from whoosh.query import Every
from whoosh.qparser import MultifieldParser, OrGroup

from .. import app, whoosh
from user import User


class DataStore():
    def __init__(self, user):
        self.user = user

    def update_library(self, ebooks):
        """
        The core library synchronisation method.
        A dict containing ebook metadata and file hashes is sent by each client
        and synchronised against the contents of the OGRE database.
        """
        output = []

        conn = r.connect("localhost", 28015, db="ogreserver")

        lib_updated = False

        for authortitle in ebooks.keys():
            #try:
            incoming = ebooks[authortitle]

            # first check if this exact file has been uploaded before
            # query formats table by key, joining to versions to get ebook pk
            res = r.table('formats').filter(
                {'id': incoming['file_md5']}
            ).eq_join(
                'version_id', r.table('versions')
            ).zip().run(conn)

            if len(list(res)) > 0:
                print "Ignoring exact duplicate {0}".format(authortitle.encode("UTF-8"))
                continue

            elif incoming['ogre_id'] is None:
                # TODO file hash match, with no ogre_id is an exception
                pass

            # create firstname, lastname (these are often the wrong way around)
            if 'firstname' in incoming:
                firstname = incoming['firstname']
                lastname = incoming['lastname']
            else:
                firstname, lastname = incoming['author'].split(',')

            # check for this book by meta data in the library
            ebook_id = DataStore.build_ebook_key(lastname, firstname, incoming['title'])
            existing = r.table('ebooks').get(ebook_id).run(conn)

            if existing is None:
                # create this as a new book
                new_book = {
                    'id': ebook_id,
                    'title': incoming['title'],
                    'firstname': firstname,
                    'lastname': lastname,
                    'rating': None,
                    'comments': [],
                    'publisher': incoming['publisher'] if 'publisher' in incoming else None,
                    'publish_date': incoming['published'] if 'published' in incoming else None,
                    'meta': {
                        'isbn': incoming['isbn'] if 'isbn' in incoming else None,
                        'asin': incoming['asin'] if 'asin' in incoming else None,
                        'uri': incoming['uri'] if 'uri' in incoming else None,
                        'raw_tags': incoming['tags'] if 'tags' in incoming else None,
                    },
                }
                r.table('ebooks').insert(new_book).run(conn)

                # add the first version
                new_version = {
                    'ebook_id': ebook_id,
                    'user': self.user.username,
                    'size': incoming['size'],
                    'popularity': 1,
                    'quality': 0,
                    'original_format': incoming['format'],
                }
                ret = r.table('versions').insert(new_version).run(conn)

                new_format = {
                    'id': incoming['file_md5'],
                    'version_id': ret['generated_keys'][0],
                    'format': incoming['format'],
                    'uploaded': False,
                    'source_patched': False,
                }
                r.table('formats').insert(new_format).run(conn)

                # return a list of new books to the client
                output.append({
                    'ebook_id': ebook_id,
                    'path': incoming['path'],
                    'file_md5': incoming['file_md5'],
                })
                lib_updated = True

                # update the whoosh text search interface
                self.index_for_search(new_book)

            else:
                # parse the ebook data
                other_versions = r.table('versions').filter(
                    {'ebook_id': ebook_id, 'user': self.user.username}
                ).count().run(conn)

                if other_versions > 0:
                    print "Rejecting new version of {0} from {1}".format(
                        authortitle.encode("UTF-8"), self.user.username
                    )
                    continue

                # TODO favour mobi format in uploads.. epub after that - dont upload multiple formats of same book
                # test user upload of a mobi, then same user tries to upload epub version
                # then user could upload a re-mobi of that book - which becomes a new version

                new_version = {
                    'ebook_id': ebook_id,
                    'user': self.user.username,
                    'size': incoming['size'],
                    'popularity': 1,
                    'quality': 0,
                    'original_format': incoming['format'],
                }
                ret = r.table('versions').insert(new_version).run(conn)

                new_format = {
                    'id': incoming['file_md5'],
                    'ebook_id': ebook_id,
                    'version_id': ret['generated_keys'][0],
                    'format': incoming['format'],
                    'uploaded': False,
                }
                r.table('formats').insert(new_format).run(conn)

                #print json.dumps(existing, indent=2)

                output.append({
                    'ebook_id': ebook_id,
                    'path': incoming['path'],
                    'file_md5': incoming['file_md5'],
                })
                lib_updated = True

                # TODO version popularity determines which formats appear on ebook base top-level
                # popularity += 1 for download
                # popularity += 1 for new owner
                # use quality as co-efficient when calculating most popular
                # see: versions_rank_algorithm()

            #except Exception as e:
            #    print "[EXCP] %s" % authortitle
            #    print "\t%s: %s" % (type(e), e)

        return output


    def index_for_search(self, book_data):
        author = " ".join((book_data['firstname'], book_data['lastname']))
        title = book_data['title']

        # add info about this book to the search index
        writer = whoosh.writer()
        try:
            writer.add_document(ebook_id=unicode(book_data['id']), author=author, title=title)
            writer.commit()
        except Exception as e:
            print e


    def list(self):
        """
        List all books from whoosh
        """
        return self.search(None)

    def search(self, searchstr):
        """
        Search for books using whoosh
        """
        output = []

        if searchstr is None:
            query = Every('author')
        else:
            qp = MultifieldParser(['author', 'title'], whoosh.schema, group=OrGroup)
            query = qp.parse(searchstr)

        with whoosh.searcher() as s:
            results = s.search(query)
            for r in results:
                output.append(r.fields())

        return output


    @staticmethod
    def get_rating(ebook_id):
        """
        Get the user rating for this book
        """
        conn = r.connect("localhost", 28015, db="ogreserver")
        return r.table('ebooks').get(ebook_id)['rating'].run(conn)

    @staticmethod
    def get_comments(ebook_id):
        """
        Get the list of comments on this book
        """
        conn = r.connect("localhost", 28015, db="ogreserver")
        return r.table('ebooks').get(ebook_id)['comments'].run(conn)

    @staticmethod
    def build_ebook_key(lastname, firstname, title):
        """
        Generate a key for this ebook from the author and title
        This is used as the ebook's key in the DB - referred to as ebook_id in code
        """
        return hashlib.md5(
            ("~".join((lastname, firstname, title))).encode("UTF-8")
        ).hexdigest()

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
    def get_ebook_url(ebook_id, fmt=None, version_id=None):
        """
        Generate a download URL for the requested ebook

        If a version isn't requested the top-ranked one will be supplied.
        If a format isn't requested one will be served in the order defined in EBOOK_FORMATS
        """
        conn = r.connect("localhost", 28015, db="ogreserver")

        if version_id is None:
            versions = list(r.table('versions').filter({'ebook_id': ebook_id}).eq_join(
                'id', r.table('formats'), index='version_id'
            ).zip().run(conn))

            if len(versions) > 1:
                # sort this book's versions by quality & popularity
                versions = sorted(versions,
                    key=lambda v: DataStore.versions_rank_algorithm(v),
                    reverse=True
                )

            print versions
            if fmt is None:
                # select top-ranked version
                version = versions[0]
                # serve the OGRE preferred format
                for fmt in app.config['EBOOK_FORMATS']:
                    if fmt == version['format']:
                        file_md5 = version['id']
                        break
            else:
                # serve the requested format from best version possible
                for version in versions:
                    if fmt == version['format']:
                        file_md5 = version['id']
                        break
        else:
            # get the specific requested version
            version = r.table('versions').filter({'id': version_id}).eq_join(
                'id', r.table('formats'), index='version_id'
            ).zip().run(conn)

            if fmt is None:
                # serve the OGRE preferred format
                for fmt in app.config['EBOOK_FORMATS']:
                    if fmt == version['format']:
                        file_md5 = version['id']
                        break
            else:
                # verify requested format is available on requested version
                if fmt != version['format']:
                    raise Exception("Requested format not available on requested version.")
                else:
                    file_md5 = version['id']

        # generate the filename - which is the key on S3
        filename = DataStore.generate_filename(ebook_id, file_md5, fmt)

        # create an expiring auto-authenicate url for S3
        s3 = boto.connect_s3(app.config['AWS_ACCESS_KEY'], app.config['AWS_SECRET_KEY'])
        return s3.generate_url(app.config['DOWNLOAD_LINK_EXPIRY'], 'GET',
            bucket=app.config['S3_BUCKET'],
            key=filename
        )

    @staticmethod
    def update_book_md5(current_file_md5, updated_file_md5):
        """
        Update a formats entry with a new PK
        This is called after the OGRE-ID meta data is written into an ebook on the client
        """
        conn = r.connect("localhost", 28015, db="ogreserver")
        try:
            data = r.table('formats').get(current_file_md5).run(conn)
            data['id'] = updated_file_md5
            data['source_patched'] = True
            r.table('formats').insert(data).run(conn)
            r.table('formats').get(current_file_md5).delete().run(conn)
            print "Updated {0} to {1}".format(current_file_md5, updated_file_md5)
        except Exception as e:
            print "Something bad happened {0}".format(e)
            return False
        return True

    @staticmethod
    def set_uploaded(file_md5, isit=True):
        """
        Mark an ebook as having been uploaded to S3
        """
        conn = r.connect("localhost", 28015, db="ogreserver")
        r.table('formats').get(file_md5).update({'uploaded': isit}).run(conn)

    @staticmethod
    def set_dedrm_flag(file_md5):
        """
        Mark a book as having had DRM removed
        """
        conn = r.connect("localhost", 28015, db="ogreserver")
        r.table('formats').get(file_md5).update({'dedrm': True}).run(conn)

    @staticmethod
    def store_ebook(ebook_id, file_md5, filename, filepath, fmt):
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
            if 'x-amz-meta-ogre-key' in metadata and metadata['x-amz-meta-ogre-key'] == ebook_id:
                DataStore.set_uploaded(file_md5)
                return False

        # calculate uploaded file md5
        f = open(filepath, "rb")
        md5_tup = k.compute_md5(f)
        f.close()

        # error check uploaded file
        if file_md5 != md5_tup[0]:
            # TODO logging
            raise S3DatastoreError("Upload failed checksum 1")
        else:
            try:
                # TODO time this and print
                # push file to S3
                k.set_contents_from_filename(filepath,
                    headers={'x-amz-meta-ogre-key': ebook_id},
                    md5=md5_tup,
                )
                print "UPLOADED {1}".format(filename)

                # mark ebook as stored
                DataStore.set_uploaded(file_md5)

            except S3ResponseError:
                # TODO log
                raise S3DatastoreError("Upload failed checksum 2")

        return True

    @staticmethod
    def generate_filename(ebook_id, file_md5, fmt):
        """
        Generate the filename for a book on its way to S3
        """
        conn = r.connect("localhost", 28015, db="ogreserver")

        # load the author and title of this book
        ebook = r.table('ebooks').get(ebook_id).run(conn)
        authortitle = re.sub('[^a-zA-Z0-9]', '_', '{0}_{1}_-_{2}'.format(
            ebook['firstname'], ebook['lastname'], ebook['title']
        ))

        # TODO transpose unicode
        return '{0}.{1}.{2}'.format(authortitle, file_md5[0:6], fmt)

    @staticmethod
    def get_missing_books(username=None, verify_s3=False):
        """
        Query the DB for books marked as not uploaded

        The verify_s3 flag enables a further check to be run against S3 to ensure 
        the file is actually there
        """
        conn = r.connect("localhost", 28015, db="ogreserver")

        # build a query joining ebooks and versions
        query = r.table('ebooks').eq_join('id', r.table('versions'), index='ebook_id').zip()
        
        # filter by username
        if username is not None:
            query = query.filter({'user': 'mafro'})
            
        # join to formats filtering for un-uploaded files
        query = query.eq_join('id', r.table('formats'), index='version_id').zip().filter(
            {'uploaded': False}
        )
        
        cursor = query.run(conn)

        if username is None and verify_s3 is True:
            raise Exception("Can't verify entire library in one go.")

        output = []

        # flatten for output
        for ebook in cursor:
            output.append({
                'ebook_id': ebook['ebook_id'],
                'file_md5': ebook['id'], 
                'format': ebook['format'],
            })

        if verify_s3 == True:
            # connect to S3
            s3 = boto.connect_s3(app.config['AWS_ACCESS_KEY'], app.config['AWS_SECRET_KEY'])
            bucket = s3.get_bucket(app.config['S3_BUCKET'])

            # verify books are on S3
            for b in output:
                # TODO rethink
                filename = DataStore.generate_filename(b['ebook_id'], b['file_md5'], b['format'])
                k = boto.s3.key.Key(bucket, filename)
                DataStore.set_uploaded(b['file_md5'])
                # TODO update rs when verify=True

        return output


class S3DatastoreError(Exception):
    pass

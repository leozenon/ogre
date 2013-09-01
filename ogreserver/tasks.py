import os
import json
import subprocess

from . import app, celery

from models.user import User
from models.datastore import DataStore, S3DatastoreError
from models.reputation import Reputation
from models.log import Log


@celery.task(name="ogreserver.store_ebook")
def store_ebook(user_id, ebook_id, file_md5, fmt):
    """
    Store an ebook in the datastore
    """
    try:
        filepath = "{0}/{1}.{2}".format(app.config['UPLOADED_EBOOKS_DEST'], file_md5, fmt)
        filename = DataStore.generate_filename(ebook_id, file_md5, fmt)

        user = User.query.get(user_id)

        # store the file into S3
        if DataStore.store_ebook(ebook_id, file_md5, filename, filepath, fmt):
            # stats log the upload
            Log.create(user.id, "STORED", 1)

            # handle badge and reputation changes
            r = Reputation(user)
            r.earn_badges()

        else:
            print "File exists on S3"

    except S3DatastoreError:
        # TODO log this shit
        pass

    finally:
        # always delete local file
        if os.path.exists(filepath):
            os.remove(filepath)


@celery.task(name="ogreserver.convert_ebook")
def convert_ebook(sdbkey, source_filepath, dest_fmt):
    """
    Convert an ebook to another format, and push to datastore
    """
    pass
    #source_filepath = "%s/%s.%s" % (app.config['UPLOADED_EBOOKS_DEST'], file_md5, fmt)

    #for convert_fmt in app.config['EBOOK_FORMATS']:
    #    if fmt == convert_fmt:
    #        continue

    #    dest_filepath = "%s/%s.%s" % (app.config['UPLOADED_EBOOKS_DEST'], file_md5, fmt)

    #    meta = subprocess.Popen(['ebook-convert', source_filepath, ], 
    #                            stdout=subprocess.PIPE).communicate()[0]

    #if store == True:
    #    if user_id == None:
    #        raise Exception("user_id must be supplied to convert_ebook when store=True")

    #    store_ebook.delay(user_id, sdbkey, file_md5, fmt)


# TODO nightly which recalculates book ratings: 
#      10% of entire database per night (LOG the total and time spent)

# TODO nightly which check books are stored on S3 and updates SDB 


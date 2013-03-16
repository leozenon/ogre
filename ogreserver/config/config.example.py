import os
basedir = os.path.abspath(os.path.dirname(".."))

# AWS config
AWS_ACCESS_KEY = ""
AWS_SECRET_KEY = ""
S3_BUCKET = ""

# Flask app
DEBUG = True
BETA = True

# Flask-WTF
SECRET_KEY = "very-secret-ogre"

# SQLAlchemy DB URI
SQLALCHEMY_DATABASE_URI = "mysql://user:pass@localhost/ogre"

# Whoosh full-text search
WHOOSH_BASE = os.path.join(basedir, "search.db")

# Upload path
UPLOADED_EBOOKS_DEST = ""

# Ebook conversion formats; all books will be provided in these formats by OGRE
EBOOK_FORMATS = ['mobi', 'azw', 'pdf', 'epub']

# OGRE download links expire in 10 seconds
DOWNLOAD_LINK_EXPIRY = 10

import os
basedir = os.path.abspath(os.path.dirname(".."))

# Celery config
AMQP_BROKER = "amqp://{{ pillar['rabbitmq_user'] }}:{{ pillar['rabbitmq_pass'] }}@{{ pillar['rabbitmq_host'] }}:5672/{{ pillar['rabbitmq_vhost'] }}"

CELERY_DEFAULT_QUEUE = "ogreserver"
CELERY_DEFAULT_EXCHANGE = "ogreserver"
CELERY_DEFAULT_EXCHANGE_TYPE = "direct"
CELERY_DEFAULT_ROUTING_KEY = "ogreserver"

# AWS config
AWS_ACCESS_KEY = "{{ pillar['aws_access_key'] }}"
AWS_SECRET_KEY = "{{ pillar['aws_secret_key'] }}"
AWS_REGION = "{{ pillar['aws_region'] }}"
S3_BUCKET = "{{ pillar['s3_bucket'] }}"

# Flask app
DEBUG = True
BETA = True

# Flask-WTF
SECRET_KEY = "{{ pillar['flask_secret'] }}"

# SQLAlchemy DB URI
SQLALCHEMY_DATABASE_URI = "mysql://{{ pillar['mysql_user'] }}:{{ pillar['mysql_pass'] }}@{{ pillar['mysql_host'] }}/{{ pillar['mysql_db'] }}"

# Whoosh full-text search
WHOOSH_BASE = os.path.join(basedir, "search.db")

# Upload path
UPLOADED_EBOOKS_DEST = "/srv/ogre/uploads"

# Ebook conversion formats; all books will be provided in these formats by OGRE
EBOOK_FORMATS = ['mobi', 'azw', 'pdf', 'epub']

# OGRE download links expire in 10 seconds
DOWNLOAD_LINK_EXPIRY = 10

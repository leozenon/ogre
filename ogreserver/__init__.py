import os

# import Flask library
from flask import Flask
#from werkzeug.contrib.fixers import ProxyFix

# import Flask extensions
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.login import LoginManager
from flask.ext.uploads import UploadSet, ALL, configure_uploads
#from flask.ext.script import Manager
#from flask.ext.cache import Cache

# instantiate Flask application
app = Flask(__name__)
app.config.from_pyfile("config/flask.app.conf.py")

# setup SQLAlchemy
db = SQLAlchemy(app)

# init Whoosh for full-text search
from whoosh.index import create_in, open_dir
from whoosh.fields import Schema, TEXT

if os.path.exists(app.config['WHOOSH_BASE']):
    whoosh = open_dir(app.config['WHOOSH_BASE'])
else:
    os.makedirs(app.config['WHOOSH_BASE'])
    schema = Schema(
        sdb_key=TEXT(stored=True),
        author=TEXT(stored=True),
        title=TEXT(stored=True)
    #    content=TEXT TODO extract and index all book content!
    )
    whoosh = create_in(app.config['WHOOSH_BASE'], schema)

# memcache config
#cache = Cache(app)

# setup Flask-Login
login_manager = LoginManager()
login_manager.setup_app(app)
login_manager.login_view = "login"

@login_manager.user_loader
def load_user(userid):
    from ogreserver.models.user import User
    user = User.query.filter_by(id=int(userid)).first()
    return user

# setup Flask-Upload
uploads = UploadSet('ebooks', ALL)
configure_uploads(app, (uploads))

# import views to register them with Flask
import ogreserver.views

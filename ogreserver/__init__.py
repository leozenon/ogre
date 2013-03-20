import os

# import Flask library
from flask import Flask, render_template

# import Flask extensions
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.login import LoginManager
from flask.ext.uploads import UploadSet, ALL, configure_uploads

# instantiate Flask application
app = Flask(__name__)
app.config.from_pyfile("config/flask.app.conf.py")


# declare some error handler pages
@app.errorhandler(404)
def page_not_found(error):
    return render_template("404.html"), 404


@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template("500.html"), 500


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
import views
views.noop()

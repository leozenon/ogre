import os

# import Flask library
from flask import Flask, render_template

# import Flask extensions
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.login import LoginManager
from flask.ext.uploads import UploadSet, ALL, configure_uploads

# instantiate Flask application
app = Flask(__name__)
conf_path = os.getenv("OGRE_CONF")
if conf_path is None:
    if os.path.exists("config/flask.app.conf.py"):
        conf_path = "config/flask.app.conf.py"
    else:
        raise Exception("Missing application config! You must set the environment"
                        "variable $OGRE_CONF, or create a file at config/flask.app.conf.py")

try:
    app.config.from_pyfile(conf_path)
except IOError:
    raise Exception("Missing application config! No file at {0}".format(conf_path))

# setup SQLAlchemy
db = SQLAlchemy(app)


# only need to setup rest of app when config has been decrypted
if app.config['SECRET_KEY'] is not None:

    # declare some error handler pages
    @app.errorhandler(404)
    def page_not_found(error):
        return render_template("404.html"), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template("500.html"), 500

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

    # HACK to support dev
    #for rule in app.url_map.iter_rules():
    #    rule.rule = "/ogre" + rule.rule
    #    rule.refresh()

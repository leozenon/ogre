from datetime import datetime

from flask.ext.login import UserMixin

from ogreserver import app, db
from ogreserver.models import security
from ogreserver.models.reputation import Reputation, UserBadge


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80))
    password = db.Column(db.String(256))
    email = db.Column(db.String(120), unique=True)
    display_name = db.Column(db.String(50), unique=True)
    api_key_expires = db.Column(db.DateTime)
    points = db.Column(db.Integer, default=0)
    needs_password_reset = db.Column(db.Boolean, default=1)
    badges = db.relationship(UserBadge, backref='user', lazy='dynamic')

    def __init__(self, username, password, email):
        self.username = username
        self.password = security.pwd_context.encrypt(password)
        self.email = email

    @staticmethod
    def authenticate(username, password):
        user = User.query.filter_by(username=username).first()
        if not user:
            return None
        elif security.pwd_context.verify(password, user.password) == False:
            return None
        return user

    @staticmethod
    def _compile_pre_key(username, password, timestamp):
        # construct a unique identifier to be hashed
        return "%s:%s:%s:%s" % (app.config['SECRET_KEY'], username, password, timestamp)

    @staticmethod
    def create_auth_key(username, password, timestamp):
        # hash the value from _compile_pre_key()
        return security.pwd_context.encrypt(User._compile_pre_key(username, password, timestamp))

    @staticmethod
    def validate_auth_key(username, api_key):
        # load the user by name
        user = User.query.filter_by(username=username).first()
        if not user:
            return None

        # TODO check API key hasn't expired

        # reconstruct the key and verify it
        prekey = User._compile_pre_key(user.username, user.password, user.api_key_expires)
        if security.pwd_context.verify(prekey, api_key) == True:
            return user
        else:
            return None

    def assign_auth_key(self):
        # generate a new API key and save against the user
        self.api_key_expires = datetime.utcnow()
        self.api_key_expires = self.api_key_expires.replace(microsecond=0)    # remove microseconds for mysql
        api_key = User.create_auth_key(self.username, self.password, self.api_key_expires)
        db.session.add(self)
        db.session.commit()
        return "%s+%s" % (self.username, api_key)

    # Flask-Login method
    def is_authenticated(self):
        if self.email is not None:
            return True
        else:
            return False

    def has_badge(self, badge):
        return Reputation.has_badge(self, badge)

    def __str__(self):
        return "<User: %s, %s>" % (self.id, self.username)

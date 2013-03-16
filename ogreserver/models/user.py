from datetime import datetime

from flask.ext.login import UserMixin
from sqlalchemy.sql import func

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
    total_users = None

    def __init__(self, username, password, email):
        self.username = username
        self.password = security.pwd_context.encrypt(password)
        self.email = email

    @staticmethod
    def authenticate(username, password):
        """
        Authenticate a user by username and password
        """
        user = User.query.filter_by(username=username).first()
        if not user:
            return None
        elif security.pwd_context.verify(password, user.password) == False:
            return None
        return user

    @staticmethod
    def _compile_pre_key(username, password, timestamp):
        return "%s:%s:%s:%s" % (app.config['SECRET_KEY'], username, password, timestamp)

    @staticmethod
    def create_auth_key(username, password, timestamp):
        """
        Construct a unique identifier for an API key by encrypting output from _compile_pre_key()
        """
        return security.pwd_context.encrypt(User._compile_pre_key(username, password, timestamp))

    @staticmethod
    def validate_auth_key(username, api_key):
        """
        Validate an incoming API key
        """
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
        """
        Generate a new API key and save against the user
        """
        self.api_key_expires = datetime.utcnow()
        self.api_key_expires = self.api_key_expires.replace(microsecond=0)    # remove microseconds for mysql
        api_key = User.create_auth_key(self.username, self.password, self.api_key_expires)
        db.session.add(self)
        db.session.commit()
        return "%s+%s" % (self.username, api_key)

    # Flask-Login method
    def is_authenticated(self):
        """
        Check user is authenticated
        """
        if self.email is not None:
            return True
        else:
            return False

    def has_badge(self, badge):
        """
        Check if this user has earnt a specific badge
        """
        return Reputation.has_badge(self, badge)

    @staticmethod
    def get_total_users():
        """
        Return the total number of registered users
        """
        if User.total_users is None:
            q = db.session.query(func.count(User.id))
            User.total_users = db.session.execute(q).scalar()
        return User.total_users

    def __str__(self):
        return "<User: %s, %s>" % (self.id, self.username)

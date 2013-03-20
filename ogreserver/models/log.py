from .. import db

from datetime import datetime


class Log(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer)
    api_session_key = db.Column(db.String(256))
    timestamp = db.Column(db.DateTime)  # TODO Log timestamp losing seconds
    type = db.Column(db.String(30))
    data = db.Column(db.String(200))

    def __init__(self, user_id, api_session_key, type, data):
        self.user_id = user_id
        self.api_session_key = api_session_key
        self.timestamp = datetime.utcnow()
        self.type = type
        self.data = str(data)

    @staticmethod
    def create(user_id, type, data, api_session_key=None):
        print "%s %s" % (type, data)
        db.session.add(Log(user_id, api_session_key, type, data))
        db.session.commit()

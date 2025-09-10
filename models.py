from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Log(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.String(50))
    ip = db.Column(db.String(50))
    event_type = db.Column(db.String(50))
    status = db.Column(db.String(50))

    def __repr__(self):
        return f"<Log {self.id} {self.ip} {self.event_type}>"

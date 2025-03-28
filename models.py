from flask_sqlalchemy import SQLAlchemy
import datetime

db = SQLAlchemy()

class Status(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    name = db.Column(db.String(10), unique = True, nullable = False)

class Method(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    status_id = db.Column(db.Integer, db.ForeignKey("status.id"), nullable = False)
    filename = db.Column(db.String(50), unique = True, nullable = False)
    parsing_results = db.Column(db.Text)
    status = db.relationship("Status")

class Labs(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    status_id = db.Column(db.Integer, db.ForeignKey("status.id"), nullable = False)
    filename = db.Column(db.String(50), unique = True, nullable = False)
    parsing_results_1 = db.Column(db.Text)
    parsing_results_2 = db.Column(db.Text)
    status = db.relationship("Status")
    user_id = db.Column(db.String(50), nullable = False)
    method_id = db.Column(db.Integer, db.ForeignKey("method.id"), nullable = False)
    method = db.relationship("Method")
    time_stamp = db.Column(db.DateTime, default = datetime.datetime.now, nullable = False)

import datetime
from dataclasses import dataclass
from sqlalchemy.sql import func
from db_loader import db


@dataclass
class Event(db.Model):
    __tablename__ = "events"

    id: int = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name: str = db.Column(db.String(20), nullable=False)
    type: str = db.Column(db.String(3), nullable=False)
    source: str = db.Column(db.String(20), nullable=False)

    info: str = db.Column(db.String(255))

    timestamp: datetime.datetime = db.Column(db.DateTime, default=func.now())

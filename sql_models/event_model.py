import datetime
from dataclasses import dataclass
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from db_loader import db


@dataclass
class Event(db.Model):
    __tablename__ = "events"

    id: int = db.Column(db.Integer, primary_key=True, autoincrement=True)
    uid: int = db.Column(db.Integer, nullable=False)
    name: str = db.Column(db.String(20), nullable=False)
    type: str = db.Column(db.String(3), nullable=False)
    source: str = db.Column(db.String(20), nullable=False)

    info: str = db.Column(db.String(255))

    timestamp: datetime.datetime = db.Column(db.DateTime, default=func.now())

    country_id: int = db.Column(db.Integer, db.ForeignKey('countries.id'))
    country = relationship("Country", lazy='joined')

    def serialize(self):
        return {
            'id': self.id,
            'uid': self.uid,
            'name': self.name,
            'type': self.type,
            'source': self.source,
            'info': self.info,
            'timestamp': self.timestamp.isoformat(),
            'diff': self.calc_timestamp_diff(self.get_prev_event())
        }

    def get_prev_event(self):
        return db.session.query(Event).filter_by(id=self.id + 1, uid=self.uid).one_or_none()

    def calc_timestamp_diff(self, next_event):
        if next_event is None:
            return 0

        return round((next_event.timestamp - self.timestamp).total_seconds(), 2)


@dataclass
class Country(db.Model):
    __tablename__ = "countries"

    id: int = db.Column(db.Integer, primary_key=True, autoincrement=True)

    city: str = db.Column(db.String(255), unique=True, nullable=False)
    country_code2: str = db.Column(db.String(255))
    country_code3: str = db.Column(db.String(255))
    country_flag: str = db.Column(db.String(255))
    state_prov: str = db.Column(db.String(255), unique=True, nullable=False)
    country_name: str = db.Column(db.String(255), unique=True, nullable=False)
    zipcode: str = db.Column(db.String(255))

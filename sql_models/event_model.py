from dataclasses import dataclass, asdict
from datetime import datetime

from pygments.lexer import default
from sqlalchemy.sql import func, text
from db_loader import db
import logging

logger = logging.getLogger(__name__)


@dataclass()
class Session(db.Model):
    __tablename__ = "sessions"

    id: int = db.Column(db.Integer, primary_key=True)
    sid: str = db.Column(db.String, unique=True, nullable=False)
    source: str = db.Column(db.String, nullable=False)
    created_at: datetime = db.Column(db.DateTime(timezone=True), server_default=func.now(), nullable=False)
    country_id: int = db.Column(db.Integer, db.ForeignKey("countries.id"))
    viewed: bool = db.Column(db.Boolean, default=False, nullable=False)

    country = db.relationship("Country", back_populates="sessions")
    events = db.relationship("Event", back_populates="session", lazy=True, cascade="all, delete-orphan", passive_deletes=True)

    def serialize(self):
        return {
            'id': self.id,
            'sid': self.sid,
            'source': self.source,
            'created_at': self.created_at,
            'geo': asdict(self.country),
            'viewed': self.viewed,
        }


@dataclass()
class Event(db.Model):
    __tablename__ = "events"

    id: int = db.Column(db.Integer, primary_key=True)
    session_id: int = db.Column(db.Integer, db.ForeignKey("sessions.id", ondelete="CASCADE"),
                                nullable=False,
                                index=True)
    timestamp: int = db.Column(db.Integer, nullable=False)
    data: bytes = db.Column(db.LargeBinary, nullable=False)  # JSON string

    session = db.relationship("Session", back_populates="events")


@dataclass
class Country(db.Model):
    __tablename__ = "countries"

    id: int = db.Column(db.Integer, primary_key=True)

    city: str = db.Column(db.String(255), nullable=False)
    country_code2: str = db.Column(db.String(255))
    country_code3: str = db.Column(db.String(255))
    country_flag: str = db.Column(db.String(255))
    state_prov: str = db.Column(db.String(255), nullable=False)
    country_name: str = db.Column(db.String(255), nullable=False)
    zipcode: str = db.Column(db.String(255))

    sessions = db.relationship("Session", back_populates="country", lazy='joined')

    def find_or_create(self, event_geo):

        if event_geo is None:
            return db.session.query(Country).first()

        logger.info(f'attempting to create country: {event_geo}')
        # find in db
        country = db.session.query(Country).filter_by(
            city=event_geo.get('city'),
            state_prov=event_geo.get('state_prov'),
            country_name=event_geo.get('country_name')).one_or_none()

        # add if none
        if not country:
            logger.info('country not found, creating')

            new_country = Country(**event_geo)
            db.session.add(new_country)

            country = db.session.query(Country).filter_by(
                city=event_geo.get('city'),
                state_prov=event_geo.get('state_prov'),
                country_name=event_geo.get('country_name')).one()

            logger.info(f'created country: {country.id}')
        else:
            logger.info(f'found country: {country.id}')

        return country

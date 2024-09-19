import datetime
from dataclasses import dataclass
from sqlalchemy import exc
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

    def __repr__(self):
        return f'Event.id={self.id}.uid={self.uid}'

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

    def create(self, event_data):
        # create or find country
        country = Country().find_or_create(event_geo=event_data['event_geo'])

        # create new event
        new_event = Event(
            uid=event_data['event_uid'],
            name=event_data['event_name'],
            source=event_data['event_source'],
            type=event_data['event_type'],
            info=event_data['event_info'],
            country_id=country.id
        )

        return new_event

    def get_prev_event(self):

        prev_event = (db.session.query(Event)
                      .filter(Event.name != 'page_leave' and Event.id == self.id + 1 and Event.uid == self.uid)
                      .order_by(Event.id)
                      .one_or_none())

        return prev_event

    def calc_timestamp_diff(self, prev_event):
        if prev_event is None:
            return 0

        return round((prev_event.timestamp - self.timestamp).total_seconds(), 2)


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

    def find_or_create(self, event_geo):
        # find in db
        country = db.session.query(Country).filter_by(
            city=event_geo.get('city'),
            state_prov=event_geo.get('state_prov'),
            country_name=event_geo.get('country_name')).one_or_none()

        # add if none
        if not country:
            try:
                new_country = Country(**event_geo)
                db.session.add(new_country)
                db.session.commit()
                country = new_country

            except exc.IntegrityError as err:
                print('failed to create new country')
                print(err)

        return country

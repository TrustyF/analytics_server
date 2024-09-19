import datetime
from dataclasses import dataclass
from sqlalchemy import exc
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from db_loader import db


@dataclass
class User(db.Model):
    __tablename__ = "users"

    id: int = db.Column(db.Integer, primary_key=True, autoincrement=True)
    uid: int = db.Column(db.Integer, nullable=False, unique=True)
    source: str = db.Column(db.String(20), nullable=False)

    first_touch_time: datetime.datetime = db.Column(db.DateTime, default=func.now())
    last_touch_time: datetime.datetime = db.Column(db.DateTime, default=func.now())

    country_id: int = db.Column(db.Integer, db.ForeignKey('countries.id'))
    country = relationship("Country", back_populates="users", lazy='joined')

    events = relationship('Event', back_populates='user', lazy='joined',
                          cascade="all, delete-orphan", passive_deletes=True)

    def find_or_create(self, event_data):
        # find in db
        country = Country().find_or_create(event_geo=event_data['event_geo'])
        user = db.session.query(User).with_for_update().filter_by(uid=event_data['event_uid']).one_or_none()

        # add if none
        if not user:
            try:
                new_user = User(
                    uid=event_data['event_uid'],
                    source=event_data['event_source'],
                    country_id=country.id
                )
                db.session.add(new_user)
                user = new_user

            except exc.IntegrityError as err:
                print('failed to create new user')
                print(err)

        return user


@dataclass
class Event(db.Model):
    __tablename__ = "events"

    id: int = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name: str = db.Column(db.String(20), nullable=False)
    type: str = db.Column(db.String(10), nullable=False)

    info: str = db.Column(db.String(255))

    timestamp: datetime.datetime = db.Column(db.DateTime, default=func.now())

    user_id: int = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    user = relationship("User", back_populates='events', lazy='joined')

    def __repr__(self):
        return f'Event.id={self.id}.uid={self.uid}'

    def create(self, event_data):
        # create or find country,user
        user = User().find_or_create(event_data)

        # create new event
        new_event = Event(
            user_id=user.id,
            name=event_data['event_name'],
            type=event_data['event_type'],
            info=event_data['event_info'],
        )

        return new_event

    def get_next_event(self):
        next_event = (db.session.query(Event).filter(Event.id == self.id + 1 and Event.user_id == self.user_id)
                      .order_by(Event.id)
                      .one_or_none())

        return next_event

    def calc_timestamp_diff(self, next_event):
        if next_event is None:
            temp_diff = round((self.user.last_touch_time - self.timestamp).total_seconds(), 2)
            if temp_diff < 0:
                return 0
            else:
                return temp_diff

        return round((next_event.timestamp - self.timestamp).total_seconds(), 2)

    def serialize(self):
        return {
            'id': self.id,
            'uid': self.user.uid,
            'name': self.name,
            'type': self.type,
            'source': self.user.source,
            'info': self.info,
            'timestamp': self.timestamp.isoformat(),
            'diff': self.calc_timestamp_diff(self.get_next_event())
        }


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

    users = relationship("User", back_populates="country", lazy='joined',
                         cascade="all, delete-orphan", passive_deletes=True)

    def find_or_create(self, event_geo):
        # find in db
        country = db.session.query(Country).with_for_update().filter_by(
            city=event_geo.get('city'),
            state_prov=event_geo.get('state_prov'),
            country_name=event_geo.get('country_name')).one_or_none()

        # add if none
        if not country:
            try:
                new_country = Country(**event_geo)
                db.session.add(new_country)
                country = new_country

            except exc.IntegrityError as err:
                print('failed to create new country')
                print(err)

        return country

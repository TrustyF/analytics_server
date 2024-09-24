import datetime
from dataclasses import dataclass
from sqlalchemy import exc
from sqlalchemy.sql import func, text
from sqlalchemy.orm import relationship
from db_loader import db
import functools
import json
import logging

# Configure logging
# logging.basicConfig(level=logging.INFO,
#                     format='%(asctime)s - custom logger - %(levelname)s - %(message)s',
#                     handlers=[logging.FileHandler('app.log'),
#                               logging.StreamHandler()])

logger = logging.getLogger(__name__)


def retry_on_deadlock(retries=3):
    def decorator(f_func):
        @functools.wraps(f_func)
        def wrapper(*args, **kwargs):
            for i in range(retries):
                try:
                    return f_func(*args, **kwargs)
                except exc.OperationalError as e:
                    if 'deadlock' in str(e).lower():
                        logger.warning(f'Deadlock occurred, retrying ({i + 1}/{retries})...')
                        db.session.rollback()
                    else:
                        raise
                except Exception as e:
                    logger.error(f"Error occurred: {e}")
                    db.session.rollback()
                    raise
            raise RuntimeError('Max retries reached')

        return wrapper

    return decorator


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

    @retry_on_deadlock()
    def create(self, event_data):
        # create or find country,user
        user = User().find_or_create(event_data)

        logger.info(f'creating event with user: {user.id}')

        # create new event
        new_event = Event(
            user_id=user.id,
            name=event_data['event_name'],
            type=event_data['event_type'],
            info=event_data['event_info'],
            timestamp=event_data['event_time'],
        )

        user.last_touch_time = datetime.datetime.now()
        db.session.add(new_event)
        db.session.commit()

        logger.info(f'created event: {new_event.id}')

    def get_next_event(self):
        next_event = (db.session.query(Event).filter_by(id=self.id + 1, user_id=self.user.id)
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

    @retry_on_deadlock()
    def find_or_create(self, event_data):
        # find in db
        user = db.session.query(User).filter_by(uid=event_data['event_uid']).one_or_none()

        # add if none
        if not user:
            logger.info(f'user not found, creating...')

            country = Country().find_or_create(event_geo=event_data['event_geo'])

            # new_user = User(
            #     uid=event_data['event_uid'],
            #     source=event_data['event_source'],
            #     country_id=country.id
            # )
            # db.session.add(new_user)

            #  insert
            sql = text("INSERT IGNORE INTO users "
                       "(uid, source,country_id,first_touch_time,last_touch_time) VALUES "
                       "(:uid, :src, :country_id, :first_touch_time, :last_touch_time)")
            db.session.execute(sql, {
                'uid': event_data['event_uid'],
                'src': event_data['event_source'],
                'country_id': country.id,
                'first_touch_time': event_data['event_time'],
                'last_touch_time': event_data['event_time'],
            })
            db.session.commit()

            user = db.session.query(User).filter_by(uid=event_data['event_uid']).one()

            logger.info(f'created user: {user.id}')
        else:
            logger.info(f'found user: {user.id}')

        return user


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

    users = relationship("User", back_populates="country", lazy='joined')

    @retry_on_deadlock()
    def find_or_create(self, event_geo):
        # find in db
        country = db.session.query(Country).filter_by(
            city=event_geo.get('city'),
            state_prov=event_geo.get('state_prov'),
            country_name=event_geo.get('country_name')).one_or_none()

        # add if none
        if not country:

            # new_country = Country(**event_geo)
            # db.session.add(new_country)

            #  insert
            sql = text("INSERT IGNORE INTO countries "
                       "(country_name,state_prov,city,zipcode,country_code2,country_code3,country_flag)"
                       " VALUES "
                       "(:country_name, :state_prov, :city, :zipcode, :country_code2, :country_code3, :country_flag)")

            db.session.execute(sql, event_geo)
            db.session.commit()

            country = db.session.query(Country).filter_by(
                city=event_geo.get('city'),
                state_prov=event_geo.get('state_prov'),
                country_name=event_geo.get('country_name')).one()

            logger.info(f'created country: {country.id}')
        else:
            logger.info(f'found country: {country.id}')

        return country

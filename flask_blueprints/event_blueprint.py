import json
from datetime import datetime
from dataclasses import asdict
from collections import defaultdict

import requests
from sqlalchemy import exc, desc, func, distinct, cast, Date
from flask import Blueprint, request, Response, jsonify, send_file
from constants import GEO_API

from db_loader import db
from sql_models.event_model import Event, Country, User

bp = Blueprint('event', __name__)


@bp.route("/sleep_check", methods=['GET'])
def sleep_check():
    print('not sleeping', datetime.now())
    print('query db')

    db.session.query(Event).first()
    db.session.close()


@bp.route("/add", methods=['POST'])
def add():
    event_data = {
        'event_uid': int(request.json.get('uid')),
        'event_name': request.json.get('name'),
        'event_source': request.json.get('source'),
        'event_type': request.json.get('type'),
        'event_info': request.json.get('info'),
        'event_geo': request.json.get('geo'),
        'event_time': datetime.fromtimestamp(request.json.get('timestamp') / 1000),
    }

    Event().create(event_data)

    return json.dumps({'ok': True}), 200, {'ContentType': 'application/json'}


@bp.route("/get", methods=['GET'])
def get():
    db_users = (db.session.query(User).order_by(User.id).all())

    sorted_data = defaultdict(lambda:
                              defaultdict(lambda:
                                          {
                                              'events': list(),
                                              'geo': dict(),
                                              'source': '',
                                              'total_time': 0,
                                          }
                                          )
                              )

    for user in db_users:
        date = str(user.first_touch_time.date())

        sorted_data[date][user.uid]['events'] = sorted([ev.serialize() for ev in user.events],
                                                       key=lambda x: x['timestamp'])
        sorted_data[date][user.uid]['geo'] = asdict(user.country)
        sorted_data[date][user.uid]['source'] = user.source
        sorted_data[date][user.uid]['total_time'] = round(
            (user.last_touch_time - user.first_touch_time).total_seconds(), 2)
        sorted_data[date][user.uid]['uid'] = user.uid

    sorted_data = json.loads(json.dumps(sorted_data))

    # pprint.pprint(sorted_data, indent=1)

    return sorted_data


@bp.route("/ping_user_alive", methods=['PUT'])
def ping_user_alive():
    event_data = {
        'event_uid': int(request.json.get('uid')),
        'event_source': request.json.get('source'),
        'event_geo': request.json.get('geo'),
        'event_time': datetime.fromtimestamp(request.json.get('timestamp') / 1000),
    }

    user = User().find_or_create(event_data)

    if not user:
        db.session.close()
        return json.dumps({'success': False}), 404, {'ContentType': 'application/json'}

    user.last_touch_time = event_data['event_time']
    db.session.commit()
    db.session.close()

    return json.dumps({'success': True}), 200, {'ContentType': 'application/json'}


@bp.route("/delete", methods=['DELETE'])
def delete():
    uid = request.args.get('user_id')

    with db.session() as session:

        user = session.query(User).with_for_update().filter_by(uid=uid).one_or_none()

        try:
            session.delete(user)
            session.commit()
        except exc.IntegrityError as e:
            print(e)
            return json.dumps({'success': False}), 200, {'ContentType': 'application/json'}

    return json.dumps({'success': True}), 200, {'ContentType': 'application/json'}


@bp.route("/geo_locate", methods=['GET'])
def geo_locate():
    ip = request.args.get('ip')

    req = requests.get(f'https://api.ipgeolocation.io/ipgeo?apiKey={GEO_API}&ip={ip}')
    data = req.json()

    out = {'country_name': data['country_name'],
           'state_prov': data['state_prov'],
           'city': data['city'],
           'zipcode': data['zipcode'],
           'country_code2': data['country_code2'],
           'country_code3': data['country_code3'],
           'country_flag': data['country_flag'], }

    return out

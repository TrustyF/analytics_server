import json
import pprint
from datetime import datetime
from dataclasses import asdict
from collections import defaultdict

import requests
from sqlalchemy import exc, desc, func, distinct, cast, Date
from flask import Blueprint, request, Response, jsonify, send_file
from itertools import groupby
from constants import GEO_API

from db_loader import db
from sql_models.event_model import Event, Country

bp = Blueprint('event', __name__)


@bp.route("/sleep_check", methods=['GET'])
def sleep_check():
    print('not sleeping', datetime.now())
    print('query db')

    try:
        db.session.query(Event).first()
    except Exception:
        print('query failed')

    return json.dumps({'ok': True}), 200, {'ContentType': 'application/json'}


@bp.route("/add", methods=['POST'])
def add():
    event_uid = int(request.json.get('uid'))
    event_name = request.json.get('name')
    event_source = request.json.get('source')
    event_type = request.json.get('type')
    event_info = request.json.get('info')
    event_geo = request.json.get('geo')

    # find in db
    country = db.session.query(Country).filter_by(
        city=event_geo.get('city'),
        state_prov=event_geo.get('state_prov'),
        country_name=event_geo.get('country_name'),
    ).one_or_none()

    # add if none
    if not country:
        new_country = Country(**event_geo)

        try:
            db.session.add(new_country)
            db.session.commit()
        except exc.IntegrityError as err:
            print('failed to create new country')
            print(err)
            return json.dumps({'ok': False}), 404, {'ContentType': 'application/json'}

    new_event = Event(
        uid=event_uid,
        name=event_name,
        source=event_source,
        type=event_type,
        info=event_info,
        country_id=country.id
    )

    print(new_event)

    db.session.add(new_event)
    db.session.commit()

    try:
        db.session.commit()
    except exc.IntegrityError:
        return json.dumps({'ok': False}), 404, {'ContentType': 'application/json'}

    db.session.close()
    return json.dumps({'ok': True}), 200, {'ContentType': 'application/json'}


@bp.route("/get", methods=['GET'])
def get():
    db_events = (db.session.query(Event).all())

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

    for event in db_events:
        dat = str(event.timestamp.date())
        src = event.source
        ser_event = event.serialize()

        sorted_data[dat][event.uid]['events'].append(ser_event)
        sorted_data[dat][event.uid]['geo'] = asdict(event.country)
        sorted_data[dat][event.uid]['source'] = event.source
        sorted_data[dat][event.uid]['total_time'] += ser_event['diff']
        sorted_data[dat][event.uid]['uid'] = event.uid

    sorted_data = json.loads(json.dumps(sorted_data))

    # pprint.pprint(sorted_data, indent=1)

    return sorted_data


@bp.route("/delete", methods=['DELETE'])
def delete():
    uid = request.args.get('user_id')

    user = db.session.query(Event).filter_by(uid=uid).all()

    for event in user:
        db.session.delete(event)

    try:
        db.session.commit()
    except Exception:
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

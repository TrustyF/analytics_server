import json
import pprint
from datetime import datetime
from dataclasses import asdict

from sqlalchemy import exc, desc
from flask import Blueprint, request, Response, jsonify, send_file
from itertools import groupby

from db_loader import db
from sql_models.event_model import Event

bp = Blueprint('event', __name__)


@bp.route("/sleep_check", methods=['GET'])
def sleep_check():
    print('not sleeping', datetime.now())
    return json.dumps({'ok': True}), 200, {'ContentType': 'application/json'}


@bp.route("/add", methods=['GET'])
def add():
    event_uid = int(request.args.get('uid'))
    event_name = request.args.get('name')
    event_source = request.args.get('source')
    event_type = request.args.get('type')
    event_info = request.args.get('info')

    new_event = Event(
        uid=event_uid,
        name=event_name,
        source=event_source,
        type=event_type,
        info=event_info
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
    db_events = db.session.query(Event).all()
    mapped_events = [asdict(x) for x in db_events]

    entry_index = 0
    sorted_data = []

    geo = [x for x in mapped_events if x['name'] == 'geolocation'][0] or None
    mapped_events = [x for x in mapped_events if x['name'] != 'geolocation'] or []

    for date, f_events in groupby(sorted(mapped_events, key=lambda y: y['timestamp'], reverse=True),
                                  key=lambda x: x['timestamp'].date()):
        print(date)
        sorted_data.append({
            'date': date.strftime('%d/%m/%Y'),
            'geo': json.loads(geo['info']),
            'source': {}
        })
        for source, j_events in groupby(sorted(f_events, key=lambda y: y['source']), key=lambda x: x['source']):

            sorted_data[entry_index]['source'][source] = {
                'users': {}
            }

            for user_id, value in groupby(sorted(j_events, key=lambda y: y['uid']), key=lambda x: x['uid']):
                all_val = list(sorted(value, key=lambda y: y['timestamp']))

                sorted_data[entry_index]['source'][source]['users'][user_id] = {}
                sorted_data[entry_index]['source'][source]['users'][user_id]['events'] = []

                for i, x in enumerate(all_val):
                    temp = {
                        'event_name': x['name'],
                        'event_type': x['type'],
                        'event_info': x['info'],
                        'timestamp': x['timestamp'].isoformat(),
                        'diff': 0
                    }

                    try:
                        temp['diff'] = round((all_val[i + 1]['timestamp'] - x['timestamp']).total_seconds(), 2)
                    except Exception:
                        temp['diff'] = 0.0

                    sorted_data[entry_index]['source'][source]['users'][user_id]['events'].append(temp)
        entry_index += 1

    db.session.close()

    return sorted_data

import json
from dataclasses import asdict

import sqlalchemy.exc
from flask import Blueprint, request, Response, jsonify, send_file
from sqlalchemy import func

from db_loader import db
from sql_models.event_model import Event

bp = Blueprint('event', __name__)


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
    except sqlalchemy.exc.IntegrityError:
        return json.dumps({'ok': False}), 404, {'ContentType': 'application/json'}

    db.session.close()
    return json.dumps({'ok': True}), 200, {'ContentType': 'application/json'}

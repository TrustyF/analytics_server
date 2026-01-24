import json
import logging
import time
import zstandard as zstd

import requests
from flask import Blueprint, request, jsonify
from requests import RequestException
from sqlalchemy import func, asc, desc

from constants import GEO_API
from db_loader import db
from sql_models.event_model import Session, Event, Country

bp = Blueprint('session', __name__)
logger = logging.getLogger(__name__)

FALLBACK_COUNTRY = {
    'country_name': 'Nauru',
    'state_prov': None,
    'city': None,
    'zipcode': None,
    'country_code2': 'NR',
    'country_code3': 'NRU',
    'country_flag': '🇳🇷',
}

def compress_event(event):
    json_bytes = json.dumps(event, separators=(',', ':')).encode('utf-8')

    # Max compression with Zstandard
    cctx = zstd.ZstdCompressor(level=19)
    compressed = cctx.compress(json_bytes)

    return compressed


def decompress_event(s):
    cctx = zstd.ZstdDecompressor()
    json_bytes = cctx.decompress(s)
    events = json.loads(json_bytes)

    return events


@bp.route("/add", methods=["POST"])
def add():
    session_id = request.json.get("sid")
    session_source = request.json.get("source")
    session_geo = request.json.get("geo")
    session_events = request.json.get("events")

    # check if session exists
    session = Session.query.filter_by(sid=session_id, source=session_source).first()
    session.update({Session.viewed: False}, synchronize_session=False)

    if not session:
        country = Country().find_or_create(event_geo=session_geo)
        session = Session(
            sid=session_id,
            source=session_source,
            country_id=country.id
        )
        db.session.add(session)
        db.session.commit()

    # store the batch
    event_entry = Event(
        session_id=session.id,
        timestamp=int(time.time()),
        data=compress_event(session_events)
    )

    db.session.add(event_entry)
    db.session.commit()

    return jsonify({"status": "ok", "saved_events": len(session_events)})


@bp.route('/get_sessions')
def get_sessions():
    sessions = (
        db.session.query(Session)
        .outerjoin(Session.events)
        .group_by(Session.id)
        .all()
    )
    all_sessions = [x.serialize() for x in sessions]
    return all_sessions


@bp.route('/get_session_info/<int:sid>')
def get_session_info(sid):
    session = Session.query.filter_by(id=sid).one_or_none()

    if not session:
        return {"error": "session not found"}, 404

    # Find next session (newer)
    next_sess = Session.query \
        .filter(Session.id > sid) \
        .order_by(Session.id.asc()) \
        .first()

    # Find previous session (older)
    prev_sess = Session.query \
        .filter(Session.id < sid) \
        .order_by(Session.id.desc()) \
        .first()

    data = session.serialize()
    data.update({
        "next_session": next_sess.id if next_sess else None,
        "prev_session": prev_sess.id if prev_sess else None
    })

    return data


@bp.route("/get/<int:sid>")
def load_session(sid):
    session = Session.query.filter_by(id=sid).one_or_none()
    all_events = []

    if session.events:
        for row in session.events:
            events = decompress_event(row.data)
            all_events.extend(events)

    return jsonify(all_events)


@bp.route("/set_viewed/<int:sid>")
def set_viewed(sid):
    db.session.query(Session).filter_by(id=sid) \
        .update({Session.viewed: True}, synchronize_session=False)
    db.session.commit()
    db.session.close()
    return "ok", 200


@bp.route("/geo_locate", methods=['GET'])
def geo_locate():
    ip = request.args.get('ip')

    try:
        req = requests.get(f'https://api.ipgeolocation.io/ipgeo?apiKey={GEO_API}&ip={ip}', timeout=3)
        req.raise_for_status()
        data = req.json()

        logger.info(f'Geo located: {data}')

        return {'country_name': data['country_name'],
                'state_prov': data['state_prov'],
                'city': data['city'],
                'zipcode': data['zipcode'],
                'country_code2': data['country_code2'],
                'country_code3': data['country_code3'],
                'country_flag': data['country_flag'], }

    except Exception as e:
        logger.warning(f'geolocation failed: {e}')
        return FALLBACK_COUNTRY

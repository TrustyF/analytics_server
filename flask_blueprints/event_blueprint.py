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

    cctx = zstd.ZstdCompressor(level=6)
    compressed = cctx.compress(json_bytes)

    return compressed


def decompress_event(s):
    cctx = zstd.ZstdDecompressor()
    json_bytes = cctx.decompress(s)
    events = json.loads(json_bytes)

    return events


def normalize_event(e):
    # older clients double-encoded each event as a JSON string
    if isinstance(e, str):
        try:
            e = json.loads(e)
        except json.JSONDecodeError:
            logger.warning('Failed to parse event string, skipping')
            return None

    if not isinstance(e, dict):
        logger.warning(f'Unexpected event type {type(e)}, skipping')
        return None

    return e


def count_clicks(events):
    # rrweb IncrementalSnapshot (type 3) with MouseInteraction source (2) and Click type (2)
    return sum(
        1 for e in events
        if e.get('type') == 3
        and e.get('data', {}).get('source') == 2
        and e.get('data', {}).get('type') == 2
    )


@bp.route("/add", methods=["POST"])
def add():
    session_id = request.json.get("sid")
    session_source = request.json.get("source")
    session_geo = request.json.get("geo")
    session_events = [e for e in map(normalize_event, request.json.get("events") or []) if e is not None]

    # check if session exists
    session = Session.query.filter_by(sid=session_id, source=session_source).one_or_none()

    if session is None:
        country = Country().find_or_create(event_geo=session_geo)
        session = Session(
            sid=session_id,
            source=session_source,
            country_id=country.id,
            click_count=0
        )
        db.session.add(session)
        db.session.flush()

    session.viewed = False
    session.click_count += count_clicks(session_events)

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
    sessions = db.session.query(Session).all()

    durations = dict(
        db.session.query(Session.id, func.max(Event.timestamp) - func.min(Event.timestamp))
        .join(Session.events)
        .group_by(Session.id)
        .all()
    )

    all_sessions = []
    for x in sessions:
        serialized = x.serialize()
        serialized['duration'] = durations.get(x.id, 0)
        all_sessions.append(serialized)

    return all_sessions, 200


@bp.route('/get_session_info/<int:sid>')
def get_session_info(sid):
    session = Session.query.filter_by(id=sid).one_or_none()

    if session is None:
        return "Failed to get session", 404

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

    return data, 200


@bp.route("/get/<int:sid>")
def load_session(sid):
    session = Session.query.filter_by(id=sid).one_or_none()

    if session is None:
        return "Failed to get session", 404

    all_events = []

    if session.events:
        for row in session.events:
            events = decompress_event(row.data)
            all_events.extend(e for e in map(normalize_event, events) if e is not None)

    return jsonify(all_events), 200


@bp.route("/set_viewed/<int:sid>")
def set_viewed(sid):
    session = db.session.query(Session).filter_by(id=sid).one_or_none()

    if session is not None:
        session.viewed = True
        db.session.commit()
        return "ok", 200

    else:
        logger.error(f'Failed to set viewed on {sid}')
        return "Failed to process request", 400


@bp.route("/geo_locate", methods=['GET'])
def geo_locate():
    ip = request.args.get('ip')

    try:
        req = requests.get(f'https://api.ipgeolocation.io/ipgeo?apiKey={GEO_API}&ip={ip}', timeout=3)
        req.raise_for_status()
        data = req.json()

        logger.info(f'Geo located: {data["country_flag"]} {data["state_prov"]} {data["city"]}')

        return {'country_name': data['country_name'],
                'state_prov': data['state_prov'],
                'city': data['city'],
                'zipcode': data['zipcode'],
                'country_code2': data['country_code2'],
                'country_code3': data['country_code3'],
                'country_flag': data['country_flag'], }, 200

    except Exception as e:
        logger.warning(f'geolocation failed: {e}')
        return FALLBACK_COUNTRY, 200

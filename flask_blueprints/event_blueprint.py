import json
import os
import time
from datetime import datetime, timedelta, timezone
import zstandard as zstd

import requests
from flask import Blueprint, request, jsonify, send_from_directory, abort
from sqlalchemy import func

from constants import GEO_API
from db_loader import db
from sql_models.event_model import Session, Event, Country

bp = Blueprint('event', __name__)


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
        session_id=session_id,
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
        .having(
            (func.max(Event.timestamp) - func.min(Event.timestamp)) >= 30
        )
        .all()
    )
    all_sessions = [x.serialize() for x in sessions]
    return all_sessions


@bp.route("/session/<sid>")
def load_session(sid):
    session = Session.query.filter_by(id=sid).first()
    all_events = []

    if session.events:
        for row in session.events:
            events = decompress_event(row.data)
            all_events.extend(events)

    return jsonify(all_events)


@bp.route("/event_cleanup")
def event_cleanup():
    cutoff = datetime.now(timezone.utc) - timedelta(days=3)
    test = db.session.query(Session).filter(Session.created_at < cutoff).all()

    print(test)

    return 200


# event_cleanup()


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


@bp.route("/site/<path:filename>")
def serve_dist_assets(website, filename):
    site_path = os.path.join("dists", website, "dist")
    if not os.path.exists(site_path):
        abort(404)

    return send_from_directory(site_path, filename)

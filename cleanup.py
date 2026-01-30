import logging
from datetime import datetime, timedelta, timezone

from db_loader import db
from sql_models.event_model import Session, Event
from sqlalchemy import func
from app import app
logger = logging.getLogger(__name__)


def event_cleanup():
    cutoff = datetime.now(timezone.utc) - timedelta(days=4)

    old_sessions = db.session.query(Session).filter(Session.created_at < cutoff)
    logger.info(f'Deleting {len(old_sessions.all())} old sessions')
    old_sessions.delete(synchronize_session=False)

    short_sessions = [
        sid for (sid,) in (
            db.session.query(Session.id)
            .outerjoin(Session.events)
            .group_by(Session.id)
            .having((func.max(Event.timestamp) - func.min(Event.timestamp)) <= 30)
            .all())
    ]
    if short_sessions:
        logger.info(f'Deleting {len(short_sessions)} short sessions')
        db.session.query(Session).filter(Session.id.in_(short_sessions)).delete(synchronize_session=False)

    db.session.commit()
    db.session.close()


with app.app_context():
    event_cleanup()

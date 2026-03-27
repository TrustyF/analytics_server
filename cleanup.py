import logging
from datetime import datetime, timedelta, timezone

from db_loader import db
from sql_models.event_model import Session, Event
from sqlalchemy import func, text
from app import app

logger = logging.getLogger(__name__)


def event_cleanup():
    cutoff = datetime.now(timezone.utc) - timedelta(days=4)

    old_sessions = db.session.query(Session).filter(Session.created_at < cutoff)
    logger.info(f'Deleting {len(old_sessions.all())} old sessions')
    old_sessions.delete(synchronize_session=False)

    viewed_sessions = db.session.query(Session).filter(Session.viewed == True)
    logger.info(f'Deleting {len(viewed_sessions.all())} viewed sessions')
    viewed_sessions.delete(synchronize_session=False)

    short_sessions = [
        sid for (sid,) in (
            db.session.query(Session.id)
            .outerjoin(Session.events)
            .filter(Session.source == 'houdini_icons')
            .group_by(Session.id)
            .having((func.max(Event.timestamp) - func.min(Event.timestamp)) <= 30)
            .all())
    ]
    if short_sessions:
        logger.info(f'Deleting {len(short_sessions)} short sessions')
        db.session.query(Session).filter(Session.id.in_(short_sessions)).delete(synchronize_session=False)

    db.session.commit()

    # reformat file to save space after deletions
    # db.session.execute(text("REINDEX"))
    # db.session.execute(text("VACUUM"))
    # db.session.commit()

    db.session.close()


with app.app_context():
    event_cleanup()

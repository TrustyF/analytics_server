from datetime import datetime, timedelta, timezone

from db_loader import db
from sql_models.event_model import Session, Event
from flask_apscheduler import APScheduler
from sqlalchemy import func

scheduler = APScheduler()


class SchedulerConfig:
    SCHEDULER_API_ENABLED = False


def event_cleanup():
    cutoff = datetime.now(timezone.utc) - timedelta(days=6)
    db.session.query(Session).filter(Session.created_at < cutoff).delete(synchronize_session=False)

    short_sessions = [
        sid for (sid,) in (
            db.session.query(Session.id)
            .outerjoin(Session.events)
            .group_by(Session.id)
            .having((func.max(Event.timestamp) - func.min(Event.timestamp)) <= 10)
            .all())
    ]
    if short_sessions:
        db.session.query(Session).filter(Session.id.in_(short_sessions)).delete(synchronize_session=False)

    db.session.commit()
    db.session.close()

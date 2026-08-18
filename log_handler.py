import logging


class DBLogHandler(logging.Handler):
    """Persists WARNING+ log records to the logs table so they can be
    surfaced to the viewer app. Never raises - a failure to persist a log
    entry must not break the request that triggered it."""

    def emit(self, record):
        try:
            from db_loader import db
            from sql_models.log_model import LogEntry

            entry = LogEntry(
                level=record.levelname,
                logger=record.name,
                message=self.format(record)[:1000],
            )
            db.session.add(entry)
            db.session.commit()
        except Exception:
            self.handleError(record)

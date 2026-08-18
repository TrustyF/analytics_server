from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.sql import func
from db_loader import db


@dataclass()
class LogEntry(db.Model):
    __tablename__ = "logs"

    id: int = db.Column(db.Integer, primary_key=True)
    created_at: datetime = db.Column(db.DateTime(timezone=True), server_default=func.now(), nullable=False)
    level: str = db.Column(db.String(20), nullable=False)
    logger: str = db.Column(db.String(255), nullable=False)
    message: str = db.Column(db.String(1000), nullable=False)

    def serialize(self):
        return {
            'id': self.id,
            'created_at': self.created_at,
            'level': self.level,
            'logger': self.logger,
            'message': self.message,
        }

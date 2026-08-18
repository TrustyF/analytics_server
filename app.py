import os
from flask import Flask
from flask_cors import CORS
from constants import MAIN_DIR
from db_loader import db
import logging
from sqlalchemy import event

# check if using locally
dev_mode = os.path.exists(os.path.join(MAIN_DIR, 'devmode.txt'))

app = Flask(__name__)
CORS(app)

basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'database.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  # To suppress a warning

if dev_mode:
    logging.basicConfig(level=logging.INFO)

db.init_app(app)

with app.app_context():

    # enable foreign keys for correct delete
    @event.listens_for(db.engine, "connect")
    def _enable_sqlite_fk(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON;")
        cursor.close()

    from sql_models.event_model import *

    db.create_all()

    # lightweight migration for columns added after initial create_all
    with db.engine.connect() as conn:
        existing_columns = {row[1] for row in conn.exec_driver_sql("PRAGMA table_info(sessions)")}
        if 'click_count' not in existing_columns:
            conn.exec_driver_sql("ALTER TABLE sessions ADD COLUMN click_count INTEGER NOT NULL DEFAULT 0")
            conn.commit()

    from flask_blueprints import event_blueprint

    app.register_blueprint(event_blueprint.bp, url_prefix='/session')

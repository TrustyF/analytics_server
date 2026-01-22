import os
from flask import Flask
from flask_cors import CORS
from flask_caching import Cache
from constants import MAIN_DIR
from db_loader import db
from flask_scheduler import SchedulerConfig, scheduler, event_cleanup
import logging

# check if using locally
dev_mode = os.path.exists(os.path.join(MAIN_DIR, 'devmode.txt'))

app = Flask(__name__)
CORS(app)

app.config.from_object(SchedulerConfig)
scheduler.init_app(app)

basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'database.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  # To suppress a warning

if dev_mode:
    logging.basicConfig(level=logging.INFO)
# else:
#     logging.disable(logging.WARNING)

db.init_app(app)

with app.app_context():
    from sql_models.event_model import *

    db.create_all()

    from flask_blueprints import event_blueprint

    app.register_blueprint(event_blueprint.bp, url_prefix='/session')


@scheduler.task("interval", hours=1)
def scheduled_cleanup():
    with app.app_context():
        event_cleanup()

scheduler.start()
scheduled_cleanup()
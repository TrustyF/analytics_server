import os
from flask import Flask
from flask_cors import CORS

from constants import MAIN_DIR, DB_NAME, DB_PASSWORD, DB_USERNAME
from db_loader import db
import logging

# check if using locally
dev_mode = os.path.exists(os.path.join(MAIN_DIR, 'devmode.txt'))

app = Flask(__name__)
CORS(app)

basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'database.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  # To suppress a warning

if not dev_mode:
    logging.disable(logging.WARNING)

db.init_app(app)

with app.app_context():
    # pprint.pprint(app.config)
    from sql_models.event_model import *
    db.create_all()

    from flask_blueprints import event_blueprint

    app.register_blueprint(event_blueprint.bp, url_prefix='/event')

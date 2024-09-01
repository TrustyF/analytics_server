import json
import os
from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv

from constants import MAIN_DIR, FLASK_SECRET, DB_NAME, DB_PASSWORD, DB_USERNAME
from db_loader import db
import logging

# check if using locally
dev_mode = os.path.exists(os.path.join(MAIN_DIR, 'devmode.txt'))

database_uri = f'mysql+pymysql://{DB_USERNAME}:{DB_PASSWORD}@TrustyFox.mysql.pythonanywhere-services.com:3306/{DB_NAME}'
local_database_uri = f'mysql+pymysql://root:{DB_PASSWORD}@127.0.0.1:3306/{DB_NAME}'

app = Flask(__name__)
CORS(app)

if dev_mode:
    print('using local')
    app.config["SQLALCHEMY_DATABASE_URI"] = local_database_uri
else:
    app.config["SQLALCHEMY_DATABASE_URI"] = database_uri
    logging.disable(logging.WARNING)

app.config["SQLALCHEMY_ENGINE_OPTIONS "] = {
    'pool_recycle': 280,
    'pool_pre_ping': True
}

with app.app_context():
    db.init_app(app)

    # from sql_models.event_model import *
    # db.create_all()

    from flask_blueprints import event_blueprint

    app.register_blueprint(event_blueprint.bp, url_prefix='/event')

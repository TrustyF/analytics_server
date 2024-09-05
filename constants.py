import os
from dotenv import load_dotenv

MAIN_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(MAIN_DIR, '.env'))

FLASK_SECRET = os.getenv('FLASK_SECRET')
DB_USERNAME = os.getenv('MYSQL_DATABASE_USERNAME')
DB_PASSWORD = os.getenv('MYSQL_DATABASE_PASSWORD')
GEO_API = os.getenv('GEO_API')
DB_NAME = 'TrustyFox$firebase_events'

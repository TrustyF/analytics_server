import os
from dotenv import load_dotenv

MAIN_DIR = os.path.dirname(os.path.abspath(__file__))
dotenv_loaded = load_dotenv(os.path.join(MAIN_DIR, '.env'))

FLASK_SECRET = os.getenv('FLASK_SECRET')
DB_USERNAME = os.getenv('MYSQL_DATABASE_USERNAME')
DB_PASSWORD = os.getenv('MYSQL_DATABASE_PASSWORD')
GEO_API = os.getenv('GEO_API')
DB_NAME = 'TrustyFox$firebase_events'

if not dotenv_loaded:
    raise Exception('Dotenv failed to load secrets')
else:
    print('secrets loaded')

print('test', os.getenv('TEST'))

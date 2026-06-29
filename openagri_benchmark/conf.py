import os

from decouple import config

SOURCE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SOURCE_DIR)
DEFAULT_OUTPUTS_DIR = os.path.join(PROJECT_ROOT, 'outputs')


HEALTHCHECK_TIMEOUT = config('HEALTHCHECK_TIMEOUT', default=20, cast=int)
STATS_INTERVAL_SECONDS = config('STATS_INTERVAL_SECONDS', default=2, cast=int)

BOOTSTRAP_DIR = config('BOOTSTRAP_DIR', default=None)

OUTPUTS_DIR = config('OUTPUTS_DIR', default=DEFAULT_OUTPUTS_DIR)

JWT_SIGNING_KEY = config('JWT_SIGNING_KEY')
JWT_ALG = config('JWT_ALG')

GATEKEEPER_BASE_URL = config('GATEKEEPER_BASE_URL', default='http://localhost:8001')
GATEKEEPER_PROXY_BASE = f'{GATEKEEPER_BASE_URL}/api/proxy/'
LOGIN_URL = f"{GATEKEEPER_BASE_URL}/api/login/"

GATEKEEPER_ADMIN_USER = config('GATEKEEPER_ADMIN_USER', default='admin')
GATEKEEPER_ADMIN_PASSWORD = config('GATEKEEPER_ADMIN_PASSWORD', default='admin')

FARMCALENDAR_BASE_URL = config('FARMCALENDAR_BASE_URL', default='http://localhost:8002')
PND_BASE_URL = config('PND_BASE_URL', default='http://localhost:8003')


LOGGING_LEVEL = config('LOGGING_LEVEL', default='DEBUG')

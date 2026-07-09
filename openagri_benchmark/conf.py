import os

from decouple import config

SOURCE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SOURCE_DIR)
DEFAULT_OUTPUTS_DIR = os.path.join(PROJECT_ROOT, 'outputs')
POSTPROCESSING_INPUT_DIR = os.path.join(SOURCE_DIR, 'postprocessing', 'inputs')


HEALTHCHECK_TIMEOUT = config('HEALTHCHECK_TIMEOUT', default=20, cast=int)
STATS_INTERVAL_SECONDS = config('STATS_INTERVAL_SECONDS', default=1, cast=int)

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
REPORTING_BASE_URL = config('REPORTING_BASE_URL', default='http://localhost:8006')

# Port the benchmark's local callback listener binds to (see stress_test/reporting.py).
# Must match the port embedded in STRESS_TEST_CALLBACK_URL on the Reporting service's .env.
REPORTING_STRESS_TEST_LISTENER_PORT = config('REPORTING_STRESS_TEST_LISTENER_PORT', default=8099, cast=int)
IRR_BASE_URL = config('IRR_BASE_URL', default='http://localhost:8005')
WEATHER_BASE_URL = config('WEATHER_BASE_URL', default='http://localhost:8004')

PND_CSV_PATH = os.path.join(SOURCE_DIR, 'data', 'pdm_data_90days.csv')
IRR_CSV_PATH = os.path.join(SOURCE_DIR, 'data', 'irrigation_data_90days.csv')

LOGGING_LEVEL = config('LOGGING_LEVEL', default='DEBUG')

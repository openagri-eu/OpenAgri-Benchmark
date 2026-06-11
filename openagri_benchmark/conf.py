import os

from decouple import config

SOURCE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SOURCE_DIR)
SANDBOX_DIR = os.path.join(PROJECT_ROOT, 'sandbox')


print(f"SOURCE_DIR: {SOURCE_DIR}")
print(f"PROJECT_ROOT: {PROJECT_ROOT}")
LOGGING_LEVEL = config('LOGGING_LEVEL', default='DEBUG')

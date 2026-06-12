import json

import requests

from openagri_benchmark.conf import LOGIN_URL



class BaseEvaluator():
    def __init__(self, logger, output_dir, admin_user, admin_pass):
        self.logger = logger
        self.output_dir = output_dir
        self.admin_user = admin_user
        self.admin_pass = admin_pass
        self.base_headers = {
            # 'Authorization': f'Bearer {auth_token}',
            'Content-Type': 'application/ld+json',
        }


    def get_auth_token(self, username, passsword):
        data = {
            "username": username,
            "password": passsword
        }
        response = requests.post(LOGIN_URL, data=data)

        if response.status_code == 200:
            tokens = response.json()
            token = tokens.get("access")
            refresh = tokens.get("refresh")
            return token, refresh
        else:
            response.raise_for_status()

    def task_admin_login(self):
        return self.get_auth_token(self.admin_user, self.admin_pass)

    def run(self):
        output = {
        }
        return output

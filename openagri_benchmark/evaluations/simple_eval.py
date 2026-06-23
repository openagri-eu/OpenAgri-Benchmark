import time

import requests

from openagri_benchmark.conf import GATEKEEPER_PROXY_BASE


from .base import BaseEvaluator


class SimpleEval(BaseEvaluator):

    def task_retrieve_fc_farm_list(self):
        url = f'{GATEKEEPER_PROXY_BASE}farmcalendar/api/v1/Farm/'

        response = requests.get(url, headers=self.base_headers.copy())
        if response.status_code == 200:
            data = response.json()
            farms = data.get("@graph")
            return farms

    def run(self):
        output = super().run()
        access, refresh = self.task_admin_login()
        self.logger.info(f"Logged in successfully: Access: {access}. Refresh {refresh}")
        self.base_headers['Authorization'] = f'Bearer {access}'
        time.sleep(4)
        farms = self.task_retrieve_fc_farm_list()

        output.update({
            'access': access,
            'refresh': refresh,
            'farms': farms,
        })
        return output


evaluator = SimpleEval

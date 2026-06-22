import time

import requests

from openagri_benchmark.conf import GATEKEEPER_PROXY_BASE


from ..base import BaseEvaluator
from .farmcalendar import FCStressTestMixin




class StressTestEval(FCStressTestMixin, BaseEvaluator):


    def run(self):
        output = super().run()
        access, refresh = self.task_admin_login()
        self.logger.info(f"Logged in successfully: Access: {access}. Refresh {refresh}")
        self.base_headers['Authorization'] = f'Bearer {access}'

        farms = self.task_retrieve_fc_farm_list()

        output.update({
            'farms': farms,
        })
        return output


evaluator = StressTestEval

import requests


from openagri_benchmark.conf import GATEKEEPER_PROXY_BASE


class FCStressTestMixin():

    def task_retrieve_fc_farm_list(self):
        url = f'{GATEKEEPER_PROXY_BASE}farmcalendar/api/v1/Farm/'

        response = requests.get(url, headers=self.base_headers.copy())
        if response.status_code == 200:
            data = response.json()
            farms = data.get("@graph")
            return farms


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


    def fc_tasks(self):
        fc_results = {

        }

    def task_register_farm(self, farm_i):
        url = f'{GATEKEEPER_PROXY_BASE}farmcalendar/api/v1/Farm/'

        data = {

        }
        response = requests.post(url,data=data, headers=self.base_headers.copy())

        if response.status_code == 200:
            graph = data.get("@graph")
            entry = graph[0]
            entry_id = entry['@id']
            return entry_id
        else:
            response.raise_for_status()

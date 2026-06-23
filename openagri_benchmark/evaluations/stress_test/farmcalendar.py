import time
import datetime

import requests
import numpy as np


from openagri_benchmark.conf import GATEKEEPER_PROXY_BASE


class FCStressTestMixin():

    def fc_tasks(self):
        start_timestamp = datetime.datetime.now().isoformat()
        farm_ids = []
        farm_request_times = []
        for i in range(10):
            elapsed_time, farm_id = self.task_register_farm(i)
            farm_ids.append(farm_id)
            farm_request_times.append(elapsed_time)
            time.sleep(0.8)
        end_timestamp = datetime.datetime.now().isoformat()

        fc_results = {
            'start_timestamp': start_timestamp,
            'end_timestamp': end_timestamp,
            'farm_ids': farm_ids,
            'farm_request_times': farm_request_times,
        }
        return fc_results

    def task_register_farm(self, farm_i):
        url = f'{GATEKEEPER_PROXY_BASE}farmcalendar/api/v1/Farm/'
        # url = f'http://localhost:8002/api/v1/Farm/'

        data = {
            "status": 1,
            "deleted_at": None,
            "name": f"Farm {farm_i}",
            "description": f"Some description for {farm_i}",
            "administrator": "Someone",
            "telephone": "123",
            "vatID": "123",
            "contactPerson": {
                "firstname": "Some",
                "lastname": "Person"
            },
            "address": {
                "adminUnitL1": "Some",
                "adminUnitL2": "Place",
                "addressArea": "Area",
                "municipality": "Mun",
                "community": "Com",
                "locatorName": "Something"
            }
        }
        headers = self.base_headers.copy()
        headers.update({
            # not sure why this works with FC, but not when using GK
            # 'Accept': 'application/ld+json',  # Requesting JSON-LD format
        })
        # Record start time before the request
        start_time = time.perf_counter()
        response = requests.post(url, json=data, headers=headers)
        # Record end time after the request
        end_time = time.perf_counter()
        elapsed_time = end_time - start_time

        if response.status_code == 201:
            entry_data = response.json()
            graph = entry_data.get("@graph")
            entry = graph[0]
            entry_id = entry['@id']
            return elapsed_time, entry_id
        else:
            response.raise_for_status()

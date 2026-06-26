import time
import datetime

import requests
import numpy as np
import threading


from openagri_benchmark.conf import (
    PND_BASE_URL,
)


class PNDStressTestMixin():
    PND_RPS = 2
    NUM_DESEASE = 10

    def pnd_tasks(self):
        start_timestamp = datetime.datetime.now().isoformat()
        pnd_results = {}

        reg_farms_results = self.pnd_register_desease(num_desease=self.NUM_DESEASE, rps=self.PND_RPS)
        pnd_results.update(reg_farms_results)

        end_timestamp = datetime.datetime.now().isoformat()
        pnd_results.update({
            'start_timestamp': start_timestamp,
            'end_timestamp': end_timestamp,
        })
        return pnd_results

    def pnd_register_desease(self, num_desease, rps):
        stagger_interval = 1 / rps
        desease_ids = [None] * num_desease
        desease_request_times = [None] * num_desease

        start_timestamp = datetime.datetime.now().isoformat()
        threads = []
        for i in range(num_desease):
            thread = threading.Timer(
                i * stagger_interval,
                self.pnd_register_desease_worker,
                args=(i, desease_ids, desease_request_times)
            )
            thread.daemon = False  # Make sure threads complete
            thread.start()
            threads.append(thread)

        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        end_timestamp = datetime.datetime.now().isoformat()

        return {
            'register_desease_start_timestamp': start_timestamp,
            'register_desease_end_timestamp': end_timestamp,
            'desease_ids': desease_ids,
            'desease_request_times': desease_request_times,
        }

    def pnd_register_desease_worker(self, index, entry_ids, entry_request_times):
        "running each request on a separated thread, storing result pointer args"
        self.logger.debug(f'Registering desease {index}')
        elapsed_time, desease_id = self.task_register_desease(index)
        entry_ids[index] = desease_id
        entry_request_times[index] = elapsed_time

    def task_register_desease(self, desease_i):
        url = f'{PND_BASE_URL}/api/v1/desease/'

        data = {
            "name": f"Powdery Mildew {desease_i}",
            "eppo_code": f"ERYSGT {desease_i}",
            "base_gdd": 5,
            "description": f"Fungal disease affecting wheat leaves {desease_i}",
            "gdd_points": [
            {"start": 0,   "end": 100, "descriptor": "Germination"},
            {"start": 100, "end": 300, "descriptor": "Growth"},
            {"start": 300, "end": 600, "descriptor": "Sporulation"}
            ]
        }
        headers = self.base_headers.copy()
        
        # Record start time before the request
        start_time = time.perf_counter()
        response = requests.post(url, json=data, headers=headers)
        # Record end time after the request
        end_time = time.perf_counter()
        elapsed_time = end_time - start_time

        if response.status_code == 201:
            entry_data = response.json()
            entry_id = entry_data['id']
            return elapsed_time, entry_id
        else:
            response.raise_for_status()


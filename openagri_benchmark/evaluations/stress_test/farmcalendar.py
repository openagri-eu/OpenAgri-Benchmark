import time
import datetime

import requests


from openagri_benchmark.conf import (
    FARMCALENDAR_BASE_URL,
)

from .base import BaseStressTestEval



class FCStressTest(BaseStressTestEval):
    def __init__(self, controller, logger, setup_id, output_dir, admin_user, admin_pass):
        super().__init__(controller, logger, setup_id, output_dir, admin_user, admin_pass)
        self.health_check_urls = [
            FARMCALENDAR_BASE_URL,
        ]

    def run(self):
        output = super().run()
        output.update(self.run_service_tasks('farmcalendar', self.fc_tasks))
        return output

    def fc_tasks(self):
        fc_results = {}

        reg_farms_results, farm_ids = self.fc_register_farms(num_farm=self.num_entries, rps=self.rps)
        fc_results.update(reg_farms_results)

        reg_parcels_results, parcel_ids = self.fc_register_farm_parcels(num_parcels=self.num_entries, rps=self.rps, farm_ids=farm_ids)
        fc_results.update(reg_parcels_results)

        return fc_results

    def fc_register_farms(self, num_farm, rps):
        farm_ids = [None] * num_farm

        results = self.multithread_task(
            'register_farm',
            self.task_register_farm, num_farm, rps,
            farm_ids=farm_ids
        )

        return results, farm_ids

    def task_register_farm(self, task_i, farm_ids):
        url = f'{FARMCALENDAR_BASE_URL}/api/v1/Farm/'

        data = {
            "status": 1,
            "deleted_at": None,
            "name": f"Farm {task_i}",
            "description": f"Some description for {task_i}",
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
            farm_ids[task_i] = entry_id
            return elapsed_time
        else:
            response.raise_for_status()

    def fc_register_farm_parcels(self, num_parcels, rps, farm_ids):
        parcel_ids = [None] * num_parcels

        results = self.multithread_task(
            'register_parcel',
            self.task_register_farm_parcel, num_parcels, rps,
            farm_ids=farm_ids, parcel_ids=parcel_ids
        )

        return results, parcel_ids


    def task_register_farm_parcel(self, task_i, farm_ids, parcel_ids):
        url = f'{FARMCALENDAR_BASE_URL}/api/v1/FarmParcels/'
        farm_id = farm_ids[task_i]
        wkt, center_lat, center_long = self.fc_generate_square_geometry(task_i)
        data = {
            "status": 1,
            "deleted_at": None,
            # "created_at": "2024-11-04T12:51:14.074000Z",
            # "updated_at": "2024-11-04T12:51:14.074000Z",
            "identifier": f"Parcel {task_i}",
            "description": f"Farm parcel description {task_i}",
            "validFrom": "2024-11-04T12:51:14.074000Z",
            "validTo": "2024-11-05T12:51:14.074000Z",
            "area": "0.94",
            "hasIrrigationFlow": "100.00",
            "category": "Category",
            "inRegion": "Some region",
            "hasToponym": "Toponym",
            "isNitroArea": False,
            "isNatura2000Area": False,
            "isPdopgArea": False,
            "isIrrigated": False,
            "isCultivatedInLevels": False,
            "isGroundSlope": False,
            "depiction": "",
            "hasGeometry": {
                "@type": "Geometry",
                "asWKT": wkt
            },
            "location": {
                "lat": center_lat,
                "long": center_long
            },
            "hasAgriCrop": [],
            "farm": {
                "@type": "Farm",
                "@id": farm_id
            }
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
            graph = entry_data.get("@graph")
            entry = graph[0]
            entry_id = entry['@id']
            parcel_ids[task_i] = entry_id
            return elapsed_time
        else:
            self.logger.error(response.json())
            response.raise_for_status()

    def fc_generate_square_geometry(self, index):
        size = 0.001

        row = index // 10
        col = index % 10

        x1 = col * size * 2
        y1 = row * size * 2
        x2 = x1 + size
        y2 = y1 + size

        wkt = f"POLYGON (({x1} {y1}, {x2} {y1}, {x2} {y2}, {x1} {y2}, {x1} {y1}))"
        center_lat = round((y1 + y2) / 2, 6)
        center_long = round((x1 + x2) / 2, 6)

        return wkt, center_lat, center_long


evaluator = FCStressTest

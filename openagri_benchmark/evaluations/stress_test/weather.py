import time
import datetime

import requests


from openagri_benchmark.conf import (
    WEATHER_BASE_URL,
)

from .base import BaseStressTestEval



class WDStressTest(BaseStressTestEval):
    def __init__(self, controller, logger, setup_id, output_dir, admin_user, admin_pass):
        super().__init__(controller, logger, setup_id, output_dir, admin_user, admin_pass)
        self.health_check_urls = [
            f"{WEATHER_BASE_URL}/docs",
        ]

    def run(self):
        output = super().run()
        output.update(self.run_service_tasks('weather', self.wd_tasks))
        return output

    def wd_tasks(self):
        wd_results = {}

        get_cached_locations_results = self.wd_get_locations_by_coordinates(num_calls=self.num_entries, rps=self.rps)
        wd_results.update(get_cached_locations_results)

        # reg_parcels_results, parcel_ids = self.wd_register_farm_parcels(num_parcels=self.num_entries, rps=self.rps, farm_ids=farm_ids)
        # wd_results.update(reg_parcels_results)

        # filter_parcels_results = self.wd_filter_farm_parcels_by_lat_lon(num_calls=self.num_entries, rps=self.rps, parcel_ids=parcel_ids)
        # wd_results.update(filter_parcels_results)

        return wd_results

    def wd_get_locations_by_coordinates(self, num_calls, rps):

        results = self.multithread_task(
            'get_locations_by_coordinates',
            self.task_get_locations_by_coordinates, num_calls, rps,
        )

        return results

    def task_get_locations_by_coordinates(self, task_i):
        url = f'{WEATHER_BASE_URL}/api/v1/locations/locations/by-coordinates/'

        headers = self.base_headers.copy()
        # Record start time before the request
        start_time = time.perf_counter()
        response = requests.get(url, params={"lat": task_i * 10.0, "lon": task_i * 10.0}, headers=headers)
        # Record end time after the request
        end_time = time.perf_counter()
        elapsed_time = end_time - start_time

        if response.status_code == 200:
            entry_data = response.json()
            return elapsed_time
        if response.status_code == 404:
            return elapsed_time
        else:
            response.raise_for_status()

    # def fc_register_farm_parcels(self, num_parcels, rps, farm_ids):
    #     parcel_ids = [None] * num_parcels

    #     results = self.multithread_task(
    #         'register_parcel',
    #         self.task_register_farm_parcel, num_parcels, rps,
    #         farm_ids=farm_ids, parcel_ids=parcel_ids
    #     )

    #     return results, parcel_ids


    # def task_register_farm_parcel(self, task_i, farm_ids, parcel_ids):
    #     url = f'{FARMCALENDAR_BASE_URL}/api/v1/FarmParcels/'
    #     farm_id = farm_ids[task_i]
    #     wkt, center_lat, center_long = self.fc_generate_square_geometry(task_i)
    #     data = {
    #         "status": 1,
    #         "deleted_at": None,
    #         # "created_at": "2024-11-04T12:51:14.074000Z",
    #         # "updated_at": "2024-11-04T12:51:14.074000Z",
    #         "identifier": f"Parcel {task_i}",
    #         "description": f"Farm parcel description {task_i}",
    #         "validFrom": "2024-11-04T12:51:14.074000Z",
    #         "validTo": "2024-11-05T12:51:14.074000Z",
    #         "area": "0.94",
    #         "hasIrrigationFlow": "100.00",
    #         "category": "Category",
    #         "inRegion": "Some region",
    #         "hasToponym": "Toponym",
    #         "isNitroArea": False,
    #         "isNatura2000Area": False,
    #         "isPdopgArea": False,
    #         "isIrrigated": False,
    #         "isCultivatedInLevels": False,
    #         "isGroundSlope": False,
    #         "depiction": "",
    #         "hasGeometry": {
    #             "@type": "Geometry",
    #             "asWKT": wkt
    #         },
    #         "location": {
    #             "lat": center_lat,
    #             "long": center_long
    #         },
    #         "hasAgriCrop": [],
    #         "farm": {
    #             "@type": "Farm",
    #             "@id": farm_id
    #         }
    #     }
    #     headers = self.base_headers.copy()
    #     # Record start time before the request
    #     start_time = time.perf_counter()
    #     response = requests.post(url, json=data, headers=headers)
    #     # Record end time after the request
    #     end_time = time.perf_counter()
    #     elapsed_time = end_time - start_time

    #     if response.status_code == 201:
    #         entry_data = response.json()
    #         graph = entry_data.get("@graph")
    #         entry = graph[0]
    #         entry_id = entry['@id']
    #         parcel_ids[task_i] = entry_id
    #         return elapsed_time
    #     else:
    #         self.logger.error(response.json())
    #         response.raise_for_status()

    # def fc_generate_square_geometry(self, index):
    #     size = 0.001

    #     row = index // 10
    #     col = index % 10

    #     x1 = col * size * 2
    #     y1 = row * size * 2
    #     x2 = x1 + size
    #     y2 = y1 + size

    #     wkt = f"POLYGON (({x1} {y1}, {x2} {y1}, {x2} {y2}, {x1} {y2}, {x1} {y1}))"
    #     center_lat = round((y1 + y2) / 2, 6)
    #     center_long = round((x1 + x2) / 2, 6)

    #     return wkt, center_lat, center_long


    # def fc_filter_farm_parcels_by_lat_lon(self, num_calls, rps, parcel_ids):
    #     results = self.multithread_task(
    #         'filter_parcels',
    #         self.task_filter_parcels, num_calls, rps,
    #         parcel_ids=parcel_ids
    #     )

    #     return results

    # def task_filter_parcels(self, task_i, parcel_ids):
    #     expected_parcel_id = parcel_ids[task_i]
    #     url = f'{FARMCALENDAR_BASE_URL}/api/v1/FarmParcels/'
    #     _, center_lat, center_long = self.fc_generate_square_geometry(task_i)
    #     # query_filter = "?contains_point=10%2C40"
    #     query_filter = {
    #         'contains_point': f'{center_lat},{center_long}'
    #     }
    #     headers = self.base_headers.copy()
    #     # Record start time before the request
    #     start_time = time.perf_counter()
    #     response = requests.get(url, params=query_filter, headers=headers)
    #     # Record end time after the request
    #     end_time = time.perf_counter()
    #     elapsed_time = end_time - start_time
    #     if response.status_code == 200:
    #         entry_data = response.json()
    #         graph = entry_data.get("@graph")
    #         entry = graph[0]
    #         entry_id = entry['@id']
    #         assert entry_id == expected_parcel_id, f"Wrong parcel returned when filtering for {task_i}: {entry_id} != {expected_parcel_id}"
    #         return elapsed_time
    #     else:
    #         self.logger.error(response.json())
    #         response.raise_for_status()

evaluator = WDStressTest

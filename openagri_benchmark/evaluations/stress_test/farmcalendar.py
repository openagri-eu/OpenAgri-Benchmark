import time
import datetime

import requests
import numpy as np
import threading


from openagri_benchmark.conf import (
    # GATEKEEPER_PROXY_BASE,
    FARMCALENDAR_BASE_URL,
)


class FCStressTestMixin():

    def fc_tasks(self):
        start_timestamp = datetime.datetime.now().isoformat()
        fc_results = {}

        reg_farms_results = self.fc_register_farms(num_farm=10, rps=2)
        fc_results.update(reg_farms_results)

        reg_parcels_results = self.fc_register_farm_parcels(num_parcels=10, rps=2, farm_ids=reg_farms_results['farm_ids'])
        fc_results.update(reg_parcels_results)

        # farm_parcel_ids, farm_parcel_request_times =

        end_timestamp = datetime.datetime.now().isoformat()
        fc_results.update({
            'start_timestamp': start_timestamp,
            'end_timestamp': end_timestamp,
        })
        return fc_results

    def fc_register_farms(self, num_farm, rps=2):
        stagger_interval = 1 / rps
        farm_ids = [None] * num_farm
        farm_request_times = [None] * num_farm

        start_timestamp = datetime.datetime.now().isoformat()
        threads = []
        for i in range(num_farm):
            thread = threading.Timer(
                i * stagger_interval,
                self.fc_register_farm_thread_worker,
                args=(i, farm_ids, farm_request_times)
            )
            thread.daemon = False  # Make sure threads complete
            thread.start()
            threads.append(thread)

        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        end_timestamp = datetime.datetime.now().isoformat()

        return {
            'register_farms_start_timestamp': start_timestamp,
            'register_farms_end_timestamp': end_timestamp,
            'farm_ids': farm_ids,
            'farm_request_times': farm_request_times,
        }

    def fc_register_farm_thread_worker(self, index, entry_ids, entry_request_times):
        "running each request on a separated thread, storing result pointer args"
        self.logger.debug(f'Registering farm {index}')
        elapsed_time, farm_id = self.task_register_farm(index)
        entry_ids[index] = farm_id
        entry_request_times[index] = elapsed_time

    def task_register_farm(self, farm_i):
        # url = f'{GATEKEEPER_PROXY_BASE}farmcalendar/api/v1/Farm/'
        url = f'{FARMCALENDAR_BASE_URL}/api/v1/Farm/'

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

    def fc_register_farm_parcels(self, num_parcels, rps, farm_ids):
        stagger_interval = 1 / rps
        parcel_ids = [None] * num_parcels
        parcel_request_times = [None] * num_parcels
        start_timestamp = datetime.datetime.now().isoformat()
        threads = []
        for i in range(num_parcels):
            thread = threading.Timer(
                i * stagger_interval,
                self.fc_register_farm_parcels_thread_worker,
                args=(i, farm_ids, parcel_ids, parcel_request_times)
            )
            thread.daemon = False  # Make sure threads complete
            thread.start()
            threads.append(thread)

        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        # self.fc_register_farm_parcels_thread_worker(0, farm_ids, parcel_ids, parcel_request_times)

        end_timestamp = datetime.datetime.now().isoformat()

        return {
            'register_parcels_start_timestamp': start_timestamp,
            'register_parcels_end_timestamp': end_timestamp,
            'parcel_ids': farm_ids,
            'parcel_request_times': parcel_request_times,
        }


    def fc_register_farm_parcels_thread_worker(self, index, farm_ids, entry_ids, entry_request_times):
        "running each request on a separated thread, storing result pointer args"
        self.logger.debug(f'Registering parcel {index}')
        elapsed_time, entry_id = self.task_register_farm_parcel(index, farm_ids)
        entry_ids[index] = entry_id
        entry_request_times[index] = elapsed_time

    def task_register_farm_parcel(self, farm_parcel_i, farm_ids):
        url = f'{FARMCALENDAR_BASE_URL}/api/v1/FarmParcels/'
        farm_id = farm_ids[farm_parcel_i]
        wkt, center_lat, center_long = self.fc_generate_square_geometry(farm_parcel_i)
        data = {
            "status": 1,
            "deleted_at": None,
            # "created_at": "2024-11-04T12:51:14.074000Z",
            # "updated_at": "2024-11-04T12:51:14.074000Z",
            "identifier": f"Parcel {farm_parcel_i}",
            "description": f"Farm parcel description {farm_parcel_i}",
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
            return elapsed_time, entry_id
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

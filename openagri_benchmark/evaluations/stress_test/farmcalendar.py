import time
import datetime
import random

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

    def _get_current_activities_ids(self):
        url = f'{FARMCALENDAR_BASE_URL}/api/v1/FarmCalendarActivities/'
        headers = self.base_headers.copy()
        response = requests.get(url,  headers=headers)
        entry_ids = []
        if response.status_code == 200:
            entry_data = response.json()
            graph = entry_data.get("@graph")
            entry_ids = [entry['@id'].split(':')[-1] for entry in graph]
        else:
            self.logger.error(response.json())
            response.raise_for_status()

        return entry_ids

    def fc_tasks(self):
        fc_results = {}

        reg_farms_results, farm_ids = self.fc_register_farms(num_farm=max(1, self.num_entries // 2), rps=self.rps)
        fc_results.update(reg_farms_results)

        reg_parcels_results, parcel_ids = self.fc_register_farm_parcels(num_parcels=self.num_entries, rps=self.rps, farm_ids=farm_ids)
        fc_results.update(reg_parcels_results)

        filter_parcels_results = self.fc_filter_farm_parcels_by_lat_lon(num_calls=self.num_entries, rps=self.rps, parcel_ids=parcel_ids)
        fc_results.update(filter_parcels_results)

        reg_act_type_results, gen_activity_type_ids, alerts_type_ids, obs_type_ids = self.fc_register_activity_type(
            num_types=max(3, self.num_entries // 2), rps=self.rps
        )
        fc_results.update(reg_act_type_results)

        reg_gen_activity_results = self.fc_register_gen_activity(
            num_activities=self.num_entries * 2, rps=self.rps, gen_activity_type_ids=gen_activity_type_ids
        )
        fc_results.update(reg_gen_activity_results)

        reg_obs_results = self.fc_register_obs(
            num_activities=self.num_entries * 2, rps=self.rps, parcel_ids=parcel_ids, obs_type_ids=obs_type_ids
        )
        fc_results.update(reg_obs_results)

        list_monthly_activities_results = self.fc_list_montly_calendar_activities(
            num_calls=self.min_num_operations * 2, rps=self.rps,
        )
        fc_results.update(list_monthly_activities_results)

        activities_ids = self._get_current_activities_ids()

        get_activity_results = self.fc_get_activity(
            num_calls=self.min_num_operations * 2, rps=self.rps,
            activities_ids=activities_ids
        )
        fc_results.update(get_activity_results)

        list_monthly_activities_results = self.fc_list_montly_calendar_activities(
            num_calls=self.min_num_operations * 2, rps=self.rps,
        )
        fc_results.update(list_monthly_activities_results)

        register_crops, crops_ids = self.fc_register_farm_crop(
            num_crops=max(self.min_num_operations, self.num_entries), rps=self.rps, parcel_ids=parcel_ids
        )
        fc_results.update(register_crops)

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
        farm_id = farm_ids[task_i % 2]
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


    def fc_filter_farm_parcels_by_lat_lon(self, num_calls, rps, parcel_ids):
        results = self.multithread_task(
            'filter_parcels',
            self.task_filter_parcels, num_calls, rps,
            parcel_ids=parcel_ids
        )

        return results

    def task_filter_parcels(self, task_i, parcel_ids):
        expected_parcel_id = parcel_ids[task_i]
        url = f'{FARMCALENDAR_BASE_URL}/api/v1/FarmParcels/'
        _, center_lat, center_long = self.fc_generate_square_geometry(task_i)
        # query_filter = "?contains_point=10%2C40"
        query_filter = {
            'contains_point': f'{center_lat},{center_long}'
        }
        headers = self.base_headers.copy()
        # Record start time before the request
        start_time = time.perf_counter()
        response = requests.get(url, params=query_filter, headers=headers)
        # Record end time after the request
        end_time = time.perf_counter()
        elapsed_time = end_time - start_time
        if response.status_code == 200:
            entry_data = response.json()
            graph = entry_data.get("@graph")
            entry = graph[0]
            entry_id = entry['@id']
            assert entry_id == expected_parcel_id, f"Wrong parcel returned when filtering for {task_i}: {entry_id} != {expected_parcel_id}"
            return elapsed_time
        else:
            self.logger.error(response.json())
            response.raise_for_status()


    def fc_register_activity_type(self, num_types, rps):
        activity_type_ids = [None] * num_types

        results = self.multithread_task(
            'register_activity_type',
            self.task_register_activity_type, num_types, rps,
            activity_type_ids=activity_type_ids
        )

        gen_activity_type_ids = []
        alerts_type_ids = []
        obs_type_ids = []
        for task_i, entry_id in enumerate(activity_type_ids):
            if task_i % 3 == 0:
                gen_activity_type_ids.append(entry_id)
            elif task_i % 3 == 1:
                alerts_type_ids.append(entry_id)
            elif task_i % 3 == 2:
                obs_type_ids.append(entry_id)

        return results, gen_activity_type_ids, alerts_type_ids, obs_type_ids

    def task_register_activity_type(self, task_i, activity_type_ids):
        url = f'{FARMCALENDAR_BASE_URL}/api/v1/FarmCalendarActivityTypes/'

        categories = ['activity', 'alert', 'observation']
        category = categories[task_i % 3]
        data = {
            "@type": "FarmActivityType",
            "name": f"New Activity Type % {task_i}",
            "description": 'Some description',
            "category": category,
            "background_color": "#007bff",
            "border_color": "#007bff",
            "text_color": "#000000",
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
            activity_type_ids[task_i] = entry_id
            return elapsed_time
        else:
            self.logger.error(response.json())
            response.raise_for_status()


    def fc_register_gen_activity(self, num_activities, rps, gen_activity_type_ids):
        results = self.multithread_task(
            'register_gen_activity',
            self.task_register_gen_activity, num_activities, rps,
            gen_activity_type_ids=gen_activity_type_ids
        )

        return results

    def task_register_gen_activity(self, task_i, gen_activity_type_ids):
        url = f'{FARMCALENDAR_BASE_URL}/api/v1/FarmCalendarActivities/'

        activity_start = datetime.datetime.now()
        activity_start.replace(day=1)
        activity_start = activity_start + datetime.timedelta(days=int(task_i / 2))
        activity_end = activity_start + datetime.timedelta(hours=1)
        activity_type_id = gen_activity_type_ids[task_i % len(gen_activity_type_ids)]
        activity_type_id = activity_type_id.replace(':FarmActivityType:', ':FarmCalendarActivityType:')
        data = {
            "@type": "FarmCalendarActivity",
            "activityType": {
                "@type": "FarmCalendarActivityType",
                "@id": activity_type_id
            },
            "title": f"new activity {task_i}",
            "details": f"activity details for {task_i}",
            "hasStartDatetime": activity_start.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "hasEndDatetime": activity_end.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "hasAgriParcel": None,
            "responsibleAgent": "someone",
            "usesAgriculturalMachinery": [],
            "isPartOfActivity": None
        }

        headers = self.base_headers.copy()
        # Record start time before the request
        start_time = time.perf_counter()
        response = requests.post(url, json=data, headers=headers)
        # Record end time after the request
        end_time = time.perf_counter()
        elapsed_time = end_time - start_time

        if response.status_code == 201:
            return elapsed_time
        else:
            self.logger.error(response.json())
            response.raise_for_status()

    def fc_register_obs(self, num_activities, rps, parcel_ids, obs_type_ids):
        results = self.multithread_task(
            'register_obs',
            self.task_register_obs, num_activities, rps,
            parcel_ids=parcel_ids, obs_type_ids=obs_type_ids
        )

        return results

    def task_register_obs(self, task_i, parcel_ids, obs_type_ids):
        url = f'{FARMCALENDAR_BASE_URL}/api/v1/Observations/'
        activity_start = datetime.datetime.now()
        activity_start.replace(day=15)
        activity_start = activity_start + datetime.timedelta(days=int(task_i / 2))
        activity_end = activity_start + datetime.timedelta(hours=1)

        parcel_id = parcel_ids[task_i % len(parcel_ids)]
        parcel_id = parcel_id.replace(':FarmParcel:', ':Parcel:')

        activity_type_id = obs_type_ids[task_i % len(obs_type_ids)]
        activity_type_id = activity_type_id.replace(':FarmActivityType:', ':FarmCalendarActivityType:')



        data = {
            "@type": "Observation",
            "activityType": {
                "@type": "FarmCalendarActivityType",
                "@id": activity_type_id
            },
            "title": f"new obs {task_i}",
            "details": f"activity details for {task_i}",
            "phenomenonTime": "2026-08-13T00:00:00Z",
            "hasEndDatetime": activity_end.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "hasAgriParcel": {
                "@type": "Parcel",
                "@id": parcel_id
            },
            "madeBySensor": {
                "@type": "Sensor",
                "name": "some sensor"
            },
            "hasResult": {
                "@type": "QuantityValue",
                "unit": "liters",
                "hasValue": f"{task_i} * i"
            },
            "observedProperty": "Humidity",
            "isPartOfActivity": None
        }

        headers = self.base_headers.copy()
        # Record start time before the request
        start_time = time.perf_counter()
        response = requests.post(url, json=data, headers=headers)
        # Record end time after the request
        end_time = time.perf_counter()
        elapsed_time = end_time - start_time

        if response.status_code == 201:
            return elapsed_time
        else:
            self.logger.error(response.json())
            response.raise_for_status()

    def fc_list_montly_calendar_activities(self, num_calls, rps):
        results = self.multithread_task(
            'monthly_activities',
            self.task_list_monthly_calendar_activities, num_calls, rps,
        )

        return results

    def task_list_monthly_calendar_activities(self, task_i):
        url = f'{FARMCALENDAR_BASE_URL}/api/v1/FarmCalendarActivities/'
        from_date = datetime.datetime.now().replace(day=1)
        to_date = from_date.replace(month=(from_date.month % 12) + 1)
        query_filter = {
            'fromDate':  from_date.strftime("%Y-%m-%d"),
            'toDate': to_date.strftime("%Y-%m-%d"),
        }
        headers = self.base_headers.copy()
        # Record start time before the request
        start_time = time.perf_counter()
        response = requests.get(url, params=query_filter, headers=headers)
        # Record end time after the request
        end_time = time.perf_counter()
        elapsed_time = end_time - start_time
        if response.status_code == 200:
            entry_data = response.json()
            graph = entry_data.get("@graph")
            # self.logger.debug(f'Total montly activity: {len(graph)} on : {response.url}')
            return elapsed_time
        else:
            self.logger.error(response.json())
            response.raise_for_status()

    def fc_get_activity(self, num_calls, rps, activities_ids):
        results = self.multithread_task(
            'get_activity',
            self.task_get_activity, num_calls, rps,
            activities_ids=activities_ids
        )

        return results

    def task_get_activity(self, task_i, activities_ids):
        activity_id = activities_ids[task_i % len(activities_ids)]
        url = f'{FARMCALENDAR_BASE_URL}/api/v1/FarmCalendarActivities/{activity_id}'
        headers = self.base_headers.copy()
        # Record start time before the request
        start_time = time.perf_counter()
        response = requests.get(url,headers=headers)
        # Record end time after the request
        end_time = time.perf_counter()
        elapsed_time = end_time - start_time
        if response.status_code == 200:
            entry_data = response.json()
            # graph = entry_data.get("@graph")
            return elapsed_time
        else:
            self.logger.error(response.json())
            response.raise_for_status()

    def fc_register_farm_crop(self, num_crops, rps, parcel_ids):
        crops_ids = [None] * num_crops
        results = self.multithread_task(
            'register_crop',
            self.task_register_farm_crop, num_crops, rps,
            parcel_ids=parcel_ids, crops_ids=crops_ids
        )

        return results, crops_ids

    def task_register_farm_crop(self, task_i, parcel_ids, crops_ids):
        url = f'{FARMCALENDAR_BASE_URL}/api/v1/FarmCrops/'
        parcel_id = parcel_ids[task_i % len(parcel_ids)]
        parcel_id = parcel_id.replace(':FarmParcel:', ':Parcel:')

        data = {
            "status": 1,
            "invalidatedAtTime": None,
            "name": f"Some Crop {task_i}",
            "description": "some descr",
            "hasAgriParcel": {
                "@type": "Parcel",
                "@id": parcel_id
            },
            "cropSpecies": {
                "@type": "CropType",
                "name": "Some species {task_i}",
                "variety": "Some variety {task_i}"
            },
            "growth_stage": "bulb"
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
            crops_ids[task_i] = entry_id
            return elapsed_time
        else:
            self.logger.error(response.json())
            response.raise_for_status()



evaluator = FCStressTest

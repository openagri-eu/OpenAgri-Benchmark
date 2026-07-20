import time
import datetime
from datetime import timedelta

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
        self.location_warmup_count = min(5, max(1, self.num_entries // 5))

    def _warmup_locations(self):
        """Create a small set of cached locations through the real API."""
        url = f'{WEATHER_BASE_URL}/api/v1/locations/locations/unique/'
        headers = self.base_headers.copy()
        self.logger.info(f"Creating {self.location_warmup_count} warmup locations for stress test.")

        locations = []
        for index in range(self.location_warmup_count):
            locations.append(
                {
                    "name": f"Warmup Location {index}",
                    "lat": 38.0 + (index * 0.1),
                    "lon": 23.0 + (index * 0.1),
                }
            )

        response = requests.post(url, json={"locations": locations}, headers=headers)
        if response.status_code not in [200, 409]:
            response.raise_for_status()
        return response

    def run(self):
        output = super().run()
        output.update(self.run_service_tasks('weather', self.wd_tasks))
        return output

    def wd_tasks(self):
        wd_results = {}

        self._warmup_locations()

        # Locations endpoints
        list_locations_results = self.wd_list_locations(num_calls=self.num_entries, rps=self.rps)
        wd_results.update(list_locations_results)

        get_locations_by_coords_results = self.wd_get_locations_by_coordinates(num_calls=self.num_entries, rps=self.rps)
        wd_results.update(get_locations_by_coords_results)

        add_locations_results = self.wd_add_locations(num_calls=max(1, self.num_entries // 5), rps=self.rps)
        wd_results.update(add_locations_results)

        # Forecast endpoints
        hourly_forecast_results = self.wd_get_hourly_forecast(num_calls=self.num_entries, rps=self.rps)
        wd_results.update(hourly_forecast_results)

        hourly_spray_forecast_results = self.wd_get_hourly_spray_forecast(num_calls=self.num_entries, rps=self.rps)
        wd_results.update(hourly_spray_forecast_results)

        daily_forecast_results = self.wd_get_daily_forecast(num_calls=self.num_entries, rps=self.rps)
        wd_results.update(daily_forecast_results)

        # History endpoints
        hourly_history_results = self.wd_get_hourly_history(num_calls=self.num_entries, rps=self.rps)
        wd_results.update(hourly_history_results)

        daily_history_results = self.wd_get_daily_history(num_calls=self.num_entries, rps=self.rps)
        wd_results.update(daily_history_results)

        return wd_results

    # =========================================================================
    # LOCATIONS ENDPOINTS
    # =========================================================================

    def wd_list_locations(self, num_calls, rps):
        """GET /api/v1/locations/ - List all cached locations"""
        results = self.multithread_task(
            'list_locations',
            self.task_list_locations, num_calls, rps,
        )
        return results

    def task_list_locations(self, _task_i):
        url = f'{WEATHER_BASE_URL}/api/v1/locations/locations/'
        headers = self.base_headers.copy()
        
        start_time = time.perf_counter()
        response = requests.get(url, headers=headers)
        end_time = time.perf_counter()
        
        if response.status_code == 200:
            return end_time - start_time
        else:
            response.raise_for_status()

    def wd_get_locations_by_coordinates(self, num_calls, rps):
        """GET /api/v1/locations/locations/by-coordinates/ - Get location by coordinates"""
        results = self.multithread_task(
            'get_locations_by_coordinates',
            self.task_get_locations_by_coordinates, num_calls, rps,
        )
        return results

    def task_get_locations_by_coordinates(self, task_i):
        url = f'{WEATHER_BASE_URL}/api/v1/locations/locations/by-coordinates/'
        headers = self.base_headers.copy()
        
        start_time = time.perf_counter()
        response = requests.get(url, params={"lat": 38.0 + (task_i * 0.1), "lon": 23.0 + (task_i * 0.1)}, headers=headers)
        end_time = time.perf_counter()
        
        if response.status_code in [200, 404]:
            return end_time - start_time
        else:
            response.raise_for_status()

    def wd_add_locations(self, num_calls, rps):
        """POST /api/v1/locations/locations/ - Add new locations"""
        results = self.multithread_task(
            'add_locations',
            self.task_add_locations, num_calls, rps,
        )
        return results

    def task_add_locations(self, task_i):
        url = f'{WEATHER_BASE_URL}/api/v1/locations/locations/'
        headers = self.base_headers.copy()
        
        data = {
            "locations": [
                {
                    "name": f"Test Location {task_i}",
                    "lat": 40.0 + (task_i % 10),
                    "lon": 21.0 + (task_i % 10)
                }
            ]
        }
        
        start_time = time.perf_counter()
        response = requests.post(url, json=data, headers=headers)
        end_time = time.perf_counter()
        
        if response.status_code in [200, 201, 409]:  # 409 = already exists
            return end_time - start_time
        else:
            response.raise_for_status()

    # =========================================================================
    # FORECAST ENDPOINTS
    # =========================================================================

    def wd_get_hourly_forecast(self, num_calls, rps):
        """GET /api/v1/forecast/hourly/ - Hourly weather forecast"""
        results = self.multithread_task(
            'get_hourly_forecast',
            self.task_get_hourly_forecast, num_calls, rps,
        )
        return results

    def task_get_hourly_forecast(self, task_i):
        url = f'{WEATHER_BASE_URL}/api/v1/forecast/hourly/'
        headers = self.base_headers.copy()
        
        params = {
            "lat": 38.0 + (task_i % 5),
            "lon": 23.0 + (task_i % 5),
            "days": 5
        }
        
        start_time = time.perf_counter()
        response = requests.get(url, params=params, headers=headers)
        end_time = time.perf_counter()
        
        if response.status_code == 200:
            return end_time - start_time
        else:
            response.raise_for_status()

    def wd_get_hourly_spray_forecast(self, num_calls, rps):
        """GET /api/v1/forecast/hourly/spray/ - Spray condition forecast"""
        results = self.multithread_task(
            'get_hourly_spray_forecast',
            self.task_get_hourly_spray_forecast, num_calls, rps,
        )
        return results

    def task_get_hourly_spray_forecast(self, task_i):
        url = f'{WEATHER_BASE_URL}/api/v1/forecast/hourly/spray/'
        headers = self.base_headers.copy()
        
        params = {
            "lat": 38.0 + (task_i % 5),
            "lon": 23.0 + (task_i % 5),
            "days": 5
        }
        
        start_time = time.perf_counter()
        response = requests.get(url, params=params, headers=headers)
        end_time = time.perf_counter()
        
        if response.status_code == 200:
            return end_time - start_time
        else:
            response.raise_for_status()

    def wd_get_daily_forecast(self, num_calls, rps):
        """GET /api/v1/forecast/daily/irrigation/ - Daily irrigation forecast"""
        results = self.multithread_task(
            'get_daily_forecast',
            self.task_get_daily_forecast, num_calls, rps,
        )
        return results

    def task_get_daily_forecast(self, task_i):
        url = f'{WEATHER_BASE_URL}/api/v1/forecast/daily/irrigation/'
        headers = self.base_headers.copy()
        
        params = {
            "lat": 38.0 + (task_i % 5),
            "lon": 23.0 + (task_i % 5),
            "days": 10
        }
        
        start_time = time.perf_counter()
        response = requests.get(url, params=params, headers=headers)
        end_time = time.perf_counter()
        
        if response.status_code == 200:
            return end_time - start_time
        else:
            response.raise_for_status()

    # =========================================================================
    # HISTORY ENDPOINTS
    # =========================================================================

    def wd_get_hourly_history(self, num_calls, rps):
        """POST /api/v1/history/hourly/ - Hourly historical weather data"""
        results = self.multithread_task(
            'get_hourly_history',
            self.task_get_hourly_history, num_calls, rps,
        )
        return results

    def task_get_hourly_history(self, task_i):
        url = f'{WEATHER_BASE_URL}/api/v1/history/hourly/'
        headers = self.base_headers.copy()
        
        end_date = datetime.date.today()
        start_date = end_date - timedelta(days=7)
        
        data = {
            "lat": 38.0 + (task_i % 5),
            "lon": 23.0 + (task_i % 5),
            "start": start_date.isoformat(),
            "end": end_date.isoformat(),
            "variables": ["temperature_2m", "relative_humidity_2m", "wind_speed_10m"],
            "radius_km": 10.0
        }

        start_time = time.perf_counter()
        response = requests.post(url, json=data, headers=headers)
        end_time = time.perf_counter()
        
        if response.status_code == 200:
            return end_time - start_time
        else:
            response.raise_for_status()

    def wd_get_daily_history(self, num_calls, rps):
        """POST /api/v1/history/daily/ - Daily historical weather data"""
        results = self.multithread_task(
            'get_daily_history',
            self.task_get_daily_history, num_calls, rps,
        )
        return results

    def task_get_daily_history(self, task_i):
        url = f'{WEATHER_BASE_URL}/api/v1/history/daily/'
        headers = self.base_headers.copy()
        
        end_date = datetime.date.today()
        start_date = end_date - timedelta(days=30)
        
        data = {
            "lat": 38.0 + (task_i % 5),
            "lon": 23.0 + (task_i % 5),
            "start": start_date.isoformat(),
            "end": end_date.isoformat(),
            "variables": ["temperature_2m_max", "temperature_2m_min", "precipitation_sum"],
            "radius_km": 10.0
        }
        
        start_time = time.perf_counter()
        response = requests.post(url, json=data, headers=headers)
        end_time = time.perf_counter()
        
        if response.status_code == 200:
            return end_time - start_time
        else:
            response.raise_for_status()


evaluator = WDStressTest

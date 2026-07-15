import time
import datetime
from datetime import timedelta, timezone
from typing import List

import requests
import respx
from httpx import Response
from pymongo import MongoClient

from openagri_benchmark.conf import (
    WEATHER_BASE_URL,
)

from .base import BaseStressTestEval


# =============================================================================
# Mock Response Generators for Open-Meteo API
# =============================================================================

def generate_hourly_forecast_response(lat: float, lon: float, days: int = 5):
    """Generate synthetic Open-Meteo hourly forecast response"""
    now = datetime.datetime.now(timezone.utc)
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    
    timestamps = []
    temp_data = []
    humidity_data = []
    wind_data = []
    precip_data = []
    pressure_data = []
    visibility_data = []
    uv_data = []
    
    for day in range(days):
        for hour in range(24):
            ts = start + timedelta(days=day, hours=hour)
            timestamps.append(ts.isoformat())
            
            # Deterministic synthetic values based on coordinates
            base_temp = 20.0 + (lat % 10) + (lon % 10)
            temp_data.append(round(base_temp + (hour - 12) * 0.5, 2))
            humidity_data.append(50 + (hour % 30))
            wind_data.append(round(5.0 + (hour % 10) * 0.5, 2))
            precip_data.append(0.1 if hour % 8 == 0 else 0.0)
            pressure_data.append(1013.0 + (hour % 5))
            visibility_data.append(10000.0)
            uv_data.append(3.0 if 6 <= hour <= 18 else 0.0)
    
    return {
        "latitude": lat,
        "longitude": lon,
        "hourly": {
            "time": timestamps,
            "temperature_2m": temp_data,
            "relative_humidity_2m": humidity_data,
            "wind_speed_10m": wind_data,
            "precipitation": precip_data,
            "pressure_msl": pressure_data,
            "visibility": visibility_data,
            "uv_index": uv_data,
        }
    }


def generate_daily_forecast_response(lat: float, lon: float, days: int = 16):
    """Generate synthetic Open-Meteo daily forecast response"""
    today = datetime.date.today()
    
    dates = []
    precip_sum = []
    precip_prob = []
    temp_min = []
    temp_max = []
    et0 = []
    
    for day in range(days):
        date_obj = today + timedelta(days=day)
        dates.append(date_obj.isoformat())
        
        base_temp = 20.0 + (lat % 10) + (lon % 10)
        precip_sum.append(round(2.0 if day % 3 == 0 else 0.5, 2))
        precip_prob.append(60 if day % 3 == 0 else 20)
        temp_min.append(round(base_temp - 5, 2))
        temp_max.append(round(base_temp + 5, 2))
        et0.append(round(4.5 + (day % 3) * 0.5, 2))
    
    return {
        "latitude": lat,
        "longitude": lon,
        "daily": {
            "time": dates,
            "precipitation_sum": precip_sum,
            "precipitation_probability_max": precip_prob,
            "temperature_2m_min": temp_min,
            "temperature_2m_max": temp_max,
            "et0_fao_evapotranspiration": et0,
        }
    }


def generate_hourly_history_response(lat: float, lon: float, start: datetime.date, end: datetime.date, variables: List[str]):
    """Generate synthetic Open-Meteo hourly history response"""
    timestamps = []
    data_dict = {var: [] for var in variables}
    
    current_date = start
    while current_date <= end:
        for hour in range(24):
            ts = datetime.datetime.combine(current_date, datetime.time(hour=hour))
            timestamps.append(ts.isoformat())
            
            # Generate values for requested variables
            base_value = 20.0 + (lat % 10) + (lon % 10)
            for var in variables:
                if "temperature" in var:
                    data_dict[var].append(round(base_value + (hour - 12) * 0.5, 2))
                elif "humidity" in var or "relative_humidity" in var:
                    data_dict[var].append(50 + (hour % 30))
                elif "wind" in var:
                    data_dict[var].append(round(5.0 + (hour % 10) * 0.5, 2))
                elif "precipitation" in var:
                    data_dict[var].append(0.1 if hour % 8 == 0 else 0.0)
                else:
                    data_dict[var].append(10.0)
        
        current_date += timedelta(days=1)
    
    return {
        "latitude": lat,
        "longitude": lon,
        "hourly": {
            "time": timestamps,
            **data_dict
        }
    }


def generate_daily_history_response(lat: float, lon: float, start: datetime.date, end: datetime.date, variables: List[str]):
    """Generate synthetic Open-Meteo daily history response"""
    dates = []
    data_dict = {var: [] for var in variables}
    
    current_date = start
    while current_date <= end:
        dates.append(current_date.isoformat())
        
        base_value = 20.0 + (lat % 10) + (lon % 10)
        for var in variables:
            if "temperature" in var and "max" in var:
                data_dict[var].append(round(base_value + 5, 2))
            elif "temperature" in var and "min" in var:
                data_dict[var].append(round(base_value - 5, 2))
            elif "precipitation" in var:
                data_dict[var].append(round(2.0, 2))
            else:
                data_dict[var].append(15.0)
        
        current_date += timedelta(days=1)
    
    return {
        "latitude": lat,
        "longitude": lon,
        "daily": {
            "time": dates,
            **data_dict
        }
    }

class WDStressTest(BaseStressTestEval):
    def __init__(self, controller, logger, setup_id, output_dir, admin_user, admin_pass):
        super().__init__(controller, logger, setup_id, output_dir, admin_user, admin_pass)
        self.health_check_urls = [
            f"{WEATHER_BASE_URL}/docs",
        ]
        self.mock_router = None
        self._setup_mocks()
        self._setup_mongodb_test_data()

    def _setup_mocks(self):
        """Setup respx mocks for Open-Meteo API calls"""
        try:
            self.mock_router = respx.mock(assert_all_called=False)
            self.mock_router.start()
            
            # Mock forecast endpoint - handles both hourly and daily
            self.mock_router.get(url__regex=r"https://api\.open-meteo\.com/v1/forecast.*").mock(
                side_effect=self._handle_forecast_request
            )
            
            # Mock archive (history) endpoint - handles both hourly and daily
            self.mock_router.get(url__regex=r"https://archive-api\.open-meteo\.com/v1/archive.*").mock(
                side_effect=self._handle_history_request
            )
            
            self.logger.info("✓ HTTP mocks for Open-Meteo APIs configured successfully")
        except Exception as e:
            self.logger.error(f"Failed to setup respx mocks: {e}")
            raise

    def _handle_forecast_request(self, request):
        """Dynamic response handler for forecast requests"""
        params = dict(request.url.params)
        lat = float(params.get("latitude", 38.0))
        lon = float(params.get("longitude", 23.0))
        days = int(params.get("forecast_days", 5))
        
        if "hourly" in params:
            response_data = generate_hourly_forecast_response(lat, lon, days)
        else:
            response_data = generate_daily_forecast_response(lat, lon, days)
        
        return Response(200, json=response_data)

    def _handle_history_request(self, request):
        """Dynamic response handler for history requests"""
        params = dict(request.url.params)
        lat = float(params.get("latitude", 38.0))
        lon = float(params.get("longitude", 23.0))
        start = datetime.date.fromisoformat(params.get("start_date"))
        end = datetime.date.fromisoformat(params.get("end_date"))
        
        if "hourly" in params:
            variables = params["hourly"].split(",")
            response_data = generate_hourly_history_response(lat, lon, start, end, variables)
        else:
            variables = params["daily"].split(",")
            response_data = generate_daily_history_response(lat, lon, start, end, variables)
        
        return Response(200, json=response_data)

    def _setup_mongodb_test_data(self):
        """Pre-populate MongoDB with test locations for GET endpoints"""
        try:
            # Extract host from WEATHER_BASE_URL (e.g., http://localhost:8004 -> localhost)
            host = WEATHER_BASE_URL.split("://")[1].split(":")[0]
            
            # Connect to MongoDB - adjust connection string if needed
            mongodb_uri = f"mongodb://root:root@{host}:27017/"
            client = MongoClient(mongodb_uri, serverSelectionTimeoutMS=5000)
            
            # Test connection
            client.admin.command('ping')
            
            db = client["weather_db"]
            
            # Clear existing test data
            db["CachedLocation"].delete_many({"name": {"$regex": "^Stress Test Location"}})
            
            # Insert test locations for GET endpoints
            test_locations = []
            for i in range(50):
                location_doc = {
                    "name": f"Stress Test Location {i}",
                    "location": {
                        "type": "Point",
                        "coordinates": [i * 0.5, i * 0.5]  # [lon, lat]
                    },
                    "created_at": datetime.datetime.now(timezone.utc)
                }
                test_locations.append(location_doc)
            
            if test_locations:
                db["CachedLocation"].insert_many(test_locations)
                self.logger.info(f"✓ Pre-populated MongoDB with {len(test_locations)} test locations")
            
            client.close()
        except Exception as e:
            self.logger.warning(f"Could not pre-populate MongoDB (tests will still work): {e}")

    def run(self):
        output = super().run()
        try:
            output.update(self.run_service_tasks('weather', self.wd_tasks))
        finally:
            # Cleanup mocks
            if self.mock_router:
                self.mock_router.stop()
        return output

    def wd_tasks(self):
        wd_results = {}

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

    def task_list_locations(self, task_i):
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
        response = requests.get(url, params={"lat": task_i * 0.5, "lon": task_i * 0.5}, headers=headers)
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

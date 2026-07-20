import logging
from datetime import date, datetime, timedelta, timezone
from typing import List, Optional, Protocol, Union

from src.schemas.history_data import DailyObservationOut, HourlyObservationOut


logger = logging.getLogger(__name__)


class WeatherProvider(Protocol):
    async def get_hourly_history(
        self, lat: float, lon: float, start: date, end: date, variables: List[str]
    ) -> List[HourlyObservationOut]:
        ...

    async def get_daily_history(
        self, lat: float, lon: float, start: date, end: date, variables: List[str]
    ) -> List[DailyObservationOut]:
        ...

    async def get_hourly_forecast(
        self, lat: float, lon: float, days: int = 5
    ) -> List[HourlyObservationOut]:
        ...

    async def get_daily_forecast(
        self, lat: float, lon: float, days: int = 16
    ) -> List[DailyObservationOut]:
        ...


class OpenMeteoClient:
    HOURLY_FORECAST_VARIABLES = [
        "temperature_2m",
        "relative_humidity_2m",
        "dew_point_2m",
        "apparent_temperature",
        "precipitation",
        "rain",
        "snowfall",
        "snow_depth",
        "pressure_msl",
        "surface_pressure",
        "cloud_cover",
        "wind_speed_10m",
        "wind_direction_10m",
        "wind_gusts_10m",
        "visibility",
        "uv_index",
    ]

    DAILY_FORECAST_VARIABLES = [
        "precipitation_sum",
        "precipitation_probability_max",
        "temperature_2m_min",
        "temperature_2m_max",
        "et0_fao_evapotranspiration",
    ]

    def _base_value(self, lat: float, lon: float) -> float:
        return 20.0 + (lat % 10) + (lon % 10)

    async def get_hourly_history(
        self,
        lat: float,
        lon: float,
        start: date,
        end: date,
        variables: List[str],
    ) -> List[HourlyObservationOut]:
        timestamps: List[datetime] = []
        data_dict = {variable: [] for variable in variables}

        current_date = start
        while current_date <= end:
            for hour in range(24):
                timestamps.append(datetime.combine(current_date, datetime.min.time(), tzinfo=timezone.utc).replace(hour=hour))
                for variable in variables:
                    data_dict[variable].append(self._value_for_hourly_variable(variable, lat, lon, hour))
            current_date += timedelta(days=1)

        logger.info(
            "Mock Open-Meteo hourly history: %d hours for (%s, %s) from %s to %s",
            len(timestamps),
            lat,
            lon,
            start,
            end,
        )
        return [
            HourlyObservationOut(
                timestamp=timestamp,
                values={variable: data_dict[variable][index] for variable in variables},
            )
            for index, timestamp in enumerate(timestamps)
        ]

    async def get_daily_history(
        self,
        lat: float,
        lon: float,
        start: date,
        end: date,
        variables: List[str],
    ) -> List[DailyObservationOut]:
        results: List[DailyObservationOut] = []
        current_date = start
        day_index = 0
        while current_date <= end:
            values = {
                variable: self._value_for_daily_variable(variable, lat, lon, day_index)
                for variable in variables
            }
            results.append(DailyObservationOut(date=current_date, values=values))
            current_date += timedelta(days=1)
            day_index += 1
        logger.info(
            "Mock Open-Meteo daily history: %d days for (%s, %s) from %s to %s",
            len(results),
            lat,
            lon,
            start,
            end,
        )
        return results

    async def get_hourly_forecast(
        self, lat: float, lon: float, days: int = 5
    ) -> List[HourlyObservationOut]:
        now = datetime.now(timezone.utc)
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        results: List[HourlyObservationOut] = []

        for day in range(days):
            for hour in range(24):
                timestamp = start + timedelta(days=day, hours=hour)
                values = {
                    variable: self._value_for_hourly_variable(variable, lat, lon, hour)
                    for variable in self.HOURLY_FORECAST_VARIABLES
                }
                results.append(HourlyObservationOut(timestamp=timestamp, values=values))

        logger.info(
            "Mock Open-Meteo hourly forecast: %d hours for (%s, %s), %d days",
            len(results),
            lat,
            lon,
            days,
        )
        return results

    async def get_daily_forecast(
        self, lat: float, lon: float, days: int = 16
    ) -> List[DailyObservationOut]:
        today = date.today()
        results: List[DailyObservationOut] = []

        for day in range(days):
            current_date = today + timedelta(days=day)
            values = {
                variable: self._value_for_daily_forecast_variable(variable, lat, lon, day)
                for variable in self.DAILY_FORECAST_VARIABLES
            }
            results.append(DailyObservationOut(date=current_date, values=values))

        logger.info(
            "Mock Open-Meteo daily forecast: %d days for (%s, %s)",
            len(results),
            lat,
            lon,
        )
        return results

    def _value_for_hourly_variable(self, variable: str, lat: float, lon: float, hour: int) -> Union[float, int]:
        base = self._base_value(lat, lon)
        if variable == "temperature_2m":
            return round(base + (hour - 12) * 0.5, 2)
        if variable == "relative_humidity_2m":
            return 50 + (hour % 30)
        if variable == "dew_point_2m":
            return round(base - 2.5, 2)
        if variable == "apparent_temperature":
            return round(base + 1.5, 2)
        if variable == "precipitation":
            return 0.1 if hour % 8 == 0 else 0.0
        if variable == "rain":
            return 0.05 if hour % 8 == 0 else 0.0
        if variable == "snowfall":
            return 0.0
        if variable == "snow_depth":
            return 0.0
        if variable == "pressure_msl":
            return 1013.0 + (hour % 5)
        if variable == "surface_pressure":
            return 1008.0 + (hour % 5)
        if variable == "cloud_cover":
            return 30 + (hour % 50)
        if variable == "wind_speed_10m":
            return round(5.0 + (hour % 10) * 0.5, 2)
        if variable == "wind_direction_10m":
            return 90 + (hour * 10) % 360
        if variable == "wind_gusts_10m":
            return round(7.0 + (hour % 10) * 0.75, 2)
        if variable == "visibility":
            return 10000.0
        if variable == "uv_index":
            return 3.0 if 6 <= hour <= 18 else 0.0
        return round(base, 2)

    def _value_for_daily_variable(self, variable: str, lat: float, lon: float, day: int) -> Union[float, int]:
        base = self._base_value(lat, lon)
        if variable == "precipitation_sum":
            return round(2.0 if day % 3 == 0 else 0.5, 2)
        if variable == "precipitation_probability_max":
            return 60 if day % 3 == 0 else 20
        if variable == "temperature_2m_min":
            return round(base - 5, 2)
        if variable == "temperature_2m_max":
            return round(base + 5, 2)
        if variable == "et0_fao_evapotranspiration":
            return round(4.5 + (day % 3) * 0.5, 2)
        return round(base, 2)

    def _value_for_daily_forecast_variable(self, variable: str, lat: float, lon: float, day: int) -> Union[float, int]:
        return self._value_for_daily_variable(variable, lat, lon, day)


class WeatherClientFactory:
    _provider: Optional[WeatherProvider] = None

    @classmethod
    def get_provider(cls) -> WeatherProvider:
        if cls._provider is None:
            cls._provider = OpenMeteoClient()
        return cls._provider

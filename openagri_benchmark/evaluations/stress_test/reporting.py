import copy
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import requests


from openagri_benchmark.conf import (
    REPORTING_BASE_URL,
    REPORTING_STRESS_TEST_LISTENER_PORT,
)


from .base import BaseStressTestEval


# Local listener for the Reporting service's opt-in stress test callback
# (ENABLE_STRESS_TEST_NOTIFICATIONS / STRESS_TEST_CALLBACK_URL on that
# service). Report generation runs as a BackgroundTask there — POST returns
# a uuid almost instantly, well before the PDF exists — so instead of
# polling GET repeatedly, the service notifies this listener once the PDF
# is written, and we measure submit-to-ready time from that.


class _ReportCallbackHandler(BaseHTTPRequestHandler):
    events = {} 

    def do_POST(self):
        length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(length)
        try:
            report_uuid = json.loads(body).get('uuid')
        except Exception:
            report_uuid = None
        event = self.events.get(report_uuid) if report_uuid else None
        if event:
            event.set()
        self.send_response(204)
        self.end_headers()

    def log_message(self, format, *args):
        pass


_PARCEL_NAMES = [
    "North Polder Field",
    "Zuidpolder Plot",
    "Flevoland Grain Field",
    "Almere Dairy Meadow",
    "Lelystad Potato Field",
]

_RESPONSIBLE_AGENT = "Sophie Bakker, Field Agronomist"

_OBS_DAYS = ["2026-03-15", "2026-03-16", "2026-03-17", "2026-03-18", "2026-03-19", "2026-03-20", "2026-03-21"]
_OBS_MOISTURE_IRRIGATION_DAYS = {"2026-03-18", "2026-03-21"}

_OBS_TEMPLATE = [
    ("08:15", "08:30", "temperature", "CEL", "Soil temperature reading at 10cm depth, mid-morning.",
     [11.8, 12.1, 13.0, 13.4, 14.0, 14.3, 14.6]),
    ("12:00", "12:05", "humidity", "%", "Relative humidity reading, midday.",
     [72, 75, 68, 70, 66, 73, 69]),
    ("15:00", "15:10", "moisture", "P1", "Soil moisture reading, afternoon check.",
     [22.0, 20.5, 18.7, 24.2, 21.3, 19.8, 23.5]),
    ("18:00", "18:05", "rainfall", "MM", "Daily rainfall total recorded at end of day.",
     [0.0, 2.4, 0.0, 0.0, 1.2, 3.6, 0.0]),
]

_OBSERVATIONS = [
    {
        "@type": "Observation",
        "phenomenonTime": f"{day}T{start}:00Z",
        "hasStartDatetime": f"{day}T{start}:00Z",
        "hasEndDatetime": f"{day}T{end}:00Z",
        "observedProperty": prop,
        "responsibleAgent": _RESPONSIBLE_AGENT,
        "details": (
            "Soil moisture reading following an irrigation cycle."
            if prop == "moisture" and day in _OBS_MOISTURE_IRRIGATION_DAYS
            else details
        ),
        "hasResult": {"@type": "Property", "hasValue": str(value), "unit": unit},
    }
    for start, end, prop, unit, details, values in _OBS_TEMPLATE
    for day, value in zip(_OBS_DAYS, values)
]

_NUM_OPERATIONS = 10  

_IRRIGATION_SYSTEMS = ["Center Pivot Irrigation", "Drip Irrigation System", "Sprinkler Irrigation", "Furrow Irrigation"]
_FERTILIZERS = ["npk-15-15-15", "organic-compost-blend", "urea-46", "potassium-sulfate"]
_APPLICATION_METHODS = ["Broadcast Spreading", "Fertigation", "Foliar Spray", "Band Application"]
_PESTICIDES = ["fungicide-x", "herbicide-y", "insecticide-z", "copper-fungicide"]

_IRRIGATION_DATA = {
    "@graph": [
        {
            "@id": f"urn:ngsi-ld:IrrigationOperation:polderland-irr-{i + 1:03d}",
            "@type": "IrrigationOperation",
            "operatedOn": {"@id": f"urn:ngsi-ld:AgriParcel:{_PARCEL_NAMES[i % len(_PARCEL_NAMES)].lower().replace(' ', '-')}"},
            "hasStartDatetime": f"2026-03-{15 + i:02d}T{8 + (i % 4):02d}:00:00Z",
            "hasEndDatetime": f"2026-03-{15 + i:02d}T{11 + (i % 4):02d}:30:00Z",
            "hasAppliedAmount": {"numericValue": 80 + (i * 11) % 90, "unit": "Cubic Meter"},
            "usesIrrigationSystem": _IRRIGATION_SYSTEMS[i % len(_IRRIGATION_SYSTEMS)],
        }
        for i in range(_NUM_OPERATIONS)
    ]
}

_FERTILIZATION_DATA = {
    "@graph": [
        {
            "@id": f"urn:ngsi-ld:FertilizationOperation:polderland-fert-{i + 1:03d}",
            "@type": "FertilizationOperation",
            "operatedOn": {"@id": f"urn:ngsi-ld:AgriParcel:{_PARCEL_NAMES[i % len(_PARCEL_NAMES)].lower().replace(' ', '-')}"},
            "hasStartDatetime": f"2026-03-{15 + i:02d}T08:00:00Z",
            "hasEndDatetime": f"2026-03-{15 + i:02d}T{9 + (i % 3):02d}:30:00Z",
            "hasAppliedAmount": {"numericValue": 120 + (i * 13) % 110, "unit": "Kilogram"},
            "usesFertilizer": {"@id": f"urn:ngsi-ld:Fertilizer:{_FERTILIZERS[i % len(_FERTILIZERS)]}"},
            "hasApplicationMethod": _APPLICATION_METHODS[i % len(_APPLICATION_METHODS)],
        }
        for i in range(_NUM_OPERATIONS)
    ]
}

_PESTICIDES_DATA = {
    "@graph": [
        {
            "@id": f"urn:ngsi-ld:CropProtectionOperation:polderland-pest-{i + 1:03d}",
            "@type": "CropProtectionOperation",
            "operatedOn": {"@id": f"urn:ngsi-ld:AgriParcel:{_PARCEL_NAMES[i % len(_PARCEL_NAMES)].lower().replace(' ', '-')}"},
            "hasStartDatetime": f"2026-03-{15 + i:02d}T07:00:00Z",
            "hasEndDatetime": f"2026-03-{15 + i:02d}T09:00:00Z",
            "hasAppliedAmount": {"numericValue": 8 + (i * 3) % 20, "unit": "Liter"},
            "usesPesticide": {"@id": f"urn:ngsi-ld:Pesticide:{_PESTICIDES[i % len(_PESTICIDES)]}"},
        }
        for i in range(_NUM_OPERATIONS)
    ]
}

# (id_prefix, name, species, breed, group, description, birthdate, sex, is_castrated)
_ANIMALS = [
    ("cow", "Klara", "Bos taurus", "Holstein Friesian", "Main Dairy Herd", "Holstein dairy cow.", "2022-05-10", 1, False),
    ("cow", "Mila", "Bos taurus", "Jersey", "Main Dairy Herd", "Jersey dairy cow, high milk yield.", "2023-02-20", 1, False),
    ("cow", "Fleur", "Bos taurus", "Holstein Friesian", "Dry Herd", "Holstein dairy cow, retired from milking.", "2018-07-02", 1, False),
    ("cow", "Bram", "Bos taurus", "Meuse-Rhine-Yssel", "Main Dairy Herd", "Breeding bull.", "2021-11-14", 0, False),
    ("cow", "Saar", "Bos taurus", "Groninger Blaarkop", "Main Dairy Herd", "Groninger Blaarkop dairy cow.", "2020-09-05", 1, False),
    ("cow", "Vera", "Bos taurus", "Holstein Friesian", "Young Stock", "Holstein heifer, not yet calved.", "2024-06-01", 1, False),
    ("sheep", "Noor", "Ovis aries", "Texel", "Sheep Flock", "Texel ewe, kept for wool and lambing.", "2023-01-30", 1, False),
    ("sheep", "Anke", "Ovis aries", "Texel", "Sheep Flock", "Texel ram.", "2022-09-05", 0, False),
    ("sheep", "Sanne", "Ovis aries", "Drenthe Heath Sheep", "Sheep Flock", "Drenthe Heath ewe.", "2023-04-12", 1, False),
    ("sheep", "Daan", "Ovis aries", "Drenthe Heath Sheep", "Sheep Flock", "Drenthe Heath wether, castrated.", "2023-04-12", 0, True),
    ("goat", "Liv", "Capra aegagrus hircus", "Dutch Landrace", "Goat Herd", "Dutch Landrace dairy goat.", "2022-03-22", 1, False),
    ("goat", "Freya", "Capra aegagrus hircus", "Dutch Landrace", "Goat Herd", "Dutch Landrace goat kid.", "2024-04-18", 1, False),
    ("goat", "Tess", "Capra aegagrus hircus", "Dutch Landrace", "Goat Herd", "Dutch Landrace dairy goat.", "2021-08-09", 1, False),
    ("goat", "Guus", "Capra aegagrus hircus", "Dutch Landrace", "Goat Herd", "Dutch Landrace billy goat.", "2020-12-25", 0, False),
]

_ANIMAL_DATA = {
    "@graph": [
        {
            "@id": f"urn:ngsi-ld:FarmAnimal:polderland-{prefix}-{i + 1:03d}",
            "nationalID": f"NL-AN-{i + 1:03d}",
            "name": name,
            "description": description,
            "species": species,
            "sex": sex,
            "isCastrated": is_castrated,
            "breed": breed,
            "birthdate": birthdate,
            "isMemberOfAnimalGroup": {"hasName": group},
            "status": 0 if group == "Dry Herd" else 1,
            "hasAgriParcel": {"@id": "urn:ngsi-ld:AgriParcel:almere-dairy-meadow"},
            "dateCreated": f"2026-03-01T{10 + i:02d}:00:00Z",
            "dateModified": "2026-03-15T10:00:00Z",
            "invalidatedAtTime": "2026-03-10T09:00:00Z" if group == "Dry Herd" else None,
        }
        for i, (prefix, name, species, breed, group, description, birthdate, sex, is_castrated) in enumerate(_ANIMALS)
    ]
}

_COMPOST_MATERIALS = [
    ("Potato Haulm", 180),
    ("Straw", 60),
    ("Grass Clippings", 90),
    ("Wood Chips", 45),
    ("Manure", 220),
    ("Vegetable Trimmings", 75),
]

_COMPOST_DATES = ["2026-03-18", "2026-03-25", "2026-04-01", "2026-04-08", "2026-04-15", "2026-04-22"]

_COMPOST_DATA = {
    "@graph": [
        {
            "@id": f"urn:ngsi-ld:CompostTurningOperation:polderland-compost-{i + 1:03d}",
            "@type": "CompostTurningOperation",
            "title": "Weekly Compost Check" if i == 0 else f"Compost Turning, Week {i + 1}",
            "details": f"Turning of the compost pile at Lelystad Potato Field, week {i + 1}.",
            "hasStartDatetime": f"{_COMPOST_DATES[i]}T08:00:00Z",
            "hasEndDatetime": f"{_COMPOST_DATES[i]}T09:00:00Z",
            "responsibleAgent": _RESPONSIBLE_AGENT,
            "isOperatedOn": {"@id": "urn:ngsi-ld:CompostPile:polderland-pile-01"},
            "hasAgriParcel": {"@id": "urn:ngsi-ld:AgriParcel:lelystad-potato-field"},
            "usesAgriculturalMachinery": [{"@id": "urn:ngsi-ld:AgriculturalMachinery:tractor-01"}],
            "hasMeasurement": [
                {
                    "hasMember": [
                        {
                            "@id": f"urn:ngsi-ld:CropObservation:polderland-obs-{i + 1:03d}",
                            "@type": "Observation",
                            "type": "observed",
                            "phenomenonTime": f"{_COMPOST_DATES[i]}T08:15:00Z",
                            "observedProperty": "temperature",
                            "hasResult": {
                                "@id": f"urn:ngsi-ld:Property:polderland-result-{i + 1:03d}",
                                "@type": "Property",
                                "hasValue": str(58 - i * 3),
                                "unit": "CEL",
                            },
                            "details": "Core temperature reading, cooling as pile matures." if i > 0 else "Core temperature reading.",
                        }
                    ]
                }
            ],
            "hasNestedOperation": [
                {
                    "@id": f"urn:ngsi-ld:AddRawMaterialOperation:polderland-raw-{i + 1:03d}",
                    "@type": "AddRawMaterialOperation",
                    "type": "raw",
                    "hasStartDatetime": f"{_COMPOST_DATES[i]}T08:30:00Z",
                    "details": f"Added {_COMPOST_MATERIALS[i % len(_COMPOST_MATERIALS)][0].lower()} to the pile.",
                    "hasCompostMaterial": [
                        {
                            "@type": "CompostMaterial",
                            "typeName": _COMPOST_MATERIALS[i % len(_COMPOST_MATERIALS)][0],
                            "quantityValue": {
                                "@type": "QuantitativeValue",
                                "numericValue": str(_COMPOST_MATERIALS[i % len(_COMPOST_MATERIALS)][1]),
                                "unit": "KGM",
                            },
                        }
                    ],
                }
            ],
        }
        for i in range(len(_COMPOST_DATES))
    ]
}


def _vary(data, task_i):
    """Copy a static @graph payload and give it per-task_i identity, so
    concurrent tasks don't all submit byte-identical reports."""
    data = copy.deepcopy(data)
    parcel_slug = _PARCEL_NAMES[task_i % len(_PARCEL_NAMES)].lower().replace(" ", "-")
    for item in data["@graph"]:
        item["@id"] += f"-{task_i:03d}"
        for key in ("operatedOn", "hasAgriParcel"):
            if key in item:
                item[key] = {"@id": f"urn:ngsi-ld:AgriParcel:{parcel_slug}"}
    return data


class ReportingStressTest(BaseStressTestEval):
    REPORT_CALLBACK_TIMEOUT = 120

    _callback_server_started = False
    _callback_server_lock = threading.Lock()

    def __init__(self, controller, logger, setup_id, output_dir, admin_user, admin_pass):
        super().__init__(controller, logger, setup_id, output_dir, admin_user, admin_pass)
        self.health_check_urls = [
            REPORTING_BASE_URL + '/docs',
        ]
        self.NUM_REPORTS = self.num_entries

    def run(self):
        output = super().run()
        self.report_setup()
        output.update(self.run_service_tasks('reporting', self.report_tasks))
        return output

    # --- setup (not measured) ---

    def report_setup(self):
        self._report_ensure_callback_listener()
        self._report_register_and_login()

    def _report_ensure_callback_listener(self):
        with ReportingStressTest._callback_server_lock:
            if ReportingStressTest._callback_server_started:
                return
            server = ThreadingHTTPServer(('0.0.0.0', REPORTING_STRESS_TEST_LISTENER_PORT), _ReportCallbackHandler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            ReportingStressTest._callback_server_started = True
            self.logger.info(f'Callback listener started on port {REPORTING_STRESS_TEST_LISTENER_PORT}')

    def _report_register_and_login(self):
        admin_email = 'admin@admin.com'
        admin_pass = 'Admin1234'
        try:
            response = requests.post(
                f'{REPORTING_BASE_URL}/api/v1/user/register/',
                json={"email": admin_email, "password": admin_pass},
            )
            if response.status_code not in (200, 400):
                self.logger.warning(f'Reporting register returned {response.status_code}: {response.text[:200]}')
        except Exception as e:
            self.logger.warning(f'Reporting register failed: {e}')

        try:
            response = requests.post(
                f'{REPORTING_BASE_URL}/api/v1/login/access-token/',
                data={"username": admin_email, "password": admin_pass},
            )
            response.raise_for_status()
            token = response.json()['access_token']
            self.base_headers['Authorization'] = f'Bearer {token}'
            self.logger.info('Reporting login successful, token updated')
        except Exception as e:
            self.logger.warning(f'Reporting login failed: {e}')

    # --- shared helper (measured tasks below all funnel through this) ---

    def _report_submit_and_wait(self, task_name, post_url, files, data=None, headers=None, params=None):
        start_time = time.perf_counter()

        response = requests.post(post_url, headers=headers, data=data, files=files, params=params)
        if response.status_code != 200:
            self.logger.warning(f'{task_name} returned {response.status_code}: {response.text[:200]}')
            return time.perf_counter() - start_time

        report_id = response.json()['uuid']
        event = threading.Event()
        _ReportCallbackHandler.events[report_id] = event

        try:
            got_callback = event.wait(timeout=self.REPORT_CALLBACK_TIMEOUT)
        finally:
            _ReportCallbackHandler.events.pop(report_id, None)

        if not got_callback:
            self.logger.warning(f'{task_name} {report_id} callback not received after {self.REPORT_CALLBACK_TIMEOUT}s timeout')

        return time.perf_counter() - start_time

    # --- tasks (measured) ---

    def report_tasks(self):
        report_results = {}

        report_results.update(self.report_generate_and_wait_standalone_report(num_reports=self.NUM_REPORTS, rps=self.rps))
        report_results.update(self.report_generate_and_wait_irrigation_report(num_reports=self.NUM_REPORTS, rps=self.rps))
        report_results.update(self.report_generate_and_wait_fertilization_report(num_reports=self.NUM_REPORTS, rps=self.rps))
        report_results.update(self.report_generate_and_wait_pesticides_report(num_reports=self.NUM_REPORTS, rps=self.rps))
        report_results.update(self.report_generate_and_wait_animal_report(num_reports=self.NUM_REPORTS, rps=self.rps))
        report_results.update(self.report_generate_and_wait_compost_report(num_reports=self.NUM_REPORTS, rps=self.rps))

        return report_results

    # --- standalone-observation-report (no auth) ---

    def report_generate_and_wait_standalone_report(self, num_reports, rps):
        return self.multithread_task(
            'generate_and_wait_standalone_report',
            self.task_generate_and_wait_standalone_report, num_reports, rps,
        )

    def task_generate_and_wait_standalone_report(self, task_i):
        parcel_name = _PARCEL_NAMES[task_i % len(_PARCEL_NAMES)]

        post_url = f'{REPORTING_BASE_URL}/api/v1/openagri-report/standalone-observation-report/'
        files = {
            'data': ('observations.json', json.dumps(_OBSERVATIONS), 'application/json'),
        }
        data = {
            'title': f'{parcel_name} Observation Report',
            'from_date': '2026-03-15',
            'to_date': '2026-03-22',
            'parcel_identifier': f'NL-FLD-{task_i:03d}',
            'parcel_address': f'{parcel_name}, Flevoland, Netherlands',
            'parcel_area': '4.5',
            'farm_name': 'Polderland Farms B.V.',
            'farm_municipality': 'Lelystad',
            'farm_administrator': 'Willem de Vries',
            'farm_contact_person': 'Sophie Bakker',
            'farm_vat_id': 'NL123456789B01',
            'farm_description': 'Family-owned arable farm specializing in potatoes and cereals in the Flevoland polder.',
            # parcel_lat/parcel_lng intentionally omitted — skips the
            # satellite image fetch, which needs internet
        }
        return self._report_submit_and_wait('generate_and_wait_standalone_report', post_url, files, data=data)

    # --- irrigation-report (auth) ---

    def report_generate_and_wait_irrigation_report(self, num_reports, rps):
        return self.multithread_task(
            'generate_and_wait_irrigation_report',
            self.task_generate_and_wait_irrigation_report, num_reports, rps,
        )

    def task_generate_and_wait_irrigation_report(self, task_i):
        post_url = f'{REPORTING_BASE_URL}/api/v1/openagri-report/irrigation-report/'
        files = {
            'data': ('irrigation.json', json.dumps(_vary(_IRRIGATION_DATA, task_i)), 'application/json'),
        }
        return self._report_submit_and_wait(
            'generate_and_wait_irrigation_report', post_url, files,
            headers={'Authorization': self.base_headers.get('Authorization', '')},
            params={'from_date': '2026-03-15', 'to_date': '2026-03-24'},
        )

    # --- fertilization-report (auth) ---

    def report_generate_and_wait_fertilization_report(self, num_reports, rps):
        return self.multithread_task(
            'generate_and_wait_fertilization_report',
            self.task_generate_and_wait_fertilization_report, num_reports, rps,
        )

    def task_generate_and_wait_fertilization_report(self, task_i):
        post_url = f'{REPORTING_BASE_URL}/api/v1/openagri-report/fertilization-report/'
        files = {
            'data': ('fertilization.json', json.dumps(_vary(_FERTILIZATION_DATA, task_i)), 'application/json'),
        }
        return self._report_submit_and_wait(
            'generate_and_wait_fertilization_report', post_url, files,
            headers={'Authorization': self.base_headers.get('Authorization', '')},
            params={'from_date': '2026-03-15', 'to_date': '2026-03-24'},
        )

    # --- pesticides-report (auth) ---

    def report_generate_and_wait_pesticides_report(self, num_reports, rps):
        return self.multithread_task(
            'generate_and_wait_pesticides_report',
            self.task_generate_and_wait_pesticides_report, num_reports, rps,
        )

    def task_generate_and_wait_pesticides_report(self, task_i):
        post_url = f'{REPORTING_BASE_URL}/api/v1/openagri-report/pesticides-report/'
        files = {
            'data': ('pesticides.json', json.dumps(_vary(_PESTICIDES_DATA, task_i)), 'application/json'),
        }
        return self._report_submit_and_wait(
            'generate_and_wait_pesticides_report', post_url, files,
            headers={'Authorization': self.base_headers.get('Authorization', '')},
            params={'from_date': '2026-03-15', 'to_date': '2026-03-24'},
        )

    # --- animal-report (auth) ---

    def report_generate_and_wait_animal_report(self, num_reports, rps):
        return self.multithread_task(
            'generate_and_wait_animal_report',
            self.task_generate_and_wait_animal_report, num_reports, rps,
        )

    def task_generate_and_wait_animal_report(self, task_i):
        post_url = f'{REPORTING_BASE_URL}/api/v1/openagri-report/animal-report/'
        files = {
            'data': ('animals.json', json.dumps(_vary(_ANIMAL_DATA, task_i)), 'application/json'),
        }
        return self._report_submit_and_wait(
            'generate_and_wait_animal_report', post_url, files, headers={'Authorization': self.base_headers.get('Authorization', '')}
        )

    # --- compost-report (auth) ---

    def report_generate_and_wait_compost_report(self, num_reports, rps):
        return self.multithread_task(
            'generate_and_wait_compost_report',
            self.task_generate_and_wait_compost_report, num_reports, rps,
        )

    def task_generate_and_wait_compost_report(self, task_i):
        post_url = f'{REPORTING_BASE_URL}/api/v1/openagri-report/compost-report/'
        files = {
            'data': ('compost.json', json.dumps(_vary(_COMPOST_DATA, task_i)), 'application/json'),
        }
        return self._report_submit_and_wait(
            'generate_and_wait_compost_report', post_url, files, headers={'Authorization': self.base_headers.get('Authorization', '')}
        )


evaluator = ReportingStressTest

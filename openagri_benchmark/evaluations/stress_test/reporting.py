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
        pass  # silence default request logging to stderr


_PARCEL_NAMES = [
    "North Polder Field",
    "Zuidpolder Plot",
    "Flevoland Grain Field",
    "Almere Dairy Meadow",
    "Lelystad Potato Field",
]

_RESPONSIBLE_AGENT = "Sophie Bakker, Field Agronomist"

_OBSERVATIONS = [
    {
        "@type": "Observation",
        "phenomenonTime": "2026-03-15T08:15:00Z",
        "hasStartDatetime": "2026-03-15T08:15:00Z",
        "hasEndDatetime": "2026-03-15T08:30:00Z",
        "observedProperty": "temperature",
        "responsibleAgent": _RESPONSIBLE_AGENT,
        "details": "Soil temperature reading at 10cm depth, mid-morning.",
        "hasResult": {"@type": "Property", "hasValue": "11.8", "unit": "CEL"},
    },
    {
        "@type": "Observation",
        "phenomenonTime": "2026-03-15T15:00:00Z",
        "hasStartDatetime": "2026-03-15T15:00:00Z",
        "hasEndDatetime": "2026-03-15T15:10:00Z",
        "observedProperty": "moisture",
        "responsibleAgent": _RESPONSIBLE_AGENT,
        "details": "Soil moisture reading, afternoon check.",
        "hasResult": {"@type": "Property", "hasValue": "22.0", "unit": "P1"},
    },
    {
        "@type": "Observation",
        "phenomenonTime": "2026-03-16T08:15:00Z",
        "hasStartDatetime": "2026-03-16T08:15:00Z",
        "hasEndDatetime": "2026-03-16T08:30:00Z",
        "observedProperty": "temperature",
        "responsibleAgent": _RESPONSIBLE_AGENT,
        "details": "Soil temperature reading at 10cm depth, mid-morning.",
        "hasResult": {"@type": "Property", "hasValue": "12.1", "unit": "CEL"},
    },
    {
        "@type": "Observation",
        "phenomenonTime": "2026-03-16T15:00:00Z",
        "hasStartDatetime": "2026-03-16T15:00:00Z",
        "hasEndDatetime": "2026-03-16T15:10:00Z",
        "observedProperty": "moisture",
        "responsibleAgent": _RESPONSIBLE_AGENT,
        "details": "Soil moisture reading, afternoon check.",
        "hasResult": {"@type": "Property", "hasValue": "20.5", "unit": "P1"},
    },
    {
        "@type": "Observation",
        "phenomenonTime": "2026-03-17T08:15:00Z",
        "hasStartDatetime": "2026-03-17T08:15:00Z",
        "hasEndDatetime": "2026-03-17T08:30:00Z",
        "observedProperty": "temperature",
        "responsibleAgent": _RESPONSIBLE_AGENT,
        "details": "Soil temperature reading at 10cm depth, mid-morning.",
        "hasResult": {"@type": "Property", "hasValue": "13.0", "unit": "CEL"},
    },
    {
        "@type": "Observation",
        "phenomenonTime": "2026-03-17T15:00:00Z",
        "hasStartDatetime": "2026-03-17T15:00:00Z",
        "hasEndDatetime": "2026-03-17T15:10:00Z",
        "observedProperty": "moisture",
        "responsibleAgent": _RESPONSIBLE_AGENT,
        "details": "Soil moisture reading, afternoon check.",
        "hasResult": {"@type": "Property", "hasValue": "18.7", "unit": "P1"},
    },
    {
        "@type": "Observation",
        "phenomenonTime": "2026-03-18T08:15:00Z",
        "hasStartDatetime": "2026-03-18T08:15:00Z",
        "hasEndDatetime": "2026-03-18T08:30:00Z",
        "observedProperty": "temperature",
        "responsibleAgent": _RESPONSIBLE_AGENT,
        "details": "Soil temperature reading at 10cm depth, mid-morning.",
        "hasResult": {"@type": "Property", "hasValue": "13.4", "unit": "CEL"},
    },
    {
        "@type": "Observation",
        "phenomenonTime": "2026-03-18T15:00:00Z",
        "hasStartDatetime": "2026-03-18T15:00:00Z",
        "hasEndDatetime": "2026-03-18T15:10:00Z",
        "observedProperty": "moisture",
        "responsibleAgent": _RESPONSIBLE_AGENT,
        "details": "Soil moisture reading following an irrigation cycle.",
        "hasResult": {"@type": "Property", "hasValue": "24.2", "unit": "P1"},
    },
    {
        "@type": "Observation",
        "phenomenonTime": "2026-03-19T08:15:00Z",
        "hasStartDatetime": "2026-03-19T08:15:00Z",
        "hasEndDatetime": "2026-03-19T08:30:00Z",
        "observedProperty": "temperature",
        "responsibleAgent": _RESPONSIBLE_AGENT,
        "details": "Soil temperature reading at 10cm depth, mid-morning.",
        "hasResult": {"@type": "Property", "hasValue": "14.0", "unit": "CEL"},
    },
    {
        "@type": "Observation",
        "phenomenonTime": "2026-03-19T15:00:00Z",
        "hasStartDatetime": "2026-03-19T15:00:00Z",
        "hasEndDatetime": "2026-03-19T15:10:00Z",
        "observedProperty": "moisture",
        "responsibleAgent": _RESPONSIBLE_AGENT,
        "details": "Soil moisture reading, afternoon check.",
        "hasResult": {"@type": "Property", "hasValue": "21.3", "unit": "P1"},
    },
    {
        "@type": "Observation",
        "phenomenonTime": "2026-03-20T08:15:00Z",
        "hasStartDatetime": "2026-03-20T08:15:00Z",
        "hasEndDatetime": "2026-03-20T08:30:00Z",
        "observedProperty": "temperature",
        "responsibleAgent": _RESPONSIBLE_AGENT,
        "details": "Soil temperature reading at 10cm depth, mid-morning.",
        "hasResult": {"@type": "Property", "hasValue": "14.3", "unit": "CEL"},
    },
    {
        "@type": "Observation",
        "phenomenonTime": "2026-03-20T15:00:00Z",
        "hasStartDatetime": "2026-03-20T15:00:00Z",
        "hasEndDatetime": "2026-03-20T15:10:00Z",
        "observedProperty": "moisture",
        "responsibleAgent": _RESPONSIBLE_AGENT,
        "details": "Soil moisture reading, afternoon check.",
        "hasResult": {"@type": "Property", "hasValue": "19.8", "unit": "P1"},
    },
    {
        "@type": "Observation",
        "phenomenonTime": "2026-03-21T08:15:00Z",
        "hasStartDatetime": "2026-03-21T08:15:00Z",
        "hasEndDatetime": "2026-03-21T08:30:00Z",
        "observedProperty": "temperature",
        "responsibleAgent": _RESPONSIBLE_AGENT,
        "details": "Soil temperature reading at 10cm depth, mid-morning.",
        "hasResult": {"@type": "Property", "hasValue": "14.6", "unit": "CEL"},
    },
    {
        "@type": "Observation",
        "phenomenonTime": "2026-03-21T15:00:00Z",
        "hasStartDatetime": "2026-03-21T15:00:00Z",
        "hasEndDatetime": "2026-03-21T15:10:00Z",
        "observedProperty": "moisture",
        "responsibleAgent": _RESPONSIBLE_AGENT,
        "details": "Soil moisture reading following an irrigation cycle.",
        "hasResult": {"@type": "Property", "hasValue": "23.5", "unit": "P1"},
    },
    {
        "@type": "Observation",
        "phenomenonTime": "2026-03-15T12:00:00Z",
        "hasStartDatetime": "2026-03-15T12:00:00Z",
        "hasEndDatetime": "2026-03-15T12:05:00Z",
        "observedProperty": "humidity",
        "responsibleAgent": _RESPONSIBLE_AGENT,
        "details": "Relative humidity reading, midday.",
        "hasResult": {"@type": "Property", "hasValue": "72", "unit": "%"},
    },
    {
        "@type": "Observation",
        "phenomenonTime": "2026-03-15T18:00:00Z",
        "hasStartDatetime": "2026-03-15T18:00:00Z",
        "hasEndDatetime": "2026-03-15T18:05:00Z",
        "observedProperty": "rainfall",
        "responsibleAgent": _RESPONSIBLE_AGENT,
        "details": "Daily rainfall total recorded at end of day.",
        "hasResult": {"@type": "Property", "hasValue": "0.0", "unit": "MM"},
    },
    {
        "@type": "Observation",
        "phenomenonTime": "2026-03-16T12:00:00Z",
        "hasStartDatetime": "2026-03-16T12:00:00Z",
        "hasEndDatetime": "2026-03-16T12:05:00Z",
        "observedProperty": "humidity",
        "responsibleAgent": _RESPONSIBLE_AGENT,
        "details": "Relative humidity reading, midday.",
        "hasResult": {"@type": "Property", "hasValue": "75", "unit": "%"},
    },
    {
        "@type": "Observation",
        "phenomenonTime": "2026-03-16T18:00:00Z",
        "hasStartDatetime": "2026-03-16T18:00:00Z",
        "hasEndDatetime": "2026-03-16T18:05:00Z",
        "observedProperty": "rainfall",
        "responsibleAgent": _RESPONSIBLE_AGENT,
        "details": "Daily rainfall total recorded at end of day.",
        "hasResult": {"@type": "Property", "hasValue": "2.4", "unit": "MM"},
    },
    {
        "@type": "Observation",
        "phenomenonTime": "2026-03-17T12:00:00Z",
        "hasStartDatetime": "2026-03-17T12:00:00Z",
        "hasEndDatetime": "2026-03-17T12:05:00Z",
        "observedProperty": "humidity",
        "responsibleAgent": _RESPONSIBLE_AGENT,
        "details": "Relative humidity reading, midday.",
        "hasResult": {"@type": "Property", "hasValue": "68", "unit": "%"},
    },
    {
        "@type": "Observation",
        "phenomenonTime": "2026-03-17T18:00:00Z",
        "hasStartDatetime": "2026-03-17T18:00:00Z",
        "hasEndDatetime": "2026-03-17T18:05:00Z",
        "observedProperty": "rainfall",
        "responsibleAgent": _RESPONSIBLE_AGENT,
        "details": "Daily rainfall total recorded at end of day.",
        "hasResult": {"@type": "Property", "hasValue": "0.0", "unit": "MM"},
    },
    {
        "@type": "Observation",
        "phenomenonTime": "2026-03-18T12:00:00Z",
        "hasStartDatetime": "2026-03-18T12:00:00Z",
        "hasEndDatetime": "2026-03-18T12:05:00Z",
        "observedProperty": "humidity",
        "responsibleAgent": _RESPONSIBLE_AGENT,
        "details": "Relative humidity reading, midday.",
        "hasResult": {"@type": "Property", "hasValue": "70", "unit": "%"},
    },
    {
        "@type": "Observation",
        "phenomenonTime": "2026-03-18T18:00:00Z",
        "hasStartDatetime": "2026-03-18T18:00:00Z",
        "hasEndDatetime": "2026-03-18T18:05:00Z",
        "observedProperty": "rainfall",
        "responsibleAgent": _RESPONSIBLE_AGENT,
        "details": "Daily rainfall total recorded at end of day.",
        "hasResult": {"@type": "Property", "hasValue": "0.0", "unit": "MM"},
    },
    {
        "@type": "Observation",
        "phenomenonTime": "2026-03-19T12:00:00Z",
        "hasStartDatetime": "2026-03-19T12:00:00Z",
        "hasEndDatetime": "2026-03-19T12:05:00Z",
        "observedProperty": "humidity",
        "responsibleAgent": _RESPONSIBLE_AGENT,
        "details": "Relative humidity reading, midday.",
        "hasResult": {"@type": "Property", "hasValue": "66", "unit": "%"},
    },
    {
        "@type": "Observation",
        "phenomenonTime": "2026-03-19T18:00:00Z",
        "hasStartDatetime": "2026-03-19T18:00:00Z",
        "hasEndDatetime": "2026-03-19T18:05:00Z",
        "observedProperty": "rainfall",
        "responsibleAgent": _RESPONSIBLE_AGENT,
        "details": "Daily rainfall total recorded at end of day.",
        "hasResult": {"@type": "Property", "hasValue": "1.2", "unit": "MM"},
    },
    {
        "@type": "Observation",
        "phenomenonTime": "2026-03-20T12:00:00Z",
        "hasStartDatetime": "2026-03-20T12:00:00Z",
        "hasEndDatetime": "2026-03-20T12:05:00Z",
        "observedProperty": "humidity",
        "responsibleAgent": _RESPONSIBLE_AGENT,
        "details": "Relative humidity reading, midday.",
        "hasResult": {"@type": "Property", "hasValue": "73", "unit": "%"},
    },
    {
        "@type": "Observation",
        "phenomenonTime": "2026-03-20T18:00:00Z",
        "hasStartDatetime": "2026-03-20T18:00:00Z",
        "hasEndDatetime": "2026-03-20T18:05:00Z",
        "observedProperty": "rainfall",
        "responsibleAgent": _RESPONSIBLE_AGENT,
        "details": "Daily rainfall total recorded at end of day.",
        "hasResult": {"@type": "Property", "hasValue": "3.6", "unit": "MM"},
    },
    {
        "@type": "Observation",
        "phenomenonTime": "2026-03-21T12:00:00Z",
        "hasStartDatetime": "2026-03-21T12:00:00Z",
        "hasEndDatetime": "2026-03-21T12:05:00Z",
        "observedProperty": "humidity",
        "responsibleAgent": _RESPONSIBLE_AGENT,
        "details": "Relative humidity reading, midday.",
        "hasResult": {"@type": "Property", "hasValue": "69", "unit": "%"},
    },
    {
        "@type": "Observation",
        "phenomenonTime": "2026-03-21T18:00:00Z",
        "hasStartDatetime": "2026-03-21T18:00:00Z",
        "hasEndDatetime": "2026-03-21T18:05:00Z",
        "observedProperty": "rainfall",
        "responsibleAgent": _RESPONSIBLE_AGENT,
        "details": "Daily rainfall total recorded at end of day.",
        "hasResult": {"@type": "Property", "hasValue": "0.0", "unit": "MM"},
    },
]


class ReportingStressTest(BaseStressTestEval):
    STANDALONE_REPORT_CALLBACK_TIMEOUT = 120

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

    def _report_ensure_callback_listener(self):
        with ReportingStressTest._callback_server_lock:
            if ReportingStressTest._callback_server_started:
                return
            server = ThreadingHTTPServer(('0.0.0.0', REPORTING_STRESS_TEST_LISTENER_PORT), _ReportCallbackHandler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            ReportingStressTest._callback_server_started = True
            self.logger.info(f'Callback listener started on port {REPORTING_STRESS_TEST_LISTENER_PORT}')

    # --- tasks (measured) ---

    def report_tasks(self):
        report_results = {}

        callback_results = self.report_generate_and_wait_standalone_report(num_reports=self.NUM_REPORTS, rps=self.rps)
        report_results.update(callback_results)

        return report_results

    def report_generate_and_wait_standalone_report(self, num_reports, rps):
        results = self.multithread_task(
            'generate_and_wait_standalone_report',
            self.task_generate_and_wait_standalone_report, num_reports, rps,
        )
        return results

    def task_generate_and_wait_standalone_report(self, task_i):
        start_time = time.perf_counter()

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

        response = requests.post(post_url, data=data, files=files)
        if response.status_code != 200:
            self.logger.warning(f'Generate standalone report returned {response.status_code}: {response.text[:200]}')
            return time.perf_counter() - start_time

        report_id = response.json()['uuid']
        event = threading.Event()
        _ReportCallbackHandler.events[report_id] = event

        try:
            got_callback = event.wait(timeout=self.STANDALONE_REPORT_CALLBACK_TIMEOUT)
        finally:
            _ReportCallbackHandler.events.pop(report_id, None)

        if not got_callback:
            self.logger.warning(f'Report {report_id} callback not received after {self.STANDALONE_REPORT_CALLBACK_TIMEOUT}s timeout')

        return time.perf_counter() - start_time


evaluator = ReportingStressTest

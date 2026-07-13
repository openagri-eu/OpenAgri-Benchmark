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

from openagri_benchmark.data.reporting_data import (
    ANIMAL_DATA,
    COMPOST_DATA,
    FERTILIZATION_DATA,
    IRRIGATION_DATA,
    OBSERVATIONS,
    PARCEL_NAMES,
    PESTICIDES_DATA,
    vary,
)


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
        # Theoretical race: the service could finish the PDF and call back
        # before we register the Event below, so the callback would find
        # nothing in `events` and get dropped, forcing a full timeout wait.
        # Low probability in practice — PDF generation always takes far
        # longer than these few lines of Python.
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
        parcel_name = PARCEL_NAMES[task_i % len(PARCEL_NAMES)]

        post_url = f'{REPORTING_BASE_URL}/api/v1/openagri-report/standalone-observation-report/'
        files = {
            'data': ('observations.json', json.dumps(OBSERVATIONS), 'application/json'),
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
            'data': ('irrigation.json', json.dumps(vary(IRRIGATION_DATA, task_i)), 'application/json'),
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
            'data': ('fertilization.json', json.dumps(vary(FERTILIZATION_DATA, task_i)), 'application/json'),
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
            'data': ('pesticides.json', json.dumps(vary(PESTICIDES_DATA, task_i)), 'application/json'),
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
            'data': ('animals.json', json.dumps(vary(ANIMAL_DATA, task_i)), 'application/json'),
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
            'data': ('compost.json', json.dumps(vary(COMPOST_DATA, task_i)), 'application/json'),
        }
        return self._report_submit_and_wait(
            'generate_and_wait_compost_report', post_url, files, headers={'Authorization': self.base_headers.get('Authorization', '')}
        )


evaluator = ReportingStressTest

import csv
import os
import time
import datetime

import requests
import threading


from openagri_benchmark.conf import (
    PND_BASE_URL,
    PND_CSV_PATH,
)


from .base import BaseStressTestEval


_PARCEL_NAMES = [
    "Vojvodina North Field",
    "Bačka Central Plot",
    "Srem East Vineyard",
    "Banat West Orchard",
    "Danube Plain Plot",
]

_PEST_MODEL_NAMES = [
    "Grain Aphid",
    "Bird Cherry-Oat Aphid",
    "Russian Wheat Aphid",
    "Hessian Fly",
    "Wheat Stem Sawfly",
    "Septoria Tritici Blotch",
    "Fusarium Head Blight",
    "Tan Spot",
    "Stripe Rust",
    "Leaf Rust",
]

_DISEASE_DATA = [
    {"name": "Powdery Mildew",       "eppo_code": "ERYSGT", "base_gdd": 5,  "description": "Fungal disease of cereals caused by Blumeria graminis"},
    {"name": "Septoria Leaf Blotch", "eppo_code": "SEPTTR", "base_gdd": 7,  "description": "Caused by Zymoseptoria tritici on wheat"},
    {"name": "Stripe Rust",          "eppo_code": "PUCCST", "base_gdd": 3,  "description": "Caused by Puccinia striiformis f.sp. tritici"},
    {"name": "Leaf Rust",            "eppo_code": "PUCCRE", "base_gdd": 8,  "description": "Caused by Puccinia triticina on wheat"},
    {"name": "Fusarium Head Blight", "eppo_code": "FUSACU", "base_gdd": 10, "description": "Caused by Fusarium culmorum and F. graminearum"},
    {"name": "Tan Spot",             "eppo_code": "PYRNTR", "base_gdd": 6,  "description": "Caused by Pyrenophora tritici-repentis"},
    {"name": "Net Blotch",           "eppo_code": "PYRNTE", "base_gdd": 4,  "description": "Caused by Drechslera teres on barley"},
    {"name": "Scald",                "eppo_code": "RHYNSE", "base_gdd": 5,  "description": "Caused by Rhynchosporium secalis on barley"},
    {"name": "Eyespot",              "eppo_code": "OCULAC", "base_gdd": 2,  "description": "Caused by Oculimacula yallundae on cereals"},
    {"name": "Stem Rust",            "eppo_code": "PUCCGR", "base_gdd": 9,  "description": "Caused by Puccinia graminis f.sp. tritici"},
]

_THREAT_MODEL_DATA = [
    {"scientific_name": "Blumeria graminis f.sp. tritici",    "common_name": "Wheat Powdery Mildew"},
    {"scientific_name": "Zymoseptoria tritici",               "common_name": "Septoria Leaf Blotch"},
    {"scientific_name": "Puccinia striiformis f.sp. tritici", "common_name": "Wheat Stripe Rust"},
    {"scientific_name": "Fusarium graminearum",               "common_name": "Fusarium Head Blight"},
    {"scientific_name": "Pyrenophora tritici-repentis",       "common_name": "Tan Spot"},
]


class PNDStressTest(BaseStressTestEval):
    PND_GDD_FROM_DATE = '2026-03-20'
    PND_GDD_TO_DATE = '2026-06-17'

    def __init__(self, controller, logger, setup_id, output_dir, admin_user, admin_pass):
        super().__init__(controller, logger, setup_id, output_dir, admin_user, admin_pass)
        self.health_check_urls = [
            PND_BASE_URL + '/docs',
        ]
        self.NUM_DISEASE = self.num_entries
        self.NUM_PEST_MODELS = self.num_entries
        # half of number of entries, but awlways at least one
        self.NUM_THREAT_MODELS = max(1, int(self.num_entries / 2))
        self.NUM_PARCELS = max(1, int(self.num_entries / 2))

    def run(self):
        output = super().run()
        self.pnd_setup()
        output.update(self.run_service_tasks('pestanddisease', self.pnd_tasks))
        return output

    def _load_pnd_csv(self):
        if not os.path.exists(PND_CSV_PATH):
            self.logger.warning(f'PDM CSV not found: {PND_CSV_PATH}')
            return []
        rows = []
        with open(PND_CSV_PATH) as f:
            for row in csv.DictReader(f):
                for k, v in row.items():
                    if k not in ('date', 'time', 'wind_direction'):
                        try:
                            row[k] = float(v)
                        except (ValueError, TypeError):
                            pass
                rows.append(row)
        return rows

    # --- setup (not measured) ---

    def _pnd_register_and_login(self):
        admin_email = 'admin@admin.com'
        admin_pass = 'Admin1234'
        try:
            response = requests.post(
                f'{PND_BASE_URL}/api/v1/user/register/',
                json={"email": admin_email, "password": admin_pass},
            )
            if response.status_code not in (200, 409):
                self.logger.warning(f'PDM register returned {response.status_code}: {response.text[:200]}')
        except Exception as e:
            self.logger.warning(f'PDM register failed: {e}')

        try:
            response = requests.post(
                f'{PND_BASE_URL}/api/v1/login/access-token/',
                data={"username": admin_email, "password": admin_pass},
            )
            response.raise_for_status()
            token = response.json()['access_token']
            self.base_headers['Authorization'] = f'Bearer {token}'
            self.logger.info('PDM login successful, token updated')
        except Exception as e:
            self.logger.warning(f'PDM login failed: {e}')

    def pnd_setup(self):
        self._pnd_register_and_login()
        self.logger.info(f'PND setup: creating {self.NUM_PARCELS} parcels — POST will return 500 (weather fetch offline), parcels still saved to DB')
        self.pnd_register_parcels(num_parcels=self.NUM_PARCELS, rps=self.rps)
        self.pnd_parcel_ids = self._pnd_get_parcel_ids(num_parcels=self.NUM_PARCELS)
        found = len([pid for pid in self.pnd_parcel_ids if pid is not None])
        self.logger.info(f'PND setup done: {found}/{self.NUM_PARCELS} parcels ready')

        unit_ids = self._pnd_get_unit_ids()
        operator_ids = self._pnd_get_operator_ids()
        self.pnd_pest_model_ids = self._pnd_create_pest_models_with_rules(
            num=self.NUM_PEST_MODELS, unit_ids=unit_ids, operator_ids=operator_ids
        )
        self.logger.info(f'PND setup: {len(self.pnd_pest_model_ids)}/{self.NUM_PEST_MODELS} pest models with rules ready')

        crop_id = self._pnd_create_crop()
        self.pnd_threat_model_ids = self._pnd_create_threat_models(num=self.NUM_THREAT_MODELS, crop_id=crop_id)
        self.logger.info(f'PND setup: {len(self.pnd_threat_model_ids)}/{self.NUM_THREAT_MODELS} threat models ready')

    def _pnd_get_unit_ids(self):
        try:
            response = requests.get(f'{PND_BASE_URL}/api/v1/unit/', headers=self.base_headers.copy())
            response.raise_for_status()
            units = response.json().get('units', [])
            return {u['name']: u['id'] for u in units}
        except Exception as e:
            self.logger.warning(f'GET /unit/ failed: {e}')
            return {}

    def _pnd_get_operator_ids(self):
        try:
            response = requests.get(f'{PND_BASE_URL}/api/v1/operator/', headers=self.base_headers.copy())
            response.raise_for_status()
            operators = response.json().get('operators', [])
            return {o['symbol']: o['id'] for o in operators}
        except Exception as e:
            self.logger.warning(f'GET /operator/ failed: {e}')
            return {}

    def _pnd_create_pest_models_with_rules(self, num, unit_ids, operator_ids):
        hum_id = unit_ids.get('atmospheric_relative_humidity')
        temp_id = unit_ids.get('atmospheric_temperature')
        gt_id = operator_ids.get('>')

        has_rule_ids = all([hum_id, temp_id, gt_id])
        if not has_rule_ids:
            self.logger.warning(f'Missing unit/operator IDs for rules (hum={hum_id}, temp={temp_id}, gt={gt_id}), pest models will have no rules')
        pest_model_ids = []
        for i in range(num):
            try:
                response = requests.post(
                    f'{PND_BASE_URL}/api/v1/pest-model/',
                    json={
                        "name": _PEST_MODEL_NAMES[i % len(_PEST_MODEL_NAMES)],
                        "description": f"Pest model for {_PEST_MODEL_NAMES[i % len(_PEST_MODEL_NAMES)]}",
                        "geo_areas_of_application": None,
                        "cultivations": [],
                    },
                    headers=self.base_headers.copy()
                )
                response.raise_for_status()
                pm_id = str(response.json()['id'])
                pest_model_ids.append(pm_id)

                if has_rule_ids:
                    self._pnd_create_rules_for_pest_model(pm_id, hum_id, temp_id, gt_id)
            except Exception as e:
                self.logger.warning(f'Failed to create pest model {i}: {e}')

        return pest_model_ids

    def _pnd_create_rules_for_pest_model(self, pest_model_id, hum_id, temp_id, gt_id):
        rules = [
            {
                "name": "Moderate risk",
                "probability_value": "moderate",
                "pest_model_id": pest_model_id,
                "conditions": [
                    {"unit_id": hum_id, "operator_id": gt_id, "value": 60.0},
                    {"unit_id": temp_id, "operator_id": gt_id, "value": 15.0},
                ],
            },
            {
                "name": "High risk",
                "probability_value": "high",
                "pest_model_id": pest_model_id,
                "conditions": [
                    {"unit_id": hum_id, "operator_id": gt_id, "value": 80.0},
                    {"unit_id": temp_id, "operator_id": gt_id, "value": 20.0},
                ],
            },
        ]
        for rule in rules:
            try:
                response = requests.post(
                    f'{PND_BASE_URL}/api/v1/rule/',
                    json=rule,
                    headers=self.base_headers.copy()
                )
                response.raise_for_status()
            except Exception as e:
                self.logger.warning(f'Failed to create rule for pest model {pest_model_id}: {e}')

    def pnd_register_parcels(self, num_parcels, rps):
        stagger_interval = 1 / rps
        threads = []
        for i in range(num_parcels):
            thread = threading.Timer(
                i * stagger_interval,
                self.task_register_parcel,
                args=(i,)
            )
            thread.daemon = False
            thread.start()
            threads.append(thread)
        for thread in threads:
            thread.join()

    def task_register_parcel(self, parcel_i):
        url = f'{PND_BASE_URL}/api/v1/parcel/'
        data = {
            "name": _PARCEL_NAMES[parcel_i % len(_PARCEL_NAMES)],
            "latitude": round(44.8 + parcel_i * 0.01, 4),
            "longitude": round(20.4 + parcel_i * 0.01, 4),
        }
        requests.post(url, json=data, headers=self.base_headers.copy())

    def _pnd_get_parcel_ids(self, num_parcels):
        try:
            response = requests.get(f'{PND_BASE_URL}/api/v1/parcel/', headers=self.base_headers.copy())
            response.raise_for_status()
            parcels = response.json()['elements']
            name_to_id = {p['name']: p['id'] for p in parcels if 'name' in p and 'id' in p}
            parcel_ids = []
            for i in range(num_parcels):
                name = _PARCEL_NAMES[i % len(_PARCEL_NAMES)]
                pid = name_to_id.get(name)
                if pid is None:
                    self.logger.warning(f'Parcel "{name}" not found after creation')
                parcel_ids.append(pid)
            return parcel_ids
        except Exception as e:
            self.logger.warning(f'GET /parcel/ failed: {e}')
            return []

    def _pnd_create_crop(self):
        try:
            response = requests.post(
                f'{PND_BASE_URL}/api/v1/crop/',
                json={"name": "Winter Wheat", "description": "Triticum aestivum"},
                headers=self.base_headers.copy()
            )
            response.raise_for_status()
            return str(response.json()['id'])
        except Exception as e:
            self.logger.warning(f'Failed to create crop: {e}')
            return None

    def _pnd_create_threat_models(self, num, crop_id):
        if not crop_id:
            self.logger.warning('No crop_id — skipping threat model creation')
            return []
        threat_model_ids = []
        for i in range(num):
            try:
                response = requests.post(
                    f'{PND_BASE_URL}/api/v1/threat-model/',
                    json={
                        "scientific_name": _THREAT_MODEL_DATA[i % len(_THREAT_MODEL_DATA)]["scientific_name"],
                        "common_name": _THREAT_MODEL_DATA[i % len(_THREAT_MODEL_DATA)]["common_name"],
                        "crop_id": crop_id,
                        "definition": {
                            "bio_params": {
                                "t_base": 5.0,
                                "t_lethal_min": -5.0,
                                "t_lethal_max": 35.0,
                                "t_optimal_min": 15.0,
                                "t_optimal_max": 22.0,
                                "min_streak": 3,
                                "min_wetness_hours_critical": 6.0,
                                "min_wetness_hours_high": 4.0,
                            },
                            "fuzzy_rules": [
                                {"hum_lo": 70.0, "hum_hi": 100.0, "temp_lo": 10.0, "temp_hi": 25.0, "rain_min": 0.0, "risk_level": "high"},
                                {"hum_lo": 50.0, "hum_hi": 70.0,  "temp_lo": 10.0, "temp_hi": 25.0, "rain_min": 0.0, "risk_level": "moderate"},
                            ],
                        },
                    },
                    headers=self.base_headers.copy()
                )
                response.raise_for_status()
                threat_model_ids.append(str(response.json()['id']))
            except Exception as e:
                self.logger.warning(f'Failed to create threat model {i}: {e}')
        return threat_model_ids

    # --- tasks (measured) ---

    def pnd_tasks(self):
        start_timestamp = datetime.datetime.now().isoformat()
        pnd_results = {}

        reg_disease_results = self.pnd_register_disease(num_disease=self.NUM_DISEASE, rps=self.rps)
        pnd_results.update(reg_disease_results)

        list_disease_results = self.pnd_list_diseases(count=self.NUM_DISEASE, rps=self.rps)
        pnd_results.update(list_disease_results)

        parcel_ids = [pid for pid in self.pnd_parcel_ids if pid is not None]
        if parcel_ids:
            upload_results = self.pnd_upload_data(parcel_ids=parcel_ids, rps=self.rps)
            pnd_results.update(upload_results)

        if parcel_ids:
            get_data_results = self.pnd_get_parcel_data(parcel_ids=parcel_ids, rps=self.rps)
            pnd_results.update(get_data_results)

        disease_id = next((d for d in pnd_results.get('disease_ids', []) if d is not None), None)
        if parcel_ids and disease_id:
            gdd_results = self.pnd_calculate_gdd(parcel_ids=parcel_ids, disease_id=disease_id, rps=self.rps)
            pnd_results.update(gdd_results)

        pest_model_id = next((p for p in getattr(self, 'pnd_pest_model_ids', []) if p is not None), None)
        if parcel_ids and pest_model_id:
            risk_index_results = self.pnd_calculate_risk_index(parcel_ids=parcel_ids, pest_model_id=pest_model_id, rps=self.rps)
            pnd_results.update(risk_index_results)

        threat_model_id = next((t for t in getattr(self, 'pnd_threat_model_ids', []) if t is not None), None)
        if parcel_ids and threat_model_id:
            fuzzy_results = self.pnd_fuzzy_risk_calculate(parcel_ids=parcel_ids, threat_model_id=threat_model_id, rps=self.rps)
            pnd_results.update(fuzzy_results)

        end_timestamp = datetime.datetime.now().isoformat()
        pnd_results.update({
            'start_timestamp': start_timestamp,
            'end_timestamp': end_timestamp,
        })
        return pnd_results

    def pnd_register_disease(self, num_disease, rps):
        stagger_interval = 1 / rps
        disease_ids = [None] * num_disease
        disease_request_times = [None] * num_disease

        start_timestamp = datetime.datetime.now().isoformat()
        threads = []
        for i in range(num_disease):
            thread = threading.Timer(
                i * stagger_interval,
                self.pnd_register_disease_worker,
                args=(i, disease_ids, disease_request_times)
            )
            thread.daemon = False
            thread.start()
            threads.append(thread)

        for thread in threads:
            thread.join()
        end_timestamp = datetime.datetime.now().isoformat()


        task_name = 'register_disease'
        result = self._task_base_result_dict(task_name, start_timestamp, end_timestamp, disease_request_times)
        result.update({
            'disease_ids': disease_ids,
        })
        return result

    def pnd_register_disease_worker(self, index, entry_ids, entry_request_times):
        "running each request on a separated thread, storing result pointer args"
        self.logger.debug(f'Registering disease {index}')
        elapsed_time, disease_id = self.task_register_disease(index)
        entry_ids[index] = disease_id
        entry_request_times[index] = elapsed_time

    def task_register_disease(self, disease_i):
        url = f'{PND_BASE_URL}/api/v1/disease/'
        data = {
            "name": _DISEASE_DATA[disease_i % len(_DISEASE_DATA)]["name"],
            "eppo_code": _DISEASE_DATA[disease_i % len(_DISEASE_DATA)]["eppo_code"],
            "base_gdd": _DISEASE_DATA[disease_i % len(_DISEASE_DATA)]["base_gdd"],
            "description": _DISEASE_DATA[disease_i % len(_DISEASE_DATA)]["description"],
            "gdd_points": [
            {"start": 0,   "end": 100, "descriptor": "Germination"},
            {"start": 100, "end": 300, "descriptor": "Growth"},
            {"start": 300, "end": 600, "descriptor": "Sporulation"}
            ]
        }
        headers = self.base_headers.copy()

        start_time = time.perf_counter()
        response = requests.post(url, json=data, headers=headers)
        elapsed_time = time.perf_counter() - start_time

        if response.status_code == 200:
            return elapsed_time, response.json()['id']
        self.logger.warning(f'Register disease returned {response.status_code}: {response.text[:200]}')
        return elapsed_time, None

    def pnd_list_diseases(self, count, rps):
        stagger_interval = 1 / rps
        list_disease_request_times = [None] * count

        start_timestamp = datetime.datetime.now().isoformat()
        threads = []
        for i in range(count):
            thread = threading.Timer(
                i * stagger_interval,
                self.pnd_list_diseases_worker,
                args=(i, list_disease_request_times)
            )
            thread.daemon = False
            thread.start()
            threads.append(thread)

        for thread in threads:
            thread.join()
        end_timestamp = datetime.datetime.now().isoformat()

        task_name = 'list_disease'
        result = self._task_base_result_dict(task_name, start_timestamp, end_timestamp, list_disease_request_times)
        return result

    def pnd_list_diseases_worker(self, index, request_times):
        self.logger.debug(f'Listing diseases ({index})')
        elapsed_time = self.task_list_diseases()
        request_times[index] = elapsed_time

    def task_list_diseases(self):
        url = f'{PND_BASE_URL}/api/v1/disease/'
        headers = self.base_headers.copy()

        start_time = time.perf_counter()
        response = requests.get(url, headers=headers)
        elapsed_time = time.perf_counter() - start_time

        if response.status_code != 200:
            self.logger.warning(f'List diseases returned {response.status_code}: {response.text[:200]}')
        return elapsed_time

    def pnd_upload_data(self, parcel_ids, rps):
        data_rows = self._load_pnd_csv()
        if not data_rows:
            self.logger.warning('No CSV data loaded, skipping data upload')
            return {}

        stagger_interval = 1 / rps
        upload_request_times = [None] * len(parcel_ids)

        start_timestamp = datetime.datetime.now().isoformat()
        threads = []
        for i, parcel_id in enumerate(parcel_ids):
            thread = threading.Timer(
                i * stagger_interval,
                self.pnd_upload_data_worker,
                args=(i, parcel_id, data_rows, upload_request_times)
            )
            thread.daemon = False
            thread.start()
            threads.append(thread)

        for thread in threads:
            thread.join()
        end_timestamp = datetime.datetime.now().isoformat()

        task_name = 'upload_data'
        result = self._task_base_result_dict(task_name, start_timestamp, end_timestamp, upload_request_times)
        result.update({
            f'{task_name}_parcel_ids': parcel_ids,
        })
        return result

    def pnd_upload_data_worker(self, index, parcel_id, data_rows, request_times):
        "running each request on a separated thread, storing result pointer args"
        self.logger.debug(f'Uploading data for parcel {parcel_id}')
        elapsed_time = self.task_upload_data(parcel_id, data_rows)
        request_times[index] = elapsed_time

    def task_upload_data(self, parcel_id, data_rows):
        url = f'{PND_BASE_URL}/api/v1/data/{parcel_id}/'
        headers = self.base_headers.copy()

        start_time = time.perf_counter()
        response = requests.post(url, json=data_rows, headers=headers)
        elapsed_time = time.perf_counter() - start_time

        if response.status_code != 200:
            self.logger.warning(f'Data upload for parcel {parcel_id} returned {response.status_code}: {response.text[:200]}')
        return elapsed_time

    def pnd_get_parcel_data(self, parcel_ids, rps):
        stagger_interval = 1 / rps
        get_data_request_times = [None] * len(parcel_ids)

        start_timestamp = datetime.datetime.now().isoformat()
        threads = []
        for i, parcel_id in enumerate(parcel_ids):
            thread = threading.Timer(
                i * stagger_interval,
                self.pnd_get_parcel_data_worker,
                args=(i, parcel_id, get_data_request_times)
            )
            thread.daemon = False
            thread.start()
            threads.append(thread)

        for thread in threads:
            thread.join()
        end_timestamp = datetime.datetime.now().isoformat()


        task_name = 'get_parcel_data'
        result = self._task_base_result_dict(task_name, start_timestamp, end_timestamp, get_data_request_times)
        result.update({
            f'{task_name}_parcel_ids': parcel_ids,
        })
        return result

    def pnd_get_parcel_data_worker(self, index, parcel_id, request_times):
        self.logger.debug(f'Getting data for parcel {parcel_id}')
        elapsed_time = self.task_get_parcel_data(parcel_id)
        request_times[index] = elapsed_time

    def task_get_parcel_data(self, parcel_id):
        url = (
            f'{PND_BASE_URL}/api/v1/data'
            f'/parcel/{parcel_id}'
            f'/from/{self.PND_GDD_FROM_DATE}'
            f'/to/{self.PND_GDD_TO_DATE}/'
        )
        headers = self.base_headers.copy()

        start_time = time.perf_counter()
        response = requests.get(url, headers=headers)
        elapsed_time = time.perf_counter() - start_time

        if response.status_code != 200:
            self.logger.warning(f'Get parcel data for {parcel_id} returned {response.status_code}: {response.text[:200]}')
        return elapsed_time

    def pnd_calculate_gdd(self, parcel_ids, disease_id, rps):
        stagger_interval = 1 / rps
        gdd_request_times = [None] * len(parcel_ids)

        start_timestamp = datetime.datetime.now().isoformat()
        threads = []
        for i, parcel_id in enumerate(parcel_ids):
            thread = threading.Timer(
                i * stagger_interval,
                self.pnd_calculate_gdd_worker,
                args=(i, parcel_id, disease_id, gdd_request_times)
            )
            thread.daemon = False
            thread.start()
            threads.append(thread)

        for thread in threads:
            thread.join()
        end_timestamp = datetime.datetime.now().isoformat()

        task_name = 'calculate_gdd'
        result = self._task_base_result_dict(task_name, start_timestamp, end_timestamp, gdd_request_times)
        result.update({
            f'{task_name}_parcel_ids': parcel_ids,
        })
        return result

    def pnd_calculate_gdd_worker(self, index, parcel_id, disease_id, request_times):
        self.logger.debug(f'Calculating GDD for parcel {parcel_id}')
        elapsed_time = self.task_calculate_gdd(parcel_id, disease_id)
        request_times[index] = elapsed_time

    def task_calculate_gdd(self, parcel_id, disease_id):
        url = (
            f'{PND_BASE_URL}/api/v1/tool/calculate-gdd'
            f'/parcel/{parcel_id}'
            f'/model/{disease_id}'
            f'/verbose/{self.PND_GDD_FROM_DATE}'
            f'/from/{self.PND_GDD_TO_DATE}'
            f'/to/'
        )
        headers = self.base_headers.copy()

        start_time = time.perf_counter()
        response = requests.get(url, headers=headers)
        elapsed_time = time.perf_counter() - start_time

        if response.status_code != 200:
            self.logger.warning(f'GDD calculation for parcel {parcel_id} returned {response.status_code}: {response.text[:200]}')
        return elapsed_time

    def pnd_calculate_risk_index(self, parcel_ids, pest_model_id, rps):
        stagger_interval = 1 / rps
        risk_index_request_times = [None] * len(parcel_ids)

        start_timestamp = datetime.datetime.now().isoformat()
        threads = []
        for i, parcel_id in enumerate(parcel_ids):
            thread = threading.Timer(
                i * stagger_interval,
                self.pnd_calculate_risk_index_worker,
                args=(i, parcel_id, pest_model_id, risk_index_request_times)
            )
            thread.daemon = False
            thread.start()
            threads.append(thread)

        for thread in threads:
            thread.join()
        end_timestamp = datetime.datetime.now().isoformat()

        task_name = 'calculate_risk'
        result = self._task_base_result_dict(task_name, start_timestamp, end_timestamp, risk_index_request_times)
        result.update({
            f'{task_name}_parcel_ids': parcel_ids,
        })
        return result

    def pnd_calculate_risk_index_worker(self, index, parcel_id, pest_model_id, request_times):
        self.logger.debug(f'Calculating risk index for parcel {parcel_id}')
        elapsed_time = self.task_calculate_risk_index(parcel_id, pest_model_id)
        request_times[index] = elapsed_time

    def task_calculate_risk_index(self, parcel_id, pest_model_id):
        url = (
            f'{PND_BASE_URL}/api/v1/tool/calculate-risk-index'
            f'/weather/{parcel_id}'
            f'/model/{pest_model_id}'
            f'/verbose/{self.PND_GDD_FROM_DATE}'
            f'/from/{self.PND_GDD_TO_DATE}'
            f'/to/'
        )
        headers = self.base_headers.copy()

        start_time = time.perf_counter()
        response = requests.get(url, headers=headers)
        elapsed_time = time.perf_counter() - start_time

        if response.status_code != 200:
            self.logger.warning(f'Risk index calculation for parcel {parcel_id} returned {response.status_code}: {response.text[:200]}')
        return elapsed_time

    def pnd_fuzzy_risk_calculate(self, parcel_ids, threat_model_id, rps):
        stagger_interval = 1 / rps
        fuzzy_risk_request_times = [None] * len(parcel_ids)

        start_timestamp = datetime.datetime.now().isoformat()
        threads = []
        for i, parcel_id in enumerate(parcel_ids):
            thread = threading.Timer(
                i * stagger_interval,
                self.pnd_fuzzy_risk_calculate_worker,
                args=(i, parcel_id, threat_model_id, fuzzy_risk_request_times)
            )
            thread.daemon = False
            thread.start()
            threads.append(thread)

        for thread in threads:
            thread.join()
        end_timestamp = datetime.datetime.now().isoformat()

        task_name = 'fuzzy_risk_calculate'
        result = self._task_base_result_dict(task_name, start_timestamp, end_timestamp, fuzzy_risk_request_times)
        result.update({
            f'{task_name}_parcel_ids': parcel_ids,
        })
        return result

    def pnd_fuzzy_risk_calculate_worker(self, index, parcel_id, threat_model_id, request_times):
        self.logger.debug(f'Calculating fuzzy risk for parcel {parcel_id}')
        elapsed_time = self.task_fuzzy_risk_calculate(parcel_id, threat_model_id)
        request_times[index] = elapsed_time

    def task_fuzzy_risk_calculate(self, parcel_id, threat_model_id):
        url = f'{PND_BASE_URL}/api/v1/fuzzy-risk/calculate/'
        payload = {
            "parcel_id": parcel_id,
            "from_date": self.PND_GDD_FROM_DATE,
            "to_date": self.PND_GDD_TO_DATE,
            "threat_model_ids": [threat_model_id],
        }
        headers = self.base_headers.copy()

        start_time = time.perf_counter()
        response = requests.post(url, json=payload, headers=headers)
        elapsed_time = time.perf_counter() - start_time

        if response.status_code != 200:
            self.logger.warning(f'Fuzzy risk calculate for parcel {parcel_id} returned {response.status_code}: {response.text[:200]}')
        return elapsed_time

evaluator = PNDStressTest

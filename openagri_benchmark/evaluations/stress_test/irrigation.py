import csv
import os
import time

import requests


from openagri_benchmark.conf import (
    IRR_BASE_URL,
    IRR_CSV_PATH,
)


from .base import BaseStressTestEval


class IRRStressTest(BaseStressTestEval):
    def __init__(self, controller, logger, setup_id, output_dir, admin_user, admin_pass):
        super().__init__(controller, logger, setup_id, output_dir, admin_user, admin_pass)
        self.health_check_urls = [
            IRR_BASE_URL + '/docs',
        ]
        self.NUM_UPLOADS = 5

    def run(self):
        output = super().run()
        self.irr_setup()
        output.update(self.run_service_tasks('irrigation', self.irr_tasks))
        return output

    def _load_irr_csv(self):
        if not os.path.exists(IRR_CSV_PATH):
            self.logger.warning(f'Irrigation CSV not found: {IRR_CSV_PATH}')
            return []
        rows = []
        with open(IRR_CSV_PATH) as f:
            for row in csv.DictReader(f):
                for k, v in row.items():
                    if k != 'date':
                        try:
                            row[k] = float(v)
                        except (ValueError, TypeError):
                            pass
                row['date'] = row['date'].replace('.000Z', '')
                rows.append(row)
        return rows

    # --- setup (not measured) ---

    def _irr_register_and_login(self):
        admin_email = 'admin@admin.com'
        admin_pass = 'Admin1234'
        try:
            response = requests.post(
                f'{IRR_BASE_URL}/api/v1/user/register/',
                json={"email": admin_email, "password": admin_pass},
            )
            if response.status_code not in (200, 400):
                self.logger.warning(f'IRR register returned {response.status_code}: {response.text[:200]}')
        except Exception as e:
            self.logger.warning(f'IRR register failed: {e}')

        try:
            response = requests.post(
                f'{IRR_BASE_URL}/api/v1/login/access-token/',
                data={"username": admin_email, "password": admin_pass},
            )
            response.raise_for_status()
            token = response.json()['access_token']
            self.base_headers['Authorization'] = f'Bearer {token}'
            self.logger.info('IRR login successful, token updated')
        except Exception as e:
            self.logger.warning(f'IRR login failed: {e}')

    def irr_setup(self):
        self._irr_register_and_login()

    # --- tasks (measured) ---

    def irr_tasks(self):
        irr_results = {}

        upload_results, dataset_ids = self.irr_upload_data(num_uploads=self.NUM_UPLOADS, rps=self.rps)
        irr_results.update(upload_results)

        list_results = self.irr_list_datasets(count=self.NUM_UPLOADS, rps=self.rps)
        irr_results.update(list_results)

        dataset_ids = [d for d in dataset_ids if d is not None]
        if dataset_ids:
            get_results = self.irr_get_datasets(dataset_ids=dataset_ids, rps=self.rps)
            irr_results.update(get_results)

            analysis_results = self.irr_analyse_datasets(dataset_ids=dataset_ids, rps=self.rps)
            irr_results.update(analysis_results)

            datapoints_results = self.irr_get_irrigation_datapoints(dataset_ids=dataset_ids, rps=self.rps)
            irr_results.update(datapoints_results)

        return irr_results

    def irr_upload_data(self, num_uploads, rps):
        data_rows = self._load_irr_csv()
        if not data_rows:
            self.logger.warning('No CSV data loaded, skipping data upload')
            return {}, [None] * num_uploads

        dataset_ids = [None] * num_uploads

        results = self.multithread_task(
            'upload_data',
            self.task_upload_data, num_uploads, rps,
            dataset_ids=dataset_ids,
            data_rows=data_rows
        )

        return results, dataset_ids

    def task_upload_data(self, task_i, dataset_ids, data_rows):
        url = f'{IRR_BASE_URL}/api/v1/dataset/'
        dataset_id = f'stress_dataset_{task_i}'
        rows = [{'dataset_id': dataset_id, **row} for row in data_rows]
        headers = self.base_headers.copy()

        start_time = time.perf_counter()
        response = requests.post(url, json=rows, headers=headers)
        elapsed_time = time.perf_counter() - start_time

        if response.status_code == 200:
            dataset_ids[task_i] = dataset_id
            return elapsed_time
        self.logger.warning(f'Data upload returned {response.status_code}: {response.text[:200]}')
        return elapsed_time

    def irr_list_datasets(self, count, rps):
        results = self.multithread_task(
            'list_datasets',
            self.task_list_datasets, count, rps
        )
        return results

    def task_list_datasets(self, task_i):
        url = f'{IRR_BASE_URL}/api/v1/dataset/'
        headers = self.base_headers.copy()

        start_time = time.perf_counter()
        response = requests.get(url, headers=headers)
        elapsed_time = time.perf_counter() - start_time

        if response.status_code != 200:
            self.logger.warning(f'List datasets returned {response.status_code}: {response.text[:200]}')
        return elapsed_time

    def irr_get_datasets(self, dataset_ids, rps):
        num_operations = len(dataset_ids)
        results = self.multithread_task(
            'get_dataset',
            self.task_get_dataset, num_operations, rps,
            dataset_ids=dataset_ids
        )
        return results

    def task_get_dataset(self, task_i, dataset_ids):
        dataset_id = dataset_ids[task_i]
        url = f'{IRR_BASE_URL}/api/v1/dataset/{dataset_id}/'
        headers = self.base_headers.copy()

        start_time = time.perf_counter()
        response = requests.get(url, headers=headers)
        elapsed_time = time.perf_counter() - start_time

        if response.status_code != 200:
            self.logger.warning(f'Get dataset {dataset_id} returned {response.status_code}: {response.text[:200]}')
        return elapsed_time

    def irr_analyse_datasets(self, dataset_ids, rps):
        num_operations = len(dataset_ids)
        results = self.multithread_task(
            'analyse_dataset',
            self.task_analyse_dataset, num_operations, rps,
            dataset_ids=dataset_ids
        )
        return results

    def task_analyse_dataset(self, task_i, dataset_ids):
        dataset_id = dataset_ids[task_i]
        url = f'{IRR_BASE_URL}/api/v1/dataset/{dataset_id}/analysis/'
        headers = self.base_headers.copy()

        start_time = time.perf_counter()
        response = requests.get(url, headers=headers)
        elapsed_time = time.perf_counter() - start_time

        if response.status_code != 200:
            self.logger.warning(f'Analyse dataset {dataset_id} returned {response.status_code}: {response.text[:200]}')
        return elapsed_time

    def irr_get_irrigation_datapoints(self, dataset_ids, rps):
        num_operations = len(dataset_ids)
        results = self.multithread_task(
            'irrigation_datapoints',
            self.task_get_irrigation_datapoints, num_operations, rps,
            dataset_ids=dataset_ids
        )
        return results

    def task_get_irrigation_datapoints(self, task_i, dataset_ids):
        dataset_id = dataset_ids[task_i]
        url = f'{IRR_BASE_URL}/api/v1/dataset/{dataset_id}/irrigation-datapoints/'
        headers = self.base_headers.copy()

        start_time = time.perf_counter()
        response = requests.get(url, headers=headers)
        elapsed_time = time.perf_counter() - start_time

        if response.status_code != 200:
            self.logger.warning(f'Irrigation datapoints for {dataset_id} returned {response.status_code}: {response.text[:200]}')
        return elapsed_time


evaluator = IRRStressTest

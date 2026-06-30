import datetime
import time

import pandas as pd
import numpy as np

import requests

from openagri_benchmark.conf import (
    GATEKEEPER_BASE_URL,
    FARMCALENDAR_BASE_URL,
)


from ..base import BaseEvaluator




class BaseStressTestEval(BaseEvaluator):
    def __init__(self, controller, logger, setup_id, output_dir, admin_user, admin_pass):
        super().__init__(controller, logger, setup_id, output_dir, admin_user, admin_pass)

        self.num_entries = 1
        self.rps = 1
        self.setup_workload_from_postix()
        self.health_check_urls = [
        ]


    def setup_workload_from_postix(self):
        if self.controller.evaluation_postfix.lower() == 'low':
            self.num_entries = 10
            self.rps = 2
        elif self.controller.evaluation_postfix.lower() == 'medium':
            self.num_entries = 50
            self.rps = 10
        elif self.controller.evaluation_postfix.lower() == 'high':
            self.num_entries = 250
            self.rps = 50
        else:
            return
        self.logger.debug(f'Setting up workload for "{self.controller.evaluation_postfix.lower()}". RPS :{self.rps} . Num Entries {self.num_entries}')

    def calculate_stats(self, stats):
        if len(stats) == 0:
            return {}
        records = []
        container_names_map = {}
        for timestamp, containers in stats.items():
            for container in containers:
                records.append({
                    'timestamp': timestamp,
                    'container': container.get('Container'),
                    'cpu': float(container.get('CPUPerc').rstrip('%')),
                    'mem': float(container.get('MemPerc').rstrip('%'))
                })
                if container.get('Name') != '--':
                    clean_name = container.get('Name').split('-')[-2]
                    container_names_map[container.get('Container')] = clean_name

        # Convert to DataFrame
        df = pd.DataFrame(records)
        df['name'] = df['container'].map(container_names_map)

        # Group by container and calculate stats
        result = {}
        for container_name, group in df.groupby('name'):
            result[container_name] = {
                'cpu_avg': group['cpu'].mean(),
                'cpu_std': group['cpu'].std(),
                'mem_avg': group['mem'].mean(),
                'mem_std': group['mem'].std(),
                'count': len(group)
            }

        return result

    def avg_requests_time_calculation(self, service_results):
        results_keys = list(service_results.keys())
        for key in results_keys:
            if not key.endswith('request_times'):
                continue
            request_times = service_results[key]
            times_avg, times_std = (0.0, 0.0)
            p50, p95, p99 = (None, None, None)
            try:
                times_avg = float(np.average(request_times))
                if len(request_times) > 2:
                    times_std = float(np.std(request_times))
                # Calculate percentiles
                percentiles = np.percentile(request_times, [50, 95, 99])
                p50, p95, p99 = [float(p) for p in percentiles]
            except:
                #if empty times just use 0 as default
                pass
            service_results[f'{key}_avg'] = times_avg
            service_results[f'{key}_std'] = times_std
            service_results[f'{key}_p50'] = p50
            service_results[f'{key}_p95'] = p95
            service_results[f'{key}_p99'] = p99
        return service_results

    def run_service_tasks(self, service_name, service_tasks_func):
        service_results = service_tasks_func()
        service_results = self.avg_requests_time_calculation(service_results)
        service_stats = self.controller.get_stats_for_period(service_results['start_timestamp'], service_results['end_timestamp'])
        service_stats_results = self.calculate_stats(service_stats)
        service_results['stats'] = service_stats_results

        return {
            f'{service_name}_results': service_results,
        }

    def run(self):
        output = super().run()
        # access, refresh = self.task_admin_login()
        access = self.task_mocked_admin_login()
        self.logger.info(f"(mocked) Logged in successfully: Access: {access}.")
        self.base_headers['Authorization'] = f'Bearer {access}'


        # fc_results = self.fc_tasks()
        # fc_results = self.avg_requests_time_calculation(fc_results)
        # fc_stats = self.controller.get_stats_for_period(fc_results['start_timestamp'], fc_results['end_timestamp'])
        # fc_stats_result = self.calculate_stats(fc_stats)
        # fc_results['stats'] = fc_stats_result

        # output.update({
        #     'farmcalendar_results': fc_results,
        # })
        return output



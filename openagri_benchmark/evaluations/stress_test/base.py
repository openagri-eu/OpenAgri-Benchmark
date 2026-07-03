import threading
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

        self.sleep_before_stats = 2
        self.num_entries = 1
        self.rps = 1
        self.setup_workload_from_postfix()
        self.health_check_urls = [
        ]


    def setup_workload_from_postfix(self):
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
        has_interpolated = False
        for timestamp, containers in stats.items():
            for container in containers:
                records.append({
                    'timestamp': timestamp,
                    'container': container.get('Container'),
                    'cpu': min(100, float(container.get('CPUPerc').rstrip('%'))),
                    'mem': min(100, float(container.get('MemPerc').rstrip('%'))),
                    'interp': container.get('Interpolated', False),
                })
                if container.get('Interpolated'):
                    has_interpolated = True
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
                'count': len(group),
                'interp': has_interpolated,
            }

        return result

    def avg_requests_time_calculation(self, service_results):
        for task, task_result in service_results.items():
            key = 'request_times'
            request_times = task_result[key]
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
            task_result[f'{key}_avg'] = times_avg
            task_result[f'{key}_std'] = times_std
            task_result[f'{key}_p50'] = p50
            task_result[f'{key}_p95'] = p95
            task_result[f'{key}_p99'] = p99
        return service_results

    def _task_base_result_dict(self, task_name, start_timestamp, end_timestamp, request_times):
        return {
            task_name: {
                f'start_timestamp': start_timestamp,
                f'end_timestamp': end_timestamp,
                f'request_times': request_times,
            }
        }

    def calculate_per_tasks_stats(self, service_results):
        for task_name, task_result in service_results.items():
            start_timestamp = task_result['start_timestamp']
            end_timestamp = task_result['end_timestamp']
            task_stats = self.controller.get_stats_for_period(
                start_timestamp,
                end_timestamp
            )
            task_stats_results = self.calculate_stats(task_stats)
            task_result[f'stats'] = task_stats_results
        return service_results

    def multithread_task(self, task_name, task, num_operations, rps, **kwargs):
        stagger_interval = 1 / rps
        task_times = [None] * num_operations

        start_timestamp = datetime.datetime.now().isoformat()
        threads = []
        for i in range(num_operations):
            thread = threading.Timer(
                i * stagger_interval,
                self._multithread_task_worker,
                args=(task_name, task, i, task_times),
                kwargs=kwargs
            )
            thread.daemon = False
            thread.start()
            threads.append(thread)

        for thread in threads:
            thread.join()
        end_timestamp = datetime.datetime.now().isoformat()


        result = self._task_base_result_dict(task_name, start_timestamp, end_timestamp, task_times)
        return result

    def _multithread_task_worker(self, task_name, task, index, task_times, **kwargs):
        self.logger.debug(f'Running Task {task_name} ({index})')
        elapsed_time = task(index, **kwargs)
        task_times[index] = elapsed_time


    def run_service_tasks(self, service_name, service_tasks_func):
        start_timestamp = datetime.datetime.now().isoformat()
        service_results = service_tasks_func()
        end_timestamp = datetime.datetime.now().isoformat()

        final_output = {
            'start_timestamp': start_timestamp,
            'end_timestamp': end_timestamp,
            'tasks': service_results
        }
        service_results = self.avg_requests_time_calculation(service_results)
        time.sleep(self.sleep_before_stats)

        #could just change inplace from pointer, but lets make it explicit
        service_results.update(self.calculate_per_tasks_stats(service_results))

        service_stats = self.controller.get_stats_for_period(start_timestamp, end_timestamp)
        final_output['stats'] = self.calculate_stats(service_stats)

        return {
            f'{service_name}': final_output
        }

    def run(self):
        output = super().run()
        access = self.task_mocked_admin_login()
        self.logger.info(f"(mocked) Logged in successfully: Access: {access}.")
        self.base_headers['Authorization'] = f'Bearer {access}'

        return output



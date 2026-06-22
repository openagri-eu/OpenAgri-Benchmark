import datetime
import time

import pandas as pd
import requests

from openagri_benchmark.conf import GATEKEEPER_PROXY_BASE


from ..base import BaseEvaluator
from .farmcalendar import FCStressTestMixin




class StressTestEval(FCStressTestMixin, BaseEvaluator):

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

    def run(self):
        output = super().run()
        access, refresh = self.task_admin_login()
        self.logger.info(f"Logged in successfully: Access: {access}. Refresh {refresh}")
        self.base_headers['Authorization'] = f'Bearer {access}'

        fc_results = self.fc_tasks()
        fc_stats = self.controller.get_stats_for_period(fc_results['start_timestamp'], fc_results['end_timestamp'])
        fc_stats_result = self.calculate_stats(fc_stats)
        fc_results['stats'] = fc_stats_result

        output.update({
            'farmcalendar_results': fc_results,
        })
        return output


evaluator = StressTestEval

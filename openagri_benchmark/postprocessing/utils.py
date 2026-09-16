import json
import datetime
from pathlib import Path

import pandas as pd

from openagri_benchmark.conf import (
    POSTPROCESSING_INPUT_DIR,
)



def read_benchmark_results(eval_name):
    result_dict = {}

    for dir_path in Path(POSTPROCESSING_INPUT_DIR).iterdir():
        if dir_path.is_dir():
            dir_name = dir_path.name

            # Extract workload type (low, medium, high)
            workload = dir_name.split('_')[-2]  # second last part

            # Extract evaluation name and service name
            after_eval = dir_name.split(f'{eval_name}.')[1]

            service_name = after_eval.split('_')[0]

            # Extract timestamp
            timestamp = dir_name.split('_')[-1]  # second last part

            # Read JSON files
            result_file = dir_path / 'result.json'
            stats_file = dir_path / 'stats.json'

            with open(result_file, 'r') as f:
                result_content = json.load(f)

            with open(stats_file, 'r') as f:
                stats_content = json.load(f)

            # Build nested dictionary
            result_dict.setdefault(workload, {})
            result_dict[workload].setdefault(service_name, {})


            result_dict[workload][service_name][timestamp] = {
                'result': result_content,
                'stats': stats_content,
            }

    return result_dict


def fix_empty_stats(all_stats, start_timestamp, end_timestamp):
    # Sort timestamps
    start_dt = datetime.datetime.fromisoformat(start_timestamp)
    end_dt = datetime.datetime.fromisoformat(end_timestamp)
    target_dt = start_dt + ((end_dt - start_dt) / 2)

    period_stats = {}
    prev_dt = None
    prev_stats = None
    for key, stats in all_stats.items():
        dt = datetime.datetime.fromisoformat(key)
        if start_dt <= dt:
            period_stats[target_dt.isoformat()] = _interpolate_stats(
                target_dt=target_dt,
                prev_dt=prev_dt,
                prev_stats=prev_stats,
                next_dt=dt,
                next_stats=stats
            )

        prev_dt = dt
        prev_stats = stats


    return _re_calculate_stats(period_stats)

def _interpolate_stats(target_dt, prev_dt, prev_stats, next_dt, next_stats):
    ratio = (target_dt - prev_dt) / (next_dt - prev_dt)
    prev_by_id = {stat["Container"]: stat for stat in prev_stats}
    next_by_id = {stat["Container"]: stat for stat in next_stats}

    stats = []
    # go from next, since makes sense to have more new containers in future than pass...
    for container_id, c_next_stat in next_by_id.items():
        if container_id in prev_by_id:
            c_prev_stat = prev_by_id[container_id]

            prev_cpu = float(c_prev_stat['CPUPerc'].rstrip('%'))
            next_cpu = float(c_next_stat['CPUPerc'].rstrip('%'))
            prev_mem = float(c_prev_stat['MemPerc'].rstrip('%'))
            next_mem = float(c_next_stat['MemPerc'].rstrip('%'))
            container_name = c_next_stat.get('Name', '--')

            cpu_interp = prev_cpu + ((next_cpu - prev_cpu) * ratio)
            mem_interp = prev_mem + ((next_mem - prev_mem) * ratio)
            interpolated = {
                "Container": container_id,
                "Name": container_name,
                "CPUPerc": f"{cpu_interp:.2f}%",
                "MemPerc": f"{mem_interp:.2f}%",
                "Interpolated": True,
            }
            stats.append(interpolated)

    return stats

def _re_calculate_stats(stats):
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

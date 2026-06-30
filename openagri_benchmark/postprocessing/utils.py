import json
from pathlib import Path

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
                'stats': stats_content
            }

    return result_dict

import datetime
import importlib
import json
import time
import os
import shutil
import subprocess
import threading

from openagri_benchmark.conf import (
    OUTPUTS_DIR,
    LOGGING_LEVEL,
    WAIT_SECONDS_AFTER_UP,
    STATS_INTERVAL_SECONDS,
    GATEKEEPER_ADMIN_USER,
    GATEKEEPER_ADMIN_PASSWORD,
)
from openagri_benchmark.logger import setup_logging


class BenchmarkController(object):

    def __init__(self, evaluation_name, bootstrap_dir=None, postfix=None, force_reset_output=False):
        self.logger = setup_logging(evaluation_name, LOGGING_LEVEL)
        self.bootstrap_dir = bootstrap_dir
        self.evaluation_name = evaluation_name
        self.evaluation_postfix = postfix if postfix else ''
        self.init_timestamp = datetime.datetime.now()
        self.str_init_timestamp = self.init_timestamp.strftime("%Y-%m-%d-%H%M%S")
        self.setup_id = '_'.join([self.evaluation_name, self.evaluation_postfix, self.str_init_timestamp])
        self.output_dir = os.path.join(OUTPUTS_DIR, self.setup_id)
        self.force_reset_output = force_reset_output
        self.setup_controller()

    def start_containers(self):
        if self.bootstrap_dir is None:
            self.logger.debug('No bootstrap dir passed, ignoring bootstrap control')
            return

        self.logger.info(f'Will start containers in bootstrap directory at: {self.bootstrap_dir}.')
        compose_script = os.path.join(self.bootstrap_dir, 'run_compose.py')
        subprocess.run(['python3', compose_script, 'up', '-d'], cwd=self.bootstrap_dir, check=True)
        self.logger.info(f'Will wait for {WAIT_SECONDS_AFTER_UP} seconds before starting evalution...')
        time.sleep(WAIT_SECONDS_AFTER_UP)

    def start_container_stats(self):
        self._stats = {}
        if self.bootstrap_dir is None:
            self.logger.debug('No bootstrap dir passed, ignoring bootstrap control')
            return
        self.stats_stop_event = threading.Event()
        self.stats_thread = threading.Thread(target=self._collect_stats, daemon=True)
        self.stats_thread.start()

    def _collect_stats(self):
        stats_file = os.path.join(self.output_dir, 'container_stats.log')
        stats_script = os.path.join(self.bootstrap_dir, 'run_compose.py')

        while not self.stats_stop_event.is_set():
            timestamp = datetime.datetime.now().isoformat()
            result = subprocess.run(
                ['python3', stats_script, 'stats', '--no-stream', '--format', 'json'],
                cwd=self.bootstrap_dir,
                capture_output=True,
                text=True
            )

            with open(stats_file, 'a') as f:
                f.write(f"# {timestamp}\n")
                self._stats.setdefault(timestamp, [])
                for line in result.stdout.splitlines():
                    if line.strip().startswith('{'):
                        f.write(f"{line}\n")
                        data_line = json.loads(line)
                        self._stats[timestamp].append(data_line)
                f.flush()

    def get_stats_for_period(self, start_timestamp, end_timestamp):
        if not self._stats:
            return {}
        start_dt = datetime.datetime.fromisoformat(start_timestamp)
        end_dt = datetime.datetime.fromisoformat(end_timestamp)

        all_stats = self._stats.copy()
        filter_lambda = lambda item: start_dt <= datetime.datetime.fromisoformat(item[0]) <= end_dt
        return dict(
            filter(
                filter_lambda,
                all_stats.items()
            )
        )

    def destroy_containers(self):
        if self.bootstrap_dir is None:
            self.logger.debug('No bootstrap dir passed, ignoring bootstrap control')
            return
        compose_script = os.path.join(self.bootstrap_dir, 'run_compose.py')
        subprocess.run(['python3', compose_script, 'down', '-v'], cwd=self.bootstrap_dir, check=True)

    def stop_container_stats(self):
        if self.bootstrap_dir is None:
            self.logger.debug('No bootstrap dir passed, ignoring bootstrap control')
            return
        if hasattr(self, 'stats_stop_event'):
            self.stats_stop_event.set()
        if hasattr(self, 'stats_thread') and self.stats_thread.is_alive():
            self.stats_thread.join(timeout=2)
            if self.stats_thread.is_alive():
                self.logger.warning("Stats thread did not stop gracefully")

    def setup_controller(self):
        if os.path.exists(self.output_dir):
            if not self.force_reset_output:
                raise RuntimeError(f'Cannot continue since output directory ("{self.output_dir}") is not empty, and forced reset is False.')
            shutil.rmtree(self.output_dir)
            self.logger.debug(f'Forced reset of output dir: "{self.output_dir}".')
        os.makedirs(self.output_dir)
        self.start_container_stats()
        self.start_containers()
        self.logger.info(f'Deployment setup ready.')

    def load_evaluator(self, evaluation_name):
        eval_module = importlib.import_module(f'openagri_benchmark.evaluations.{evaluation_name}')
        evaluator_cls = getattr(eval_module, 'evaluator')
        evaluator = evaluator_cls(
            controller=self,
            logger=self.logger,
            setup_id=self.setup_id,
            output_dir=self.output_dir,
            admin_user=GATEKEEPER_ADMIN_USER,
            admin_pass=GATEKEEPER_ADMIN_PASSWORD
        )
        return evaluator

    def save_result(self, result):
        result_file = os.path.join(self.output_dir, 'result.json')
        with open(result_file, 'w') as f:
            json.dump(result, f, indent=4)

    def save_final_stats(self, result):
        data_file = os.path.join(self.output_dir, 'stats.json')
        with open(data_file, 'w') as f:
            json.dump(result, f, indent=4)


    def run(self):
        result = {}
        try:
            evaluator = self.load_evaluator(self.evaluation_name)
            result = evaluator.run()
        except KeyboardInterrupt as kie:
            self.logger.warning('Forcefully stopping benchmark.')
            result['error'] = str('Forcefully stopping benchmark.')
        except Exception as e:
            self.logger.exception(e)
            result['error'] = str(e)
        finally:
            self.stop_container_stats()
            self.destroy_containers()

        try:
            self.save_result(result)
            self.save_final_stats(self._stats)
        except Exception as e:
            # if another error happens, lets just ignore at this point
            # and at least print out the original result
            self.logger.error("Error when trying to save results to disk:")
            self.logger.exception(e)
        return result

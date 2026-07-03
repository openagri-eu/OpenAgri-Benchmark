import datetime
import importlib
import json
import time
import os
import shutil
import subprocess
import threading

import requests

from openagri_benchmark.conf import (
    OUTPUTS_DIR,
    LOGGING_LEVEL,
    HEALTHCHECK_TIMEOUT,
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
        self.health_check_init_timestamp = None
        self.health_check_timeout = HEALTHCHECK_TIMEOUT
        self.health_check_interval = 1
        self.setup_controller()

    def _health_check_url(self, check_url):
        check_ok = False
        while not check_ok:
            self.logger.info(f'Healthchecking url: {check_url}')
            try:
                response = requests.get(check_url)
                response.raise_for_status()
            except:
                check_ok = False
                self.logger.info(f'Healthchecking failed for url: {check_url}. Retry in {self.health_check_interval}s...')
                elapsed_time = datetime.datetime.now() - self.health_check_init_timestamp
                if elapsed_time.seconds > self.health_check_timeout:
                    self.init_timestamp = datetime.datetime.now()
                    raise RuntimeError(f'Healthcheck timeout ({self.health_check_timeout}) while processing {check_url}')
                else:
                    time.sleep(self.health_check_interval)
            else:
                check_ok = True
                self.logger.info(f'Healthchecking OK for url: {check_url}')

        return check_ok

    def init_health_check_test(self, health_check_urls):
        self.logger.info(f'Waiting for health check on the following urls: {health_check_urls}')
        self.health_check_init_timestamp = datetime.datetime.now()
        for check_url in health_check_urls:
            self._health_check_url(check_url)

    def start_containers(self):
        if self.bootstrap_dir is None:
            self.logger.debug('No bootstrap dir passed, ignoring bootstrap control')
            return

        self.logger.info(f'Will start containers in bootstrap directory at: {self.bootstrap_dir}.')
        compose_script = os.path.join(self.bootstrap_dir, 'run_compose.py')
        subprocess.run(['python3', compose_script, 'up', '-d'], cwd=self.bootstrap_dir, check=True)

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
            self.logger.debug('Running docker stats...')
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
        # self.logger.error(f'- get_stats_for_period: {start_timestamp} - {end_timestamp}...')
        if not self._stats:
            self.logger.warning(f'No internal stats datastructure available to query for...')
            return {}
        start_dt = datetime.datetime.fromisoformat(start_timestamp)
        end_dt = datetime.datetime.fromisoformat(end_timestamp)

        all_stats = self._stats.copy()


        period_stats = {}
        prev_dt = None
        prev_stats = None
        for key, stats in all_stats.items():
            dt = datetime.datetime.fromisoformat(key)
            if start_dt <= dt <= end_dt:
                period_stats[key] = stats
            elif dt > end_dt:
                # self.logger.error(f'No more stats for {start_timestamp} - {end_timestamp}. Current stats ({len(period_stats)})')
                if len(period_stats) == 0:
                    # self.logger.error(f'No stats registered for {start_timestamp} - {end_timestamp}... checking prev_dt: {prev_dt}')
                    if prev_dt is not None:
                        target_dt = start_dt + ((end_dt - start_dt) / 2)
                        period_stats[target_dt.isoformat()] = self._interpolate_stats(
                            target_dt=target_dt,
                            prev_dt=prev_dt,
                            prev_stats=prev_stats,
                            next_dt=dt,
                            next_stats=stats
                        )
                    else:
                        # self.logger.error(f'No prev_dt for {start_timestamp}. No interpolation possible.')
                        pass

                break
            prev_dt = dt
            prev_stats = stats
        if len(period_stats) == 0:
            self.logger.error(f'No stat timestamp after {start_timestamp}. Last timestamp was: {prev_dt.isoformat()}')

        return period_stats


    def _interpolate_stats(self, target_dt, prev_dt, prev_stats, next_dt, next_stats):
        # self.logger.error(f'Interpolating for: {target_dt} with start: {prev_dt}. End: {next_dt}')
        # self.logger.error(f'prev_stats: {prev_stats} . Next stats: {next_stats}')

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
            self.init_health_check_test(evaluator.health_check_urls)
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

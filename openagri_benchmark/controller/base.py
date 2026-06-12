import datetime
import importlib
import json
import time
import os
import shutil

from openagri_benchmark.conf import (
    OUTPUTS_DIR,
    SANDBOX_DIR,
    LOGGING_LEVEL,
    GATEKEEPER_ADMIN_USER,
    GATEKEEPER_ADMIN_PASSWORD,
)
from openagri_benchmark.logger import setup_logging
from openagri_benchmark.evaluations import BaseEvaluator


class BenchmarkController(object):

    def __init__(self, evaluation_name, postfix=None, force_reset_output=False):
        self.logger = setup_logging(evaluation_name, LOGGING_LEVEL)
        self.evaluation_name = evaluation_name
        self.evaluation_postfix = postfix if postfix else ''
        self.init_timestamp = datetime.datetime.now()
        self.str_init_timestamp = self.init_timestamp.strftime("%Y-%m-%d-%H%M%S")
        self.setup_id = '_'.join([self.evaluation_name, self.evaluation_postfix, self.str_init_timestamp])
        self.output_dir = os.path.join(OUTPUTS_DIR, self.setup_id)
        self.force_reset_output = force_reset_output
        self.setup_controller()

    def setup_controller(self):
        if os.path.exists(self.output_dir):
            if not self.force_reset_output:
                raise RuntimeError(f'Cannot continue since output directory ("{self.output_dir}") is not empty, and forced reset is False.')
            shutil.rmtree(self.output_dir)
            self.logger.debug(f'Forced reset of output dir: "{self.output_dir}".')
        os.makedirs(self.output_dir)

    def load_evaluator(self, evaluation_name):
        eval_module = importlib.import_module(f'openagri_benchmark.evaluations.{evaluation_name}')
        evaluator_cls = getattr(eval_module, 'evaluator')
        evaluator = evaluator_cls(
            logger=self.logger,
            output_dir=self.output_dir,
            admin_user=GATEKEEPER_ADMIN_USER,
            admin_pass=GATEKEEPER_ADMIN_PASSWORD
        )
        return evaluator

    def save_result(self, result):
        result_file = os.path.join(self.output_dir, 'result.json')
        with open(result_file, 'w') as f:
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

        try:
            self.save_result(result)
        except Exception as e:
            # if another error happens, lets just ignore at this point
            # and at least print out the original result
            self.logger.error("Error when trying to save results to disk:")
            self.logger.exception(e)
        return result

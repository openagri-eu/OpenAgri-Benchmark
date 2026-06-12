#!/usr/bin/env python
import sys
import json

from openagri_benchmark.controller import BenchmarkController

def run(evaluation_name, postfix, force_reset_output):
    bmc = BenchmarkController(
        evaluation_name=evaluation_name,
        postfix=postfix,
        force_reset_output=force_reset_output
    )
    print(json.dumps(bmc.run(), indent=4))


if __name__ == '__main__':
    args = sys.argv[1:]
    if len(args) == 0:
        print('Usage: python3 cli.py <evaluation_name> [postfix (default="")] [force_reset_output (default=True)]')
        exit(1)
    evaluation_name = args[0]
    postfix = None
    force_reset_output = False
    if len(args) > 1:
        postfix = args[1]
        if len(args) > 2:
            fres_str = args[2].lower()
            force_reset_output = (fres_str == 'true')
    run(evaluation_name, postfix, force_reset_output)

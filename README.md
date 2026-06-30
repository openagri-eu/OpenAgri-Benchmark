# OpenAgri Benchmark Repository
🇪🇺 *"This repository was created in the context of OpenAgri project (https://horizon-openagri.eu/). OpenAgri has received funding from the EU’s Horizon Europe research and innovation programme under Grant Agreement no. 101134083."*


A set of toolkits to perform reproducible experiments and evaluations of the performance of the OpenAgri ecosystem of services.

## Repository Structure

* Inside `./openagri_benchmark` is where all the code lives, and where entry point for running any evaluation is: `./openagri_benchmark/cli.py`.
* Inside `./openagri_benchmark/evaluations` you will find all available evaluators, including the `base.py` containing the `BaseEvaluator`, which you can inherity to create your own evaluator.
* Inside `./outputs` will you find the directory that is created for every evaluation execution separabed by their id, timestamp and the optional postfix string.
* In the `./bootstrapconfs` directory you will the specific configurations (or group of configurations) necessary to setup different bootstrap environments as a reference.
* In the `./bootstrap_sandbox` is where you should clone a fresh copy of the Bootstrap Repository, and into which where you should copy the reference configs. If this is not done, the evaluations won't be able to retrieve real-time statistics from docker.
* Inside `./openagri_benchmark/postprocessing` you will find Jupyter notebooks for running post-processing on the evaluations executed.

## Setup
Before running make sure to use use Python 3.10.12 or above. Also, you should use a venv when doing this.

To install this library you should clone it locally, then inside the cloned directory run:
`pip install -e .`

This will install all libraries and requirements, and will make sure that the benchmark repository is installed.

All the commands for evaluation of the reproducible experiments are to be executed from within this directory.

### Setting up Configurations (.env file)
You'll need to setup the environment variables in order to connect with an existing running setup of OpenAgri Bootstrap: First copy the `example.env` file into a new file called `.env`, and replace the values according to the location, and admin user details of your OpenAgri Bootstrap configuration.

You may also change the `OUTPUTS_DIR` to the full path of any directory in your machine. By defaul this will be set to the `./outputs` directory inside the repository.

If you wish to have real-time statistics from docker (CPU, Mem, etc..) then you also need to set `BOOTSTRAP_DIR` to the full path to your fresly cloned Bootstrap repository within `./bootstrap_sandbox` directory.

## Running
A simple CLI is available to run one of the existing evaluations within the linked OpenAgri Bootstrap setup (environment variables): `openagri_benchmark/cli.py`.

This CLI takes as argument:
* Evaluation name (required): name of the evaluation Python module inside `openagri_benchmark/evaluations` that you wish to use for this run.
* Evaluation Name Postfix (optional): Optional postfix string to be added to the evaluation ID. Default to blank.
* Force Reset Output (option): If set to True this will delete any existing output directory with same ID before running an evaluation. By default this is set to False, and the application exists in case the evaluation output directory already exists.

### Example of use:
To run the `simple_eval` evaluation, we call:

`python3 openagri_benchmark/cli.py simple_eval`

This will create an output directory using the evaluation name, and timestamp (e.g.: `./outputs/simple_eval__2026-06-12-123244`). Inside this output directory it will contain a `result.json` file with the output of this evaluation. Other evaluations might create additional files inside this directory as well.

Passing the optional postfix parameter (e.g., "testing"), you would call it as:

`python3 openagri_benchmark/cli.py simple_eval testing`

This will create a similar output directory as before, but also including the postfix string in the evaluation ID, e.g.: `./outputs/simple_eval_testing_2026-06-12-123244`.

## Errors
In case any errors occur during an evaluation, they will be logged inside the `results.json` file.

## Forcefully Stopping an Evaluation
To force the stop of a running evaluation just press `ctrl+c`. An error message will also be recorded in the evaluation result.json file about the forced stop.

# Adding New Evaluations
To add a new evaluation, create a python module file with the name of your evaluation (e.g., `my_eval`) inside `./openagri_benchmark/evaluations`.
Inside this module you'll need to create a new evaluator class (e.g., `MyEval`) by import and inherit the base evaluator class (`BaseEvaluator`) from `openagri_benchmark.evaluations.base`.

Your evaluator should override the default `run` method, and it must always return a dictionary with the output of your evaluation.

If you want to ensure that the evaluation only starts after some health checks, then you'll also need to add the list of urls that need to return a successfull response in the health_check_urls. You can do that by override the init method of your evaluator:

```python
    def __init__(self, controller, logger, setup_id, output_dir, admin_user, admin_pass):
        super().__init__(controller, logger, setup_id, output_dir, admin_user, admin_pass)
        self.health_check_urls = [
            GATEKEEPER_BASE_URL,
        ]
```

Finally, in the end the file of your new python module, you will need to pass your newly created evaluator class into a variable called `evaluator`. Example:
`evaluator = MyEval`

You will then be able to call this new evaluation by using the cli.py:
`python3 openagri_benchmark/cli.py my_eval`

Alternativelly, if you have a more complex evaluation setup, you may also have nested evaluations within modules inside the `openagri_benchmark.evaluations` module. For example, the individual services' stress-test are organized as submodules inside `openagri_benchmark.evaluations.stress_test`, therefore they run passing the relative python path to the actual evaluation:
`python3 openagri_benchmark/cli.py stress_test.pestanddisease`

For more informations, see the example of the [simple_eval.py](./openagri_benchmark/evaluations/simple_eval.py)

# OpenAgri Bootstrap Configurations
To use the reference setup from the `bootstrapconfs` you just need to copy the contents of a given setup directory inside a newly cloned OpenAgri Bootstrap repository (inside `./bootstrap_sandbox`). This will give you a preconfigured bootstrap repository for the specific scenario.

For instance, to get the proper deployment environment for the stress test of just the Farm Calendar service, you should copy the files from `./bootstrapconfs/service-stress-test/fc` over the files from the Bootstrap Repo cloned within `./boostrap_sandbox`.

# Post-Processing
Post-processing can be executed on a different machine from the one that executed the evaluations, it's only necessary to copy the output directories from the evaluations that you wish to post-process.
For running the postprocessing, first copy the necessary output directories from `OUTPUT_DIR` into `./openagri_benchmark/postprocessing/inputs`. Then check the notebook you wish to run for further details on the process and requirements.

# License
This project code is licensed under the Apache License 2.0 license, see the LICENSE file for more details.

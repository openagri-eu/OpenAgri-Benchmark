# OpenAgri Benchmark Repository
🇪🇺 *"This repository was created in the context of OpenAgri project (https://horizon-openagri.eu/). OpenAgri has received funding from the EU’s Horizon Europe research and innovation programme under Grant Agreement no. 101134083."*


A set of toolkits to perform reproducible experiments and evaluations of the performance of the OpenAgri ecosystem of services.

## Repository Structure

* Inside `./openagri_benchmark` is where all the code lives, and where entry point for running any evaluation is: `./openagri_benchmark/cli.py`.
* Inside `./openagri_benchmark/evaluations` you will find all available evaluators, include the `base.py` containing the `BaseEvaluator`, which you can inherity to create your own evaluator.
* Inside `./outputs` will you find the directory that is created for every evaluation execution separabed by their id, timestamp and the optional postfix string.

## Setup
Before running make sure to use use Python 3.10.12 or above. Also, you should use a venv when doing this.

To install this library you should clone it locally, then inside the cloned directory run:
`pip install -e .`

This will install all libraries and requirements, and will make sure that the benchmark repository is installed.

All the commands for evaluation of the reproducible experiments are to be executed from within this directory.

### Setting up Configurations (.env file)
You'll need to setup the environment variables in order to connect with an existing running setup of OpenAgri Bootstrap: First copy the `example.env` file into a new file called `.env`, and replace the values according to the location, and admin user details of your OpenAgri Bootstrap configuration.

You may also change the OUTPUTS_DIR to the full path of any directory in your machine. By defaul this will be set to the `./outputs` directory inside the repository.

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

Finally, in the end the file of your new python module, you will need to pass your newly created evaluator class into a variable called `evaluator`. Example:
`evaluator = MyEval`

You will then be able to call this new evaluation by using the cli.py:
`python3 openagri_benchmark/cli.py my_eval`

For more informations, see the example of the [simple_eval.py](./openagri_benchmark/evaluations/simple_eval.py)


# License
This project code is licensed under the Apache License 2.0 license, see the LICENSE file for more details.

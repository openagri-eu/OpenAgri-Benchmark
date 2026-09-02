#!/bin/bash

WORKLOAD=$1
SECONDS_WAIT=3

echo "Running with workload: $WORKLOAD"
source .env


stress_tests=("weather" "farmcalendar" "pestanddisease" "reporting" "irrigation")
conf_dirs=("wd" "fc" "pnd" "rp" "irr")

for i in "${!stress_tests[@]}"; do
    service_name="${stress_tests[$i]}"
    conf_dir="${conf_dirs[$i]}"

    echo "====== Reseting and setting up bootstrap sandbox for ${service_name} stress test..."
    # Call the Python script to reset git and copy configs
    python3 openagri_benchmark/clean_setup_sandbox.py "service-stress-test/${conf_dir}"

    echo "====== Running batch of ${service_name} ($WORKLOAD) stress test (total of 3 per service)..."
    python3 openagri_benchmark/cli.py "stress_test.${service_name}" "$WORKLOAD"
    echo "====== First ${service_name} ($WORKLOAD)  stress test done, waiting $SECONDS_WAIT seconds before next.."
    sleep $SECONDS_WAIT
    python3 openagri_benchmark/cli.py "stress_gtstest.${service_name}" "$WORKLOAD"
    echo "====== Second ${service_name} ($WORKLOAD)  stress test done, waiting $SECONDS_WAIT seconds before next.."
    sleep $SECONDS_WAIT
    python3 openagri_benchmark/cli.py "stress_test.${service_name}" "$WORKLOAD"
    echo "====== All three ${service_name} ($WORKLOAD)  stress test done, waiting $SECONDS_WAIT seconds before next service.."
    sleep $SECONDS_WAIT
done

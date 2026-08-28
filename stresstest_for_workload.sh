#!/bin/bash

WORKLOAD=$1
SECONDS_WAIT=3

echo "Running with workload: $WORKLOAD"
source .env


stress_tests=("farmcalendar" "pestanddisease" "weather" "reporting" "irrigation")
conf_dirs=("fc" "pnd" "wd" "rp" "irr")

for i in "${!stress_tests[@]}"; do
    service_name="${stress_tests[$i]}"
    conf_dir="${conf_dirs[$i]}"

    echo "====== Reseting and setting up bootstrap sandbox for ${service_name} stress test..."
    pushd "$BOOTSTRAP_DIR" || exit 1
    git reset --hard
    git clean -fdx
    popd
    echo "${conf_dir} ${BOOTSTRAP_DIR}"
    cp -rv "./bootstrapconfs/service-stress-test/${conf_dir}/"* "$BOOTSTRAP_DIR/"
    cp -v "./bootstrapconfs/service-stress-test/${conf_dir}/.env" "$BOOTSTRAP_DIR/"

    echo "====== Running batch of ${service_name} ($WORKLOAD) stress test (total of 3 per service)..."
    python3 openagri_benchmark/cli.py "stress_test.${service_name}" "$WORKLOAD"
    echo "====== First ${service_name} ($WORKLOAD)  stress test done, waiting $SECONDS_WAIT seconds before next.."
    sleep $SECONDS_WAIT
    python3 openagri_benchmark/cli.py "stress_test.${service_name}" "$WORKLOAD"
    echo "====== Second ${service_name} ($WORKLOAD)  stress test done, waiting $SECONDS_WAIT seconds before next.."
    sleep $SECONDS_WAIT
    python3 openagri_benchmark/cli.py "stress_test.${service_name}" "$WORKLOAD"
    echo "====== All three ${service_name} ($WORKLOAD)  stress test done, waiting $SECONDS_WAIT seconds before next service.."
    sleep $SECONDS_WAIT
done

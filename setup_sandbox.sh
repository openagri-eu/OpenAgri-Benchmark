#!/bin/bash

# Define variables
REPO_URL="https://github.com/agstack/OpenAgri-Bootstrap-Deployment.git"
TARGET_DIR="./bootstrap_sandbox"

pushd "$TARGET_DIR"

echo "Cloning OpenAgri-Benchmark repository into $TARGET_DIR/OpenAgri-Bootstrap-Deployment..."
git clone "$REPO_URL"

popd

#!/bin/bash
# Sync docs and .env.example to skills folder

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

mkdir -p skills/docs
mkdir -p skills/examples
cp -r docs/* skills/docs/
cp -r examples/* skills/examples/
cp examples/.env.example skills/examples/
cp README.md skills/

echo "Synced docs, examples and .env.example to skills folder"

#!/bin/bash
# Sync docs and .env.example to skills folder

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

rm -rf skills
mkdir -p skills/docs skills/examples
cp -r docs/* skills/docs/
cp -r examples/* skills/examples/
cp examples/.env.example skills/examples/
cp README.md skills/
cp SKILL.md skills/

echo "Synced docs, examples, SKILL.md and .env.example to skills folder"

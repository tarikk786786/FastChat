#!/bin/bash
# Exit on error
set -o errexit

echo "Updating pip..."
pip install --upgrade pip

echo "Installing FastChat with webui dependencies..."
pip install -e ".[webui]"

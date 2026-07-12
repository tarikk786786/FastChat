#!/bin/bash
# Exit on error
set -o errexit

echo "Updating pip..."
pip install --upgrade pip

echo "Installing CPU-only PyTorch to save space and resources..."
pip install torch --index-url https://download.pytorch.org/whl/cpu

echo "Installing FastChat with model_worker and webui dependencies..."
pip install -e ".[model_worker,webui]"

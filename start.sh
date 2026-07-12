#!/bin/bash

# Start the Controller
echo "Starting FastChat Controller..."
python3 -m fastchat.serve.controller --host 0.0.0.0 --port 21001 &

# Wait for the controller to be up
sleep 5

# Start the Model Worker with a tiny model to fit into Render's free tier memory
echo "Starting FastChat Model Worker (sshleifer/tiny-gpt2)..."
python3 -m fastchat.serve.model_worker --model-path sshleifer/tiny-gpt2 --model-names "tiny-gpt2,gpt-3.5-turbo" --host 0.0.0.0 --port 21002 --controller-address http://localhost:21001 &

# Wait for worker to register
sleep 5

# Start the OpenAI API Server in the background
echo "Starting FastChat OpenAI API Server..."
python3 -m fastchat.serve.openai_api_server --host 0.0.0.0 --port 8000 --controller-address http://localhost:21001 &

# Start the Gradio Web Server (runs on the port Render exposes)
echo "Starting FastChat Gradio Web Server on port $PORT..."
python3 -m fastchat.serve.gradio_web_server --host 0.0.0.0 --port $PORT --controller-url http://localhost:21001

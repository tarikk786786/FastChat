#!/bin/bash

# Create logs directory
mkdir -p logs

# Start the Controller
echo "Starting FastChat Controller..."
python3 -m fastchat.serve.controller --host 0.0.0.0 --port 21001 > logs/controller.log 2>&1 &

# Wait for the controller to be up
sleep 5

# Start the Model Worker with a tiny model to fit into Render's free tier memory
echo "Starting FastChat Mock Model Worker..."
python3 -m fastchat.serve.mock_worker --host 0.0.0.0 --port 21002 --controller-address http://127.0.0.1:21001 > logs/mock_worker.log 2>&1 &

# Wait for worker to register
sleep 5

# Start the Gradio Web Server (runs on the port Render exposes)
echo "Starting FastChat Gradio Web Server on port $PORT..."
python3 -m fastchat.serve.gradio_web_server --host 0.0.0.0 --port $PORT --controller-url http://127.0.0.1:21001 > logs/gradio.log 2>&1

# If Gradio server crashes or exits, start a fallback web server to expose the logs for debugging
echo "Gradio server exited. Starting fallback log server on port $PORT..."
python3 -c "
import http.server
import socketserver
import os

class MyHandler(http.server.SimpleHTTPRequestHandler):
    def translate_path(self, path):
        # Force serving from the logs directory
        return os.path.join('logs', path.lstrip('/'))

PORT = int(os.environ.get('PORT', 10000))
with socketserver.TCPServer(('', PORT), MyHandler) as httpd:
    print('Exposing logs on port', PORT)
    httpd.serve_forever()
"

import argparse
import asyncio
import json
import os
import threading
import time
import uuid
from typing import List

from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
import requests
import uvicorn

from fastchat.constants import WORKER_HEART_BEAT_INTERVAL
from fastchat.utils import build_logger

worker_id = str(uuid.uuid4())[:8]
logger = build_logger("model_worker", f"model_worker_{worker_id}.log")
app = FastAPI()

def heart_beat_worker(obj):
    while True:
        time.sleep(WORKER_HEART_BEAT_INTERVAL)
        obj.send_heart_beat()

class MockWorker:
    def __init__(self, controller_addr, worker_addr, model_names):
        self.controller_addr = controller_addr
        self.worker_addr = worker_addr
        self.model_names = model_names
        self.context_len = 2048
        self.semaphore = asyncio.Semaphore(100)
        self.limit_worker_concurrency = 100
        self.heart_beat_thread = None

    def init_heart_beat(self):
        self.register_to_controller()
        self.heart_beat_thread = threading.Thread(
            target=heart_beat_worker,
            args=(self,),
            daemon=True,
        )
        self.heart_beat_thread.start()

    def register_to_controller(self):
        logger.info("Register to controller")
        url = self.controller_addr + "/register_worker"
        data = {
            "worker_name": self.worker_addr,
            "check_heart_beat": True,
            "worker_status": self.get_status(),
            "multimodal": False,
        }
        try:
            r = requests.post(url, json=data)
            assert r.status_code == 200
        except Exception as e:
            logger.error(f"failed to register: {e}")

    def send_heart_beat(self):
        url = self.controller_addr + "/receive_heart_beat"
        try:
            ret = requests.post(
                url,
                json={
                    "worker_name": self.worker_addr,
                    "queue_length": 0,
                },
                timeout=5,
            )
            exist = ret.json()["exist"]
            if not exist:
                self.register_to_controller()
        except Exception as e:
            logger.error(f"heart beat error: {e}")

    def get_status(self):
        return {
            "model_names": self.model_names,
            "speed": 1,
            "queue_length": 0,
        }

    async def generate_stream(self, params):
        prompt = params["prompt"]
        response = f"Hello! This is a mock response from the lightweight mock model worker. You asked: '{prompt}'"
        
        chunks = [response[i:i+4] for i in range(0, len(response), 4)]
        
        curr_text = ""
        for chunk in chunks:
            curr_text += chunk
            yield (json.dumps({"text": curr_text, "error_code": 0}) + "\0").encode("utf-8")
            await asyncio.sleep(0.05)

worker = None

@app.post("/worker_generate_stream")
async def api_generate_stream(request: Request):
    params = await request.json()
    generator = worker.generate_stream(params)
    return StreamingResponse(generator)

@app.post("/worker_get_status")
async def api_get_status(request: Request):
    return worker.get_status()

@app.post("/worker_get_conv_template")
async def api_get_conv(request: Request):
    from fastchat.conversation import get_conv_template
    return {"conv": get_conv_template("one_shot")}

@app.post("/model_details")
async def api_model_details(request: Request):
    return {"context_length": worker.context_len}

@app.post("/count_token")
async def api_count_token(request: Request):
    params = await request.json()
    prompt = params["prompt"]
    return {"count": len(prompt.split()), "error_code": 0}

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", type=str, default="0.0.0.0")
    parser.add_argument("--port", type=int, default=21002)
    parser.add_argument("--worker-address", type=str, default="http://127.0.0.1:21002")
    parser.add_argument("--controller-address", type=str, default="http://127.0.0.1:21001")
    parser.add_argument("--model-names", type=str, nargs="+", default=["gpt-3.5-turbo", "mock-model"])
    args = parser.parse_args()

    worker = MockWorker(args.controller_address, args.worker_address, args.model_names)
    worker.init_heart_beat()

    uvicorn.run(app, host=args.host, port=args.port, log_level="info")

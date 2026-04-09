from fastapi import FastAPI, Request
from datetime import datetime
import json

app = FastAPI()
events = []

def log_request(method, path, status, client_ip, body=""):
    with open("/home/ubuntu/audit-api/requests.log", "a") as f:
        f.write(f"{datetime.utcnow()} | {method} | {path} | {status} | {client_ip} | {body}\n")

@app.get("/api/health")
async def health(request: Request):
    log_request("GET", "/api/health", 200, request.client.host)
    return {"status": "ok"}

@app.get("/api/events")
async def get_events(request: Request):
    log_request("GET", "/api/events", 200, request.client.host)
    return {"events": events}

@app.post("/api/events")
async def create_event(request: Request):
    body = await request.json()
    events.append(body)
    log_request("POST", "/api/events", 200, request.client.host, str(body))
    return {"message": "Event recorded", "event": body}

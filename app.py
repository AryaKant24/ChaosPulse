import time, random, socket, threading
from fastapi import FastAPI, Response, status
from fastapi.responses import HTMLResponse
from prometheus_client import Counter, Gauge, Histogram, generate_latest, CONTENT_TYPE_LATEST

app = FastAPI()
POD_NAME = socket.gethostname()

state = {"monkey": False, 
         "ready": True, 
         "healthy": True, 
         "latency": 0.03, 
         "err_rate": 0.02, 
         "event": "Stable"
        }

REQ_COUNT = Counter(name = "http_requests_total", documentation = "Total requests", labelnames=["pod", "route", "status"]) #increments every time a user visits the website
IN_FLIGHT = Gauge(name = "in_flight_requests", documentation="Active requests", labelnames=["pod"]) #can go +1 or -1
POD_READY = Gauge(name = "pod_readiness_state", documentation="1=Ready, 0=Evicted", labelnames=["pod"]) #can go +1 or -1
LATENCY = Histogram(name = "http_request_duration_seconds", documentation="Latency", labelnames=["pod", "route"], buckets=[0.05, 0.1, 0.5, 1.0, 2.5]) #buckets

POD_READY.labels(pod=POD_NAME).set(1)

def monkey_loop():
    while True:
        time.sleep(10)
        if not state["monkey"]: 
            continue
        r = random.random() #create a random event when monkey is true
        if r < 0.3:
            state.update({"ready": False, "event": "Readiness Drop (503)"})
            POD_READY.labels(pod=POD_NAME).set(0)
        elif r < 0.65:
            state.update({"latency": 1.2, "err_rate": 0.35, "event": "Latency/5xx Spike"})
        else:
            state.update({"ready": True, "latency": 0.03, "err_rate": 0.02, "event": "Recovered"})
            POD_READY.labels(pod=POD_NAME).set(1)

threading.Thread(target=monkey_loop, daemon=True).start()

@app.get("/", response_class=HTMLResponse)
def ui():
    return f"""<html><body style="font-family:monospace;background:#111;color:#eee;padding:2rem;">
    <h2>🐒 ChaosPulse War Room</h2>
    <p>Pod: <b>{POD_NAME}</b> | Monkey: <b>{state['monkey']}</b> | Event: <b>{state['event']}</b></p>
    <p>Readiness (/readyz): <b>{state['ready']}</b> | Liveness (/healthz): <b>{state['healthy']}</b></p>
    <button onclick="fetch('/chaos/monkey',{{method:'POST'}}).then(()=>location.reload())">Toggle Monkey</button>
    <button onclick="fetch('/chaos/spike',{{method:'POST'}}).then(()=>location.reload())">Spike Latency</button>
    <button onclick="fetch('/chaos/unready',{{method:'POST'}}).then(()=>location.reload())">Fail Readiness (503)</button>
    <button onclick="fetch('/chaos/poison',{{method:'POST'}}).then(()=>location.reload())">Fail Liveness (500)</button>
    <button onclick="fetch('/chaos/reset',{{method:'POST'}}).then(()=>location.reload())">Reset</button>
    </body></html>"""

#liveness probe - kill and restart container when 500
@app.get("/healthz")
def liveness(response: Response):
    if not state["healthy"]: 
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    return {"healthy": state["healthy"]}

#readiness probe - stop sending user traffic when 503
@app.get("/readyz")
def readiness(response: Response):
    if not state["ready"]: 
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {"ready": state["ready"]}

@app.get("/api/work")
def work(response: Response):
    IN_FLIGHT.labels(pod=POD_NAME).inc() #increment the visited count 

    start = time.time()
    time.sleep(state["latency"] + random.uniform(0.01, 0.03))  #creating a work delay
    code = "500" if random.random() < state["err_rate"] else "200"

    if code == "500": 
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

    LATENCY.labels(pod=POD_NAME, route="/api/work").observe(time.time() - start) #update histogram
    REQ_COUNT.labels(pod=POD_NAME, route="/api/work", status=code).inc() #increment request counter
    IN_FLIGHT.labels(pod=POD_NAME).dec() #decrement the active users
    return {"status": code, "pod": POD_NAME}

#Now we unleash the chaos

@app.post("/chaos/monkey")
def toggle(): 
    state["monkey"] = not state["monkey"]; return state

@app.post("/chaos/spike")
def spike(): 
    state.update({"latency": 1.5, "err_rate": 0.4, "event": "Manual Spike"}); return state

@app.post("/chaos/unready")
def unready(): 
    state.update({"ready": False, "event": "Manual Unready"}); POD_READY.labels(pod=POD_NAME).set(0); return state

@app.post("/chaos/poison")
def poison(): 
    state.update({"healthy": False, "event": "Poison Pill"}); return state

@app.post("/chaos/reset")
def reset(): 
    state.update({"monkey": False, "ready": True, "healthy": True, "latency": 0.03, "err_rate": 0.02, "event": "Reset"}); POD_READY.labels(pod=POD_NAME).set(1); return state

@app.get("/metrics")
def metrics(): return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
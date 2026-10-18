import json
import time
import uuid
from collections import deque
from datetime import datetime, timezone

from fastapi import FastAPI, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST

EMAIL = "23f3002833@ds.study.iitm.ac.in"   

START_TIME = time.time()           # remember when we started
LOG_BUFFER = deque(maxlen=1000)    # the "notebook": keeps the last 1000 entries

# The "tally clicker"
REQUESTS = Counter("http_requests_total", "Total HTTP requests")

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"],
                   allow_methods=["*"], allow_headers=["*"])


# ---- Middleware: runs on EVERY request, no matter which endpoint ----
@app.middleware("http")
async def observe(request: Request, call_next):
    REQUESTS.inc()                        # click the tally counter
    request_id = str(uuid.uuid4())        # unique ID for this request
    status = 500
    try:
        response = await call_next(request)
        status = response.status_code
        response.headers["X-Request-ID"] = request_id
        return response
    finally:
        entry = {
            "level": "INFO" if status < 400 else "ERROR",
            "ts": datetime.now(timezone.utc).isoformat(),
            "path": request.url.path,
            "request_id": request_id,
            "method": request.method,
            "status": status,
        }
        LOG_BUFFER.append(entry)            # write in the notebook
        print(json.dumps(entry), flush=True)  # also print as JSON line


@app.get("/work")
def work(n: int = Query(1, ge=0, le=100000)):
    total = 0
    for i in range(n):                # "do K units of work"
        total += i * i
    return {"email": EMAIL, "done": n}


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/healthz")
def healthz():
    return {"status": "ok", "uptime_s": float(time.time() - START_TIME)}


@app.get("/logs/tail")
def logs_tail(limit: int = Query(10, ge=0, le=1000)):
    if limit == 0:
        return []
    return list(LOG_BUFFER)[-limit:]

"""
BNBTask Worker Node — FastAPI service exposing task execution and health endpoints.
"""
import os
import sys
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Add skills to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "skills", "proof-generator"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "skills", "bsc-defi-scraper"))

from generator import generate_proof

app = FastAPI(title="BNBTask Worker Node", version="1.0.0")


class TaskRequest(BaseModel):
    protocol: str = "pancakeswap"
    task_id: str | None = None


def _detect_tee() -> str:
    try:
        from dstack_sdk import TappdClient
        TappdClient()
        return "Intel TDX"
    except Exception:
        pass
    if os.path.exists("/var/run/tappd.sock"):
        return "Intel TDX"
    return "mock (local dev)"


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "environment": "CVM" if os.path.exists("/var/run/tappd.sock") else "local",
        "tee_type": _detect_tee(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.post("/task")
def execute_task(req: TaskRequest):
    try:
        bundle = generate_proof(req.protocol)
        if req.task_id:
            bundle["task_id"] = req.task_id
        return bundle
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)

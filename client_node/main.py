"""
ProofPay Client Node — FastAPI service exposing task delegation and verification endpoints.
"""
import os
import sys
from datetime import datetime, timezone

import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "skills", "verifier"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "skills", "bnb-payer"))

from verifier import verify
from payer import pay

WORKER_URL = os.environ.get("WORKER_URL", "http://localhost:8001")

app = FastAPI(title="ProofPay Client Node", version="1.0.0")


class DelegateRequest(BaseModel):
    protocol: str = "pancakeswap"
    payment_amount: float = 0.01
    worker_address: str | None = None


@app.get("/health")
def health():
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}


@app.post("/delegate")
def delegate(req: DelegateRequest):
    # Step 1: request proof from worker
    try:
        resp = requests.post(f"{WORKER_URL}/task", json={"protocol": req.protocol}, timeout=30)
        resp.raise_for_status()
        bundle = resp.json()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Worker unreachable: {e}")

    # Step 2: verify proof
    result = verify(bundle)
    if not result["is_valid"]:
        raise HTTPException(status_code=422, detail=f"Proof invalid: {result['reason']}")

    # Step 3: pay worker
    private_key = os.environ.get("WORKER_PRIVATE_KEY", "")
    to_address = req.worker_address or bundle.get("worker_pubkey", "")
    if not private_key or not to_address or to_address.startswith("0x000000"):
        return {"bundle": bundle, "verify": result, "payment": {"skipped": True, "reason": "no key or address"}}

    payment = pay(private_key, to_address, req.payment_amount)
    return {"bundle": bundle, "verify": result, "payment": payment}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)

"""
ProofPay Task Delegator — Client-side orchestrator.
Coordinates: Worker data fetch → proof verify → BSC USDT payment.
"""
import argparse
import json
import os
import sys

import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "verifier"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "bnb-payer"))

from verifier import verify
from payer import pay

WORKER_URL = os.environ.get("WORKER_URL", "http://localhost:8001")


def delegate(protocol: str = "pancakeswap", payment_amount: float = 0.01,
             worker_address: str = "") -> dict:

    # Step 1: delegate to worker
    print(f"[1] Requesting ProofBundle from Worker ({WORKER_URL})...")
    resp = requests.post(f"{WORKER_URL}/task", json={"protocol": protocol}, timeout=30)
    resp.raise_for_status()
    bundle = resp.json()
    print(f"    task_id  : {bundle.get('task_id')}")
    print(f"    protocol : {bundle.get('data', {}).get('protocol')}")
    print(f"    tvl_usd  : ${bundle.get('data', {}).get('tvl_usd', 0):,.2f}")
    print(f"    zk_type  : {bundle.get('zk_proof', {}).get('type')}")
    print(f"    tee_type : {bundle.get('tee_attestation', {}).get('type')}")

    # Step 2: verify proof
    print("\n[2] Verifying ProofBundle (3-layer)...")
    result = verify(bundle)
    print(f"    ZK Layer : {'[OK]' if result['zk_valid'] else '[FAIL]'}")
    print(f"    TEE Layer: {'[OK]' if result['tee_valid'] else '[FAIL]'}")
    cv = result["cross_validation"]
    print(f"    Binance  : BNB=${cv.get('bnb_price_usd')} sane={cv.get('tvl_sane')}")
    print(f"    Result   : {'[VALID]' if result['is_valid'] else '[INVALID]'}")

    if not result["is_valid"]:
        return {"bundle": bundle, "verify": result, "payment": None,
                "error": f"Proof invalid: {result['reason']}"}

    # Step 3: pay worker
    private_key = os.environ.get("WORKER_PRIVATE_KEY", "")
    to_addr = worker_address or bundle.get("worker_pubkey", "")

    if not private_key or not to_addr or to_addr.startswith("0x000000"):
        print("\n[3] Payment skipped (no key or address configured)")
        return {"bundle": bundle, "verify": result,
                "payment": {"skipped": True, "reason": "no key or address"}}

    print(f"\n[3] Paying {payment_amount} USDT → {to_addr[:10]}... (BSC)")
    payment = pay(private_key, to_addr, payment_amount)
    print(f"    TxHash  : {payment.get('txHash')}")
    print(f"    Explorer: {payment.get('explorer_url')}")

    return {"bundle": bundle, "verify": result, "payment": payment}


def main():
    parser = argparse.ArgumentParser(description="ProofPay Delegator")
    parser.add_argument("--protocol", default="pancakeswap")
    parser.add_argument("--amount", type=float, default=0.01)
    parser.add_argument("--worker-address", default="")
    parser.add_argument("--json", action="store_true", dest="json_output")
    args = parser.parse_args()

    result = delegate(args.protocol, args.amount, args.worker_address)

    if args.json_output:
        print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()

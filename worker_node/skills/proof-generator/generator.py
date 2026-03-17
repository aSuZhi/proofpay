"""
Proof Generator — wraps DataResult in zkTLS + TEE dual-layer cryptographic proof.
Layer 1: Reclaim zkFetch (data provenance)
Layer 2: Intel TDX attestation (execution integrity)
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys
import uuid
from datetime import datetime, timezone

# Worker identity
WORKER_PRIVATE_KEY = os.environ.get("WORKER_PRIVATE_KEY", "")
WORKER_ADDRESS = os.environ.get("WORKER_ADDRESS", "0x0000000000000000000000000000000000000000")


def _sha256(data: dict) -> str:
    return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()


def _generate_zk_proof(data: dict) -> dict:
    """Layer 1: Reclaim zkFetch. Falls back to SHA256 mock if unavailable."""
    data_hash = _sha256(data)
    # Try Reclaim zkFetch via Node.js bridge
    bridge = os.path.join(os.path.dirname(__file__), "zkfetch_bridge.js")
    if os.path.exists(bridge):
        try:
            result = subprocess.run(
                ["node", bridge, data["source_url"], data_hash],
                capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0:
                proof_obj = json.loads(result.stdout.strip())
                return {"type": "reclaim_zkfetch", "hash": data_hash, "proof": proof_obj}
        except Exception:
            pass
    # Fallback
    return {"type": "sha256_mock", "hash": data_hash, "proof": None}


def _generate_tee_attestation(data_hash: str) -> dict:
    """Layer 2: Intel TDX via Phala dstack. Falls back to mock if not in TEE."""
    try:
        from dstack_sdk import TappdClient
        client = TappdClient()
        quote = client.tdx_quote(data_hash)
        return {"type": "intel_tdx", "report_data": data_hash, "quote": quote}
    except Exception:
        pass
    return {"type": "mock_tdx", "report_data": data_hash, "quote": None}


def generate_proof(protocol: str) -> dict:
    # Import scraper from sibling skill
    scraper_path = os.path.join(os.path.dirname(__file__), "..", "bsc-defi-scraper")
    sys.path.insert(0, scraper_path)
    from scraper import fetch_tvl

    data = fetch_tvl(protocol)
    zk_proof = _generate_zk_proof(data)
    tee_attestation = _generate_tee_attestation(zk_proof["hash"])

    return {
        "task_id": f"bnbt-{uuid.uuid4().hex[:8]}",
        "data": data,
        "zk_proof": zk_proof,
        "tee_attestation": tee_attestation,
        "worker_pubkey": WORKER_ADDRESS,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def main():
    parser = argparse.ArgumentParser(description="BNBTask Proof Generator")
    parser.add_argument("--protocol", default="pancakeswap")
    parser.add_argument("--json", action="store_true", dest="json_output")
    args = parser.parse_args()

    bundle = generate_proof(args.protocol)

    if args.json_output:
        print(json.dumps(bundle, indent=2))
    else:
        print(f"Task ID  : {bundle['task_id']}")
        print(f"Protocol : {bundle['data']['protocol']}")
        print(f"TVL      : ${bundle['data']['tvl_usd']:,.2f}")
        print(f"ZK Proof : {bundle['zk_proof']['type']} — {bundle['zk_proof']['hash'][:16]}...")
        print(f"TEE      : {bundle['tee_attestation']['type']}")
        print(f"Worker   : {bundle['worker_pubkey']}")


if __name__ == "__main__":
    main()

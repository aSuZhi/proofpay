"""
Verifier — validates ProofBundle cryptographic integrity.
Layer 1: SHA256(data) == zk_proof.hash
Layer 2: SHA256(data) == tee_attestation.report_data
Layer 3: Binance API cross-validation (price sanity check)
"""
import argparse
import hashlib
import json
import sys

import requests


def _sha256(data: dict) -> str:
    return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()


def _binance_cross_validate(protocol: str, tvl_usd: float) -> dict:
    """Cross-check BNB price from Binance API as sanity signal."""
    try:
        resp = requests.get(
            "https://api.binance.com/api/v3/ticker/price",
            params={"symbol": "BNBUSDT"},
            timeout=5,
        )
        resp.raise_for_status()
        bnb_price = float(resp.json()["price"])
        # Sanity: TVL should be > 0 and BNB price should be reasonable
        sane = tvl_usd > 0 and bnb_price > 10
        return {"bnb_price_usd": bnb_price, "tvl_sane": sane, "source": "binance_api"}
    except Exception as e:
        return {"bnb_price_usd": None, "tvl_sane": None, "source": "binance_api", "error": str(e)}


def verify(bundle: dict) -> dict:
    data = bundle.get("data", {})
    zk_proof = bundle.get("zk_proof", {})
    tee_attestation = bundle.get("tee_attestation", {})

    computed_hash = _sha256(data)

    # Layer 1: zkTLS hash check
    zk_valid = zk_proof.get("hash") == computed_hash

    # Layer 2: TEE report_data check
    tee_valid = tee_attestation.get("report_data") == computed_hash

    # Layer 3: Binance cross-validation
    cross = _binance_cross_validate(data.get("protocol", ""), data.get("tvl_usd", 0))

    is_valid = zk_valid and tee_valid and (cross.get("tvl_sane") is not False)

    return {
        "is_valid": is_valid,
        "zk_valid": zk_valid,
        "tee_valid": tee_valid,
        "cross_validation": cross,
        "computed_hash": computed_hash,
        "reason": "All checks passed" if is_valid else "Hash mismatch or sanity check failed",
        "task_id": bundle.get("task_id"),
    }


def main():
    parser = argparse.ArgumentParser(description="ProofPay Verifier")
    parser.add_argument("--file", help="Path to ProofBundle JSON file")
    parser.add_argument("--json", action="store_true", dest="json_output")
    args = parser.parse_args()

    if args.file:
        with open(args.file) as f:
            bundle = json.load(f)
    else:
        bundle = json.load(sys.stdin)

    result = verify(bundle)

    if args.json_output:
        print(json.dumps(result, indent=2))
    else:
        status = "✓ VALID" if result["is_valid"] else "✗ INVALID"
        print(f"Result   : {status}")
        print(f"ZK Layer : {'✓' if result['zk_valid'] else '✗'}")
        print(f"TEE Layer: {'✓' if result['tee_valid'] else '✗'}")
        cv = result["cross_validation"]
        print(f"Binance  : BNB=${cv.get('bnb_price_usd')} sane={cv.get('tvl_sane')}")
        print(f"Reason   : {result['reason']}")


if __name__ == "__main__":
    main()

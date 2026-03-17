"""
BSC DeFi Scraper — fetches TVL data from DefiLlama for BSC protocols.
"""
import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone

import requests

BSC_PROTOCOLS = {
    "pancakeswap": "pancakeswap",
    "venus": "venus",
    "alpaca-finance": "alpaca-finance",
    "biswap": "biswap",
    "beefy": "beefy",
    "radiant": "radiant-v2",
}

DEFILLAMA_TVL_URL = "https://api.llama.fi/tvl/{protocol}"
DEFILLAMA_PROTOCOL_URL = "https://api.llama.fi/protocol/{protocol}"


def fetch_tvl(protocol: str) -> dict:
    slug = BSC_PROTOCOLS.get(protocol.lower(), protocol.lower())
    url = DEFILLAMA_TVL_URL.format(protocol=slug)

    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    tvl = float(resp.text.strip())

    fetched_at = datetime.now(timezone.utc).isoformat()
    data_str = json.dumps({"protocol": slug, "tvl_usd": tvl, "fetched_at": fetched_at}, sort_keys=True)
    data_hash = hashlib.sha256(data_str.encode()).hexdigest()

    return {
        "protocol": slug,
        "tvl_usd": tvl,
        "chain": "bsc",
        "fetched_at": fetched_at,
        "source_url": url,
        "data_hash": data_hash,
    }


def main():
    parser = argparse.ArgumentParser(description="BSC DeFi Scraper")
    parser.add_argument("--protocol", default="pancakeswap", help="DefiLlama protocol slug")
    parser.add_argument("--json", action="store_true", dest="json_output", help="Output raw JSON")
    args = parser.parse_args()

    result = fetch_tvl(args.protocol)

    if args.json_output:
        print(json.dumps(result, indent=2))
    else:
        print(f"Protocol : {result['protocol']}")
        print(f"TVL (USD): ${result['tvl_usd']:,.2f}")
        print(f"Chain    : {result['chain']}")
        print(f"Fetched  : {result['fetched_at']}")
        print(f"Source   : {result['source_url']}")
        print(f"Hash     : {result['data_hash']}")


if __name__ == "__main__":
    main()

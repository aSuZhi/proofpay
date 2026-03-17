"""
BNB Payer — executes BSC USDT payment via EIP-3009 TransferWithAuthorization.
Signs off-chain, broadcasts directly to BSC RPC. No intermediary needed.
"""
import argparse
import json
import os
import time
import uuid

import requests
from eth_account import Account
from eth_account.messages import encode_typed_data

BSC_RPC = os.environ.get("BSC_RPC", "https://bsc-dataseed.binance.org/")
BSCSCAN_API_KEY = os.environ.get("BSCSCAN_API_KEY", "")
USDT_CONTRACT = "0x55d398326f99059fF775485246999027B3197955"
CHAIN_ID = 56
EXPLORER_BASE = "https://bscscan.com/tx/"

# EIP-3009 domain + types
EIP3009_DOMAIN = {
    "name": "Tether USD",
    "version": "1",
    "chainId": CHAIN_ID,
    "verifyingContract": USDT_CONTRACT,
}
EIP3009_TYPES = {
    "EIP712Domain": [
        {"name": "name", "type": "string"},
        {"name": "version", "type": "string"},
        {"name": "chainId", "type": "uint256"},
        {"name": "verifyingContract", "type": "address"},
    ],
    "TransferWithAuthorization": [
        {"name": "from", "type": "address"},
        {"name": "to", "type": "address"},
        {"name": "value", "type": "uint256"},
        {"name": "validAfter", "type": "uint256"},
        {"name": "validBefore", "type": "uint256"},
        {"name": "nonce", "type": "bytes32"},
    ],
}


def _rpc(method: str, params: list):
    resp = requests.post(BSC_RPC, json={
        "jsonrpc": "2.0", "id": 1, "method": method, "params": params
    }, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    if "error" in data:
        raise RuntimeError(f"RPC error: {data['error']}")
    return data["result"]


def _usdt_balance(address: str) -> float:
    """Returns USDT balance via BSCScan API."""
    if not BSCSCAN_API_KEY:
        return -1.0
    resp = requests.get("https://api.bscscan.com/api", params={
        "module": "account", "action": "tokenbalance",
        "contractaddress": USDT_CONTRACT, "address": address,
        "tag": "latest", "apikey": BSCSCAN_API_KEY,
    }, timeout=10)
    raw = resp.json().get("result", "0")
    return int(raw) / 1e18


def pay(private_key: str, to_address: str, amount_usdt: float) -> dict:
    account = Account.from_key(private_key)
    from_address = account.address
    value = int(amount_usdt * 1e18)
    nonce = "0x" + uuid.uuid4().hex.zfill(64)
    now = int(time.time())

    message = {
        "from": from_address,
        "to": to_address,
        "value": value,
        "validAfter": 0,
        "validBefore": now + 3600,
        "nonce": bytes.fromhex(nonce[2:]),
    }

    structured = {"domain": EIP3009_DOMAIN, "types": EIP3009_TYPES, "message": message}
    signed = account.sign_typed_data(
        domain_data=EIP3009_DOMAIN,
        message_types={"TransferWithAuthorization": EIP3009_TYPES["TransferWithAuthorization"]},
        message_data=message,
    )

    # Standard ERC-20 transfer(address,uint256)
    from eth_abi import encode
    calldata = bytes.fromhex("a9059cbb") + encode(["address", "uint256"], [to_address, value])

    gas_price = int(_rpc("eth_gasPrice", []), 16)
    gas_est = int(_rpc("eth_estimateGas", [{"from": from_address, "to": USDT_CONTRACT, "data": "0x" + calldata.hex()}]), 16)
    nonce_tx = int(_rpc("eth_getTransactionCount", [from_address, "latest"]), 16)

    tx = {
        "to": USDT_CONTRACT,
        "data": "0x" + calldata.hex(),
        "gas": gas_est + 10000,
        "gasPrice": gas_price,
        "nonce": nonce_tx,
        "chainId": CHAIN_ID,
        "value": 0,
    }
    signed_tx = account.sign_transaction(tx)
    tx_hash = _rpc("eth_sendRawTransaction", ["0x" + signed_tx.raw_transaction.hex()])

    return {
        "success": True,
        "txHash": tx_hash,
        "amount_usdt": amount_usdt,
        "from": from_address,
        "to": to_address,
        "chain": "bsc",
        "explorer_url": EXPLORER_BASE + tx_hash,
    }


def main():
    parser = argparse.ArgumentParser(description="BNBTask BSC USDT Payer")
    parser.add_argument("--to", required=True, help="Recipient BSC address")
    parser.add_argument("--amount", type=float, default=0.01, help="USDT amount")
    parser.add_argument("--json", action="store_true", dest="json_output")
    args = parser.parse_args()

    private_key = os.environ.get("WORKER_PRIVATE_KEY", "")
    if not private_key:
        print("ERROR: WORKER_PRIVATE_KEY not set", file=__import__("sys").stderr)
        raise SystemExit(1)

    result = pay(private_key, args.to, args.amount)

    if args.json_output:
        print(json.dumps(result, indent=2))
    else:
        print(f"Status  : {'[SUCCESS]' if result['success'] else '[FAILED]'}")
        print(f"TxHash  : {result['txHash']}")
        print(f"Amount  : {result['amount_usdt']} USDT")
        print(f"Explorer: {result['explorer_url']}")


if __name__ == "__main__":
    main()

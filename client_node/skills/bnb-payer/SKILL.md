---
name: bnb-payer
description: "Use this skill when the user asks to 'pay with USDT on BSC', 'send BSC payment', 'transfer USDT', 'BSC支付', 'USDT转账', 'BNB链支付', or when the Client needs to release payment to a Worker after proof verification. Uses standard ERC-20 transfer() on BSC, broadcasts directly to BSC RPC. Do NOT use before verifying the ProofBundle (use verifier first). Do NOT use for non-BSC chains."
license: MIT
metadata:
  author: proofpay
  version: "1.0.0"
  homepage: "https://github.com/aSuZhi/-proofpay"
  openclaw:
    requires:
      bins: ["python"]
      env: ["WORKER_PRIVATE_KEY", "BSCSCAN_API_KEY"]
---

# SKILL: BNB Payer

> **角色**：BNBTask Client 侧 BSC USDT 支付技能，替代 OKX x402，直接在 BSC 链上完成支付。
> **上下游**：`verifier` 验证通过 → **本技能** 执行支付 → `task-delegator` 追踪交易。

---

## Pre-flight Checks

| 检查项 | 要求 |
|--------|------|
| Python 3.10+ | `python --version` |
| eth-account | `pip install eth-account` |
| eth-abi | `pip install eth-abi` |
| requests | `pip install requests` |
| WORKER_PRIVATE_KEY | 环境变量（付款方私钥） |
| BSCSCAN_API_KEY | 环境变量（余额查询，可选） |
| BSC_RPC | 环境变量（默认 bsc-dataseed.binance.org） |

---

## Skill Routing

当以下条件满足时调用：
- `verifier` 返回 `is_valid: true`
- 用户确认支付金额
- `task-delegator` Step 4 自动调用

**不应调用**：ProofBundle 未验证时；非 BSC 链支付时。

---

## Command Index

```bash
# 支付 0.01 USDT 给 Worker
python {baseDir}/payer.py --to 0xWORKER_ADDRESS --amount 0.01

# JSON 输出
python {baseDir}/payer.py --to 0xWORKER_ADDRESS --amount 0.01 --json
```

### 参数说明

| 参数 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `--to` | 是 | — | 收款方 BSC 地址 |
| `--amount` | 否 | `0.01` | USDT 金额 |
| `--json` | 否 | — | 输出原始 JSON |

---

## Operation Flow

```
Step 1 → 从 WORKER_PRIVATE_KEY 派生付款方地址
Step 2 → 编码 ERC-20 transfer(address,uint256) calldata（selector: 0xa9059cbb）
Step 3 → eth_estimateGas + eth_gasPrice（BSC RPC）
Step 4 → 构造并签名原始交易（eth_account.sign_transaction）
Step 5 → eth_sendRawTransaction → 获取 txHash
Step 6 → 返回 {txHash, amount_usdt, explorer_url}
```

---

## Input / Output Examples

**Output:**
```json
{
  "success": true,
  "txHash": "0xabc123...",
  "amount_usdt": 0.01,
  "from": "0xCLIENT...",
  "to": "0xWORKER...",
  "chain": "bsc",
  "explorer_url": "https://bscscan.com/tx/0xabc123..."
}
```

---

## BSC 合约信息

| 参数 | 值 |
|------|-----|
| USDT 合约 | `0x55d398326f99059fF775485246999027B3197955` |
| Chain ID | `56` |
| RPC | `https://bsc-dataseed.binance.org/` |
| Explorer | `https://bscscan.com` |

---

## Edge Cases

- **余额不足**：RPC 返回 `execution reverted` → 抛出 RuntimeError
- **Gas 估算失败**：通常意味着合约调用会失败，检查地址和余额
- **WORKER_PRIVATE_KEY 未设置**：立即退出，打印错误

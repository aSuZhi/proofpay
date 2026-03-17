---
name: task-delegator
description: "Use this skill when the user asks to 'verify BSC DeFi data and pay', 'run the full ProofPay flow', 'delegate a task to a Worker', mentions 'C2C', 'Agent雇佣Agent', 'trust chain', '信任链', 'ProofPay', or wants an end-to-end verified data + payment workflow on BSC. This is the Client-side orchestrator that coordinates all other skills. Do NOT use for individual operations — use the specific sub-skills directly for those."
license: MIT
metadata:
  author: proofpay
  version: "1.0.0"
  homepage: "https://github.com/aSuZhi/proofpay"
  openclaw:
    requires:
      bins: ["python"]
      env: ["WORKER_PRIVATE_KEY", "WORKER_ADDRESS", "WORKER_URL"]
    integrates:
      - binance/binance-skills-hub/binance-web3/query-token-info
      - binance/binance-skills-hub/binance-web3/crypto-market-rank
      - binance/binance-skills-hub/binance/assets
      - binance/binance-skills-hub/binance/spot
---

# SKILL: Task Delegator (ProofPay Orchestrator)

> **角色**：ProofPay Client 侧主编排器，协调 Worker 数据抓取、密码学验证、BSC 链上支付的完整 C2C 流程。
> **集成**：使用 Binance Skills Hub 官方技能进行市场数据交叉验证和资产管理。

---

## Pre-flight Checks

| 检查项 | 要求 |
|--------|------|
| Python 3.10+ | `python --version` |
| WORKER_URL | Worker FastAPI 地址（默认 `http://localhost:8001`） |
| WORKER_PRIVATE_KEY | 付款方私钥 |
| WORKER_ADDRESS | Worker 收款地址 |
| Worker 健康 | `curl $WORKER_URL/health` 返回 `{"status":"healthy"}` |
| Binance Skills Hub | `npx skills add https://github.com/binance/binance-skills-hub` |

---

## Anti-Fabrication Protocol

```
╔══════════════════════════════════════════════════════════╗
║  STOP — DO NOT FABRICATE ANY DATA                        ║
║  Every value below MUST come from a real tool call.      ║
║  If a tool fails, report the error. Never invent numbers.║
╚══════════════════════════════════════════════════════════╝
```

所有数据必须来自真实工具调用。禁止编造 TVL、价格、哈希、交易哈希。

---

## 7-Step Orchestration Flow

### Step 0a — 分析验证策略
```
调用: binance-web3/query-token-info (symbol: "CAKE" 或目标协议代币)
目的: 获取协议代币实时价格，作为 TVL 合理性基准
输出: token_price, market_cap
```

### Step 0b — 检查 USDT 余额
```
调用: binance/assets (action: "balance", asset: "USDT", chain: "BSC")
     或 BSCScan API: GET /api?module=account&action=tokenbalance
目的: 确认付款方有足够 USDT
输出: usdt_balance
条件: usdt_balance >= payment_amount → 继续
      usdt_balance < payment_amount  → Step 0c
```

### Step 0c — 余额不足时兑换（需用户确认）
```
调用: binance/spot (side: "BUY", symbol: "USDTBNB", quantity: needed)
     或提示用户手动充值
目的: 补充 USDT 余额
⚠️  必须获得用户明确确认后才执行
```

### Step 1 — 委托 Worker 抓取数据
```
调用: POST $WORKER_URL/task {"protocol": "<slug>"}
输出: ProofBundle {task_id, data, zk_proof, tee_attestation, worker_pubkey, timestamp}
验证: HTTP 200 且 task_id 存在
```

### Step 2 — 接收并展示 ProofBundle 摘要
```
展示:
  Task ID  : {task_id}
  Protocol : {data.protocol}
  TVL      : ${data.tvl_usd:,.2f}
  ZK Type  : {zk_proof.type}
  TEE Type : {tee_attestation.type}
  Worker   : {worker_pubkey}
```

### Step 3 — 三层验证
```
调用: verifier (本地) → VerifyResult
      + binance-web3/query-token-info 交叉验证代币价格合理性
      + binance-web3/crypto-market-rank 检查协议排名

验证层:
  Layer 1: SHA256(data) == zk_proof.hash          → zk_valid
  Layer 2: SHA256(data) == tee_attestation.report_data → tee_valid
  Layer 3: Binance API BNB 价格 + TVL sanity check → cross_valid

条件: is_valid == true → Step 4
      is_valid == false → 终止，报告失败原因
```

### Step 4 — BSC USDT 支付
```
调用: bnb-payer --to {worker_pubkey} --amount {payment_amount}
输出: {txHash, explorer_url}
⚠️  仅在 Step 3 验证通过后执行
```

### Step 5 — 追踪交易确认
```
调用: BSCScan API GET /api?module=transaction&action=gettxreceiptstatus&txhash={txHash}
     或 binance-web3/query-address-info (address: worker_pubkey)
等待: status == "1"（已确认）
输出: block_number, confirmations
```

### Step 6 — 输出完整信任链报告
```
╔══════════════════════════════════════════════════════════╗
║  ProofPay 信任链报告                                      ║
╠══════════════════════════════════════════════════════════╣
║  Task ID    : {task_id}                                  ║
║  Protocol   : {protocol} (BSC)                           ║
║  TVL        : ${tvl_usd:,.2f}                            ║
╠══════════════════════════════════════════════════════════╣
║  Layer 1 ZK : {zk_proof.type} ✓                          ║
║  Layer 2 TEE: {tee_attestation.type} ✓                   ║
║  Layer 3 CEX: Binance API ✓ (BNB=${bnb_price})           ║
╠══════════════════════════════════════════════════════════╣
║  Payment    : {amount} USDT → {worker_pubkey[:10]}...    ║
║  TxHash     : {txHash[:16]}...                           ║
║  Explorer   : https://bscscan.com/tx/{txHash}            ║
╚══════════════════════════════════════════════════════════╝
```

---

## Binance Skills Hub 集成

| 步骤 | 使用的官方 Skill | 用途 |
|------|----------------|------|
| Step 0a | `binance-web3/query-token-info` | 协议代币价格基准 |
| Step 0b | `binance/assets` | USDT 余额检查 |
| Step 0c | `binance/spot` | USDT 补充兑换 |
| Step 3 | `binance-web3/crypto-market-rank` | 协议排名交叉验证 |
| Step 5 | `binance-web3/query-address-info` | 交易确认追踪 |

---

## Edge Cases

- **Worker 不可达**：Step 1 失败 → 提示用户检查 `docker-compose up`
- **验证失败**：Step 3 `is_valid: false` → 终止，不执行支付，输出失败原因
- **支付失败**：Step 4 RPC 错误 → 保留 ProofBundle，提示用户手动重试
- **Binance API 限流**：降级跳过 Layer 3，仅执行 Layer 1+2

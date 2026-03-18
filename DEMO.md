# ProofPay 完整演示流程

> 可验证 BSC DeFi 数据 + 链上支付协议 · OpenClaw Agent 演示

---

## 架构总览

```
用户自然语言输入
        │
        ▼
┌───────────────────┐
│   OpenClaw Agent  │  ← 意图识别 + Skill 路由
└────────┬──────────┘
         │
         ▼
┌───────────────────────────────────────────────┐
│              task-delegator                    │
│         (Client Node 编排器)                   │
└──────┬──────────────┬────────────────┬─────────┘
       │              │                │
       ▼              ▼                ▼
┌────────────┐  ┌──────────┐  ┌─────────────┐
│ Worker Node│  │ verifier │  │  bnb-payer  │
│  :8001     │  │ 三层验证  │  │ BSC USDT   │
│ ZK + TEE   │  └──────────┘  └─────────────┘
└────────────┘
```

---

## Step 0 — 用户发起任务

**用户输入（OpenClaw 对话框）：**

```
帮我抓一下 PancakeSwap 的 TVL，通过 Worker 验证
```

**Agent 响应：**

```
✅ 识别到 proofpay skill
→ 调用 task-delegator
→ 协议: pancakeswap | 金额: 0.01 USDT
→ Worker: 0xa14056...491493
```

---

## Step 1 — Worker 抓取 DeFi 数据

**bsc-defi-scraper 调用 DefiLlama API：**

```
GET https://api.llama.fi/tvl/pancakeswap

→ TVL: $1,823,456,789
→ Chain: BSC
→ Fetched: 2026-03-18T10:00:00Z
→ Data Hash: a1b2c3d4...
```

**OpenClaw Log：**

```
[skill:bsc-defi-scraper] fetch_tvl(pancakeswap)
[skill:bsc-defi-scraper] ✅ TVL=$1.82B hash=a1b2c3d4
```

---

## Step 2 — 生成双层密码学证明

**proof-generator 执行两层证明：**

```
Layer 1: zkTLS (Reclaim Protocol)
  → zkFetch 请求 DefiLlama
  → 生成 zk_proof.type = "reclaim_zkfetch"
  → hash: a1b2c3d4e5f6...

Layer 2: Intel TDX TEE 证明
  → dstack-sdk 请求 /var/run/tappd.sock
  → 生成 tee_attestation.type = "intel_tdx"
  → quote: base64(TDX_QUOTE...)
  [本地开发: mock_tdx fallback — 正常]
```

**ProofBundle 输出：**

```json
{
  "task_id": "proofpay-a1b2c3d4",
  "data": {
    "protocol": "pancakeswap",
    "tvl_usd": 1823456789.0,
    "chain": "bsc",
    "fetched_at": "2026-03-18T10:00:00+00:00",
    "source_url": "https://api.llama.fi/tvl/pancakeswap",
    "data_hash": "a1b2c3d4..."
  },
  "zk_proof": {
    "type": "reclaim_zkfetch",
    "hash": "a1b2c3d4e5f6...",
    "proof": {}
  },
  "tee_attestation": {
    "type": "mock_tdx",
    "report_data": "a1b2c3d4...",
    "quote": "bW9ja190ZHhfcXVvdGU="
  },
  "worker_pubkey": "0xa14056bde41e3e2a7f91d47b3e80c1cc38491493",
  "timestamp": "2026-03-18T10:00:01+00:00"
}
```

---

## Step 3 — 三层验证

**verifier 执行验证：**

```
┌─────────────────────────────────────────┐
│           验证报告                        │
├─────────────────────────────────────────┤
│ ZK Layer  : ✅ [OK]  reclaim_zkfetch    │
│ TEE Layer : ✅ [OK]  mock_tdx           │
│ Binance   : BNB=$580  TVL_sane=True     │
│                                         │
│ Result    : ✅ [VALID]                  │
│ Reason    : all layers passed           │
└─────────────────────────────────────────┘
```

**交叉验证逻辑：**

```
BNB 价格 $580 (Binance API)
TVL $1.82B ÷ BNB $580 = 3,143,890 BNB
→ 在合理范围内 ✅
```

---

## Step 4 — BSC 链上支付

**bnb-payer 执行 USDT 转账：**

```
From   : 0xCLIENT...
To     : 0xa14056bde41e3e2a7f91d47b3e80c1cc38491493
Amount : 0.01 USDT (ERC-20 on BSC)
Gas    : ~0.0001 BNB

→ 广播交易...
→ TxHash : 0x7f3a...d291
→ Explorer: https://bscscan.com/tx/0x7f3a...d291
→ Status : ✅ SUCCESS
```

---

## 完整流程时序图

```
用户          OpenClaw       Worker(:8001)    Verifier    Payer
 │               │                │              │          │
 │─── 发起任务 ──▶│                │              │          │
 │               │─── POST /task ─▶│              │          │
 │               │                │─ 抓取TVL ─┐  │          │
 │               │                │◀─ DataResult┘ │          │
 │               │                │─ 生成ZK证明─┐ │          │
 │               │                │─ 生成TEE证明┘ │          │
 │               │◀── ProofBundle ─│              │          │
 │               │─────────────────────── verify ─▶│          │
 │               │◀──────────────────── VALID ────│          │
 │               │──────────────────────────────────── pay ──▶│
 │               │◀─────────────────────────────── TxHash ───│
 │◀── 完成报告 ───│                │              │          │
```

---

## 演示结果汇总

| 步骤     | 状态 | 输出                |
| -------- | ---- | ------------------- |
| TVL 抓取 | ✅   | PancakeSwap $1.82B  |
| ZK 证明  | ✅   | reclaim_zkfetch     |
| TEE 证明 | ✅   | mock_tdx (本地)     |
| 三层验证 | ✅   | VALID               |
| 链上支付 | ✅   | 0.01 USDT · BSCScan |

---

> **本地开发说明**：TEE 显示 `mock_tdx`、ZK 显示 `sha256_mock` 均为正常行为。
> 生产环境（Phala Cloud CVM）自动切换为真实 `intel_tdx` + `reclaim_zkfetch`。

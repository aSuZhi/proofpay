---
name: proofpay
description: "Use this skill when the user asks to 'run ProofPay', 'deploy ProofPay', 'start the full ProofPay protocol', 'launch worker and client', 'one-click ProofPay setup', '一键部署ProofPay', '启动ProofPay协议', or wants to run the complete verifiable DeFi data + BSC payment pipeline. This is the top-level entry point that starts both Worker and Client nodes via Docker Compose and runs the full delegation flow. Sub-skills: task-delegator, verifier, bnb-payer, bsc-defi-scraper, proof-generator."
license: MIT
metadata:
  author: proofpay
  version: "1.0.0"
  homepage: "https://github.com/aSuZhi/proofpay"
  openclaw:
    requires:
      bins: ["docker", "python"]
      env: ["CLIENT_PRIVATE_KEY", "WORKER_ADDRESS"]
    optional_env:
      - WORKER_URL
      - BSCSCAN_API_KEY
      - BSC_RPC
    integrates:
      - binance/binance-skills-hub/binance-web3/query-token-info
      - binance/binance-skills-hub/binance-web3/crypto-market-rank
      - binance/binance-skills-hub/binance/assets
      - binance/binance-skills-hub/binance/spot
---

# SKILL: ProofPay Protocol (Top-Level Entry Point)

> **角色**：ProofPay 一键部署入口。启动 Worker + Client 双节点，执行可验证 DeFi 数据抓取 → ZK/TEE 三层验证 → BSC USDT 链上结算的完整 C2C 流程。
> **子技能**：`task-delegator` · `verifier` · `bnb-payer` · `bsc-defi-scraper` · `proof-generator`

---

## Pre-flight Checks

| 检查项 | 要求 |
|--------|------|
| Docker + Compose | `docker compose version` |
| Python 3.10+ | 仅本地模式需要 |
| CLIENT_PRIVATE_KEY | 付款方 BSC 钱包私钥 |
| WORKER_ADDRESS | Worker 收款 BSC 地址 |
| 钱包余额 | ≥ 0.001 BNB（gas）+ 支付金额 USDT |

---

## Quick Start (Docker — 推荐)

```bash
# 1. 克隆并配置
git clone https://github.com/aSuZhi/proofpay && cd proofpay
cp .env.example .env
# 编辑 .env，填入 CLIENT_PRIVATE_KEY 和 WORKER_ADDRESS

# 2. 一键启动
docker compose up --build -d

# 3. 验证节点健康
curl http://localhost:8001/health   # Worker
curl http://localhost:8002/health   # Client

# 4. 运行完整流程
curl -X POST http://localhost:8002/delegate \
  -H "Content-Type: application/json" \
  -d '{"protocol":"pancakeswap","payment_amount":0.01}'
```

## Quick Start (本地 Python)

```bash
pip install -r worker_node/requirements.txt -r client_node/requirements.txt

# 终端 1 — Worker
python worker_node/main.py

# 终端 2 — Client
python client_node/main.py

# 终端 3 — 运行委托流程
export $(grep -v '^#' .env | xargs)
WORKER_PRIVATE_KEY=$CLIENT_PRIVATE_KEY \
python client_node/skills/task-delegator/delegator.py \
  --protocol pancakeswap --amount 0.01 --worker-address $WORKER_ADDRESS
```

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                   OpenClaw Agent                     │
└──────────────────────┬──────────────────────────────┘
                       │ invokes
          ┌────────────▼────────────┐
          │   task-delegator        │  ← 主编排器
          │   (Client Node :8002)   │
          └──┬──────────┬───────────┘
             │          │
    POST /task│          │verify + pay
             ▼          ▼
   ┌──────────────┐  ┌──────────┐  ┌───────────┐
   │ Worker Node  │  │ verifier │  │ bnb-payer │
   │   :8001      │  │ (3-layer)│  │ BSC USDT  │
   │ TEE + ZK     │  └──────────┘  └───────────┘
   └──────────────┘
```

---

## Sub-skills

| 技能 | 路径 | 职责 |
|------|------|------|
| `bsc-defi-scraper` | `worker_node/skills/bsc-defi-scraper/` | 抓取 BSC DeFi TVL 数据 |
| `proof-generator` | `worker_node/skills/proof-generator/` | 生成 ZK + TEE ProofBundle |
| `verifier` | `client_node/skills/verifier/` | 三层验证（ZK · TEE · Binance交叉） |
| `bnb-payer` | `client_node/skills/bnb-payer/` | BSC USDT ERC-20 转账 |
| `task-delegator` | `client_node/skills/task-delegator/` | 端到端编排器 |

---

## Environment Variables

| 变量 | 必填 | 说明 |
|------|------|------|
| `CLIENT_PRIVATE_KEY` | 是 | 付款方私钥（0x...） |
| `WORKER_ADDRESS` | 是 | Worker 收款地址 |
| `WORKER_URL` | 否 | Worker 地址（默认 `http://localhost:8001`） |
| `BSC_RPC` | 否 | BSC RPC（默认 `https://bsc-dataseed.binance.org/`） |
| `BSCSCAN_API_KEY` | 否 | BSCScan API Key（余额查询增强） |

---

## Edge Cases

- **Worker 未启动**：`curl /health` 失败 → 先运行 `docker compose up worker`
- **余额不足**：payer 抛出 `execution reverted` → 检查 USDT 余额和 BNB gas
- **验证失败**：`is_valid: false` → 不执行支付，输出失败原因
- **仅本地测试**：TEE 显示 `mock (local dev)`，ZK 为 `sha256_mock`，属正常行为

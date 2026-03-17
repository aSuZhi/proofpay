# ProofPay

**可验证的 BSC DeFi 数据 + 链上支付协议**

Agent 雇佣 Agent 的 C2C 信任链：Worker 抓取链上数据并生成密码学证明，Client 验证后自动通过 BSC 完成 USDT 结算。

---

## 架构

```
Client Node (8002)          Worker Node (8001)
┌─────────────────┐         ┌─────────────────────┐
│ task-delegator  │──POST──▶│ bsc-defi-scraper    │
│ verifier        │◀──JSON──│ proof-generator     │
│ bnb-payer       │         │  (zkTLS + TEE)      │
└─────────────────┘         └─────────────────────┘
        │
        ▼
   BSC USDT 转账
```

**完整流程：**
1. Client 向 Worker 发送任务请求
2. Worker 从 DefiLlama 抓取 BSC 协议 TVL 数据
3. Worker 生成三层证明（SHA256 数据哈希 + zkTLS + Intel TDX TEE）
4. Client 验证 ProofBundle（哈希校验 + TEE report_data + Binance API 交叉验证）
5. 验证通过 → Client 自动向 Worker 发送 USDT 支付

---

## 快速开始

### 前置条件

| 依赖 | 说明 |
|------|------|
| Docker + Compose | `docker compose version` |
| BSC 钱包 | Client 付款方私钥 + Worker 收款地址 |
| 钱包余额 | ≥ 0.001 BNB（gas）+ 支付金额 USDT |

### 部署

```bash
# 1. 克隆并配置
git clone https://github.com/aSuZhi/proofpay && cd proofpay
cp .env.example .env
# 编辑 .env，填入 CLIENT_PRIVATE_KEY 和 WORKER_ADDRESS

# 2. 启动双节点
docker compose up --build -d

# 3. 验证健康状态
curl http://localhost:8001/health   # Worker
curl http://localhost:8002/health   # Client
```

### 运行完整流程

```bash
curl -X POST http://localhost:8002/delegate \
  -H "Content-Type: application/json" \
  -d '{"protocol": "pancakeswap", "payment_amount": 0.01}'
```

**返回示例：**
```json
{
  "bundle": {
    "protocol": "pancakeswap",
    "tvl_usd": 1234567890.12,
    "proof": { "type": "sha256_mock", "hash": "..." }
  },
  "verify": { "is_valid": true, "layers_passed": 3 },
  "payment": { "txHash": "0x...", "amount_usdt": 0.01 }
}
```

---

## 环境变量

| 变量 | 必填 | 说明 |
|------|------|------|
| `CLIENT_PRIVATE_KEY` | ✅ | Client 付款方 BSC 私钥 |
| `WORKER_ADDRESS` | ✅ | Worker 收款 BSC 地址 |
| `WORKER_PRIVATE_KEY` | ✅ | Worker 节点签名私钥 |
| `BSC_RPC` | 否 | BSC RPC 端点（默认 Binance dataseed）|
| `BSCSCAN_API_KEY` | 否 | BSCScan API Key（余额查询）|
| `WORKER_URL` | 否 | Worker 服务地址（默认 localhost:8001）|

---

## 子技能

| 技能 | 节点 | 功能 |
|------|------|------|
| `bsc-defi-scraper` | Worker | 从 DefiLlama 抓取 BSC 协议 TVL |
| `proof-generator` | Worker | 生成 zkTLS + TEE ProofBundle |
| `verifier` | Client | 三层验证 ProofBundle |
| `bnb-payer` | Client | BSC USDT ERC-20 转账 |
| `task-delegator` | Client | 端到端流程编排 |

---

## 支持的协议

`pancakeswap` · `venus` · `alpaca-finance` · `biswap` · `beefy` · `radiant`

---

## 本地开发（无 Docker）

```bash
# Worker
cd worker_node && pip install -r requirements.txt
python main.py

# Client（新终端）
cd client_node && pip install -r requirements.txt
python main.py
```

> 本地模式下 TEE 自动降级为 `mock_tdx`，证明仍可生成和验证。

---

## License

MIT

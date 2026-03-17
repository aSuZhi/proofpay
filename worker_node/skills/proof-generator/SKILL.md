---
name: proof-generator
description: "Use this skill when the user asks to 'generate proof', 'create ProofBundle', 'add cryptographic attestation', mentions '生成证明', 'zkFetch', 'TEE证明', 'TDX attestation', '密码学证明', or when the Worker needs to attach verifiable credentials to BSC DeFi data in a C2C flow. This skill is the core of BNBTask's trust chain: it ensures data provenance via zkTLS (Reclaim Protocol) and execution environment integrity via Intel TDX TEE attestation. Do NOT use when only raw data is needed (use bsc-defi-scraper) or to verify an existing proof (use verifier)."
license: MIT
metadata:
  author: proofpay
  version: "1.0.0"
  homepage: "https://github.com/aSuZhi/-proofpay"
  openclaw:
    requires:
      bins: ["python"]
      env: ["WORKER_PRIVATE_KEY", "WORKER_ADDRESS"]
---

# SKILL: Proof Generator

> **角色**：BNBTask Worker 侧证明生成技能，为 BSC DeFi 数据提供双层密码学证明。
> **上下游**：调用 `bsc-defi-scraper` → 输出 ProofBundle → 由 Client `verifier` 验证。

---

## Pre-flight Checks

| 检查项 | 要求 |
|--------|------|
| Python 3.10+ | `python --version` |
| dstack-sdk | `pip install dstack-sdk`（TEE 层） |
| Node.js 18+ | `node --version`（zkFetch bridge，可选） |
| WORKER_PRIVATE_KEY | 环境变量（Worker 身份签名） |
| WORKER_ADDRESS | 环境变量（Worker 公钥地址） |
| (可选) TEE 环境 | `/var/run/tappd.sock`（Phala Cloud CVM） |

---

## Skill Routing

当以下条件满足时调用：
- C2C 流程中 `bsc-defi-scraper` 已返回 DataResult，需要附加密码学证明
- Worker FastAPI `POST /task` 内部自动调用
- 用户明确要求生成可验证的 ProofBundle

---

## Command Index

```bash
# 为 PancakeSwap 数据生成 ProofBundle
python {baseDir}/generator.py --protocol pancakeswap

# JSON 输出
python {baseDir}/generator.py --protocol venus --json
```

### 参数说明

| 参数 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `--protocol` | 否 | `pancakeswap` | DefiLlama 协议 slug |
| `--json` | 否 | — | 输出原始 JSON ProofBundle |

---

## Operation Flow

```
Step 1 → 调用 bsc-defi-scraper.fetch_tvl(protocol) → DataResult
Step 2 → Layer 1: Reclaim zkFetch (Node.js subprocess)
         → 成功: zk_proof.type = "reclaim_zkfetch"
         → 失败: zk_proof.type = "sha256_mock"（fallback）
Step 3 → Layer 2: Phala dstack TDX quote
         → TEE 可用: tee_attestation.type = "intel_tdx"
         → 非 TEE:   tee_attestation.type = "mock_tdx"（fallback）
Step 4 → 组装 ProofBundle，返回
```

---

## Input / Output Examples

**Output (ProofBundle):**
```json
{
  "task_id": "bnbt-a1b2c3d4",
  "data": {
    "protocol": "pancakeswap",
    "tvl_usd": 1823456789.0,
    "chain": "bsc",
    "fetched_at": "2026-03-20T10:00:00+00:00",
    "source_url": "https://api.llama.fi/tvl/pancakeswap",
    "data_hash": "a1b2c3..."
  },
  "zk_proof": {
    "type": "reclaim_zkfetch",
    "hash": "a1b2c3d4...",
    "proof": {}
  },
  "tee_attestation": {
    "type": "intel_tdx",
    "report_data": "a1b2c3d4...",
    "quote": "base64..."
  },
  "worker_pubkey": "0xABCD...",
  "timestamp": "2026-03-20T10:00:01+00:00"
}
```

---

## Edge Cases

- **zkFetch 超时**：自动 fallback SHA256 mock，ProofBundle 仍可生成
- **TEE 不可用**（本地开发）：自动 fallback mock_tdx
- **Node.js 不可用**：zkFetch bridge 跳过，直接 SHA256 fallback

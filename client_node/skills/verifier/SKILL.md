---
name: verifier
description: "Use this skill when the user asks to 'verify proof', 'validate ProofBundle', 'check cryptographic attestation', mentions '验证证明', 'verify', 'ProofBundle验证', or when the Client needs to validate a Worker's ProofBundle before releasing payment. Performs 3-layer verification: zkTLS hash, TEE report_data, and Binance API cross-validation. Do NOT use to generate proofs (use proof-generator) or to make payments (use bnb-payer)."
license: MIT
metadata:
  author: proofpay
  version: "1.0.0"
  homepage: "https://github.com/aSuZhi/-proofpay"
  openclaw:
    requires:
      bins: ["python"]
      env: []
---

# SKILL: Verifier

> **角色**：BNBTask Client 侧证明验证技能，对 Worker 返回的 ProofBundle 执行三层验证。
> **上下游**：接收 ProofBundle → 输出 VerifyResult → 触发 `bnb-payer` 支付（验证通过时）。

---

## Pre-flight Checks

| 检查项 | 要求 |
|--------|------|
| Python 3.10+ | `python --version` |
| requests | `pip install requests` |
| Binance API | 公开端点，无需认证 |

---

## Skill Routing

当以下条件满足时调用：
- Client 收到 Worker 的 ProofBundle，需要在支付前验证
- 用户要求验证数据真实性
- `task-delegator` Step 3 自动调用

---

## Command Index

```bash
# 从文件验证
python {baseDir}/verifier.py --file proof_bundle.json

# 从 stdin 验证（管道）
cat proof_bundle.json | python {baseDir}/verifier.py

# JSON 输出
python {baseDir}/verifier.py --file proof_bundle.json --json
```

---

## Operation Flow

```
Step 1 → 读取 ProofBundle（文件或 stdin）
Step 2 → Layer 1: SHA256(data) == zk_proof.hash
Step 3 → Layer 2: SHA256(data) == tee_attestation.report_data
Step 4 → Layer 3: GET https://api.binance.com/api/v3/ticker/price?symbol=BNBUSDT
         → BNB 价格合理性检查（>$10）+ TVL > 0
Step 5 → 返回 VerifyResult {is_valid, zk_valid, tee_valid, cross_validation}
```

---

## Input / Output Examples

**Output (VerifyResult):**
```json
{
  "is_valid": true,
  "zk_valid": true,
  "tee_valid": true,
  "cross_validation": {
    "bnb_price_usd": 612.5,
    "tvl_sane": true,
    "source": "binance_api"
  },
  "computed_hash": "a1b2c3d4...",
  "reason": "All checks passed",
  "task_id": "bnbt-a1b2c3d4"
}
```

---

## Edge Cases

- **Hash 不匹配**：`is_valid: false`，`reason: "Hash mismatch or sanity check failed"`
- **Binance API 不可达**：`cross_validation.tvl_sane: null`，不阻断验证（降级通过）
- **mock_tdx / sha256_mock**：哈希仍可验证，类型字段仅供参考

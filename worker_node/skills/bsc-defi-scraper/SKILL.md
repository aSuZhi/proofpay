---
name: bsc-defi-scraper
description: "Use this skill when the user asks to 'fetch BSC DeFi data', 'get PancakeSwap TVL', 'check Venus TVL', 'scrape BSC protocol data', mentions 'DefiLlama', 'BSC TVL', 'pancakeswap', 'venus', 'alpaca', or when the Worker needs raw on-chain DeFi metrics from BSC protocols. Do NOT use when proof is needed (use proof-generator) or when verifying existing data (use verifier)."
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

# SKILL: BSC DeFi Scraper

> **角色**：BNBTask Worker 侧数据抓取技能，从 DefiLlama 获取 BSC 生态协议 TVL 数据。
> **上下游**：独立运行 → 输出 DataResult → 由 `proof-generator` 包装成 ProofBundle。

---

## Pre-flight Checks

| 检查项 | 要求 |
|--------|------|
| Python 3.10+ | `python --version` |
| requests | `pip install requests` |
| DefiLlama API | 无需认证，公开端点 |
| 网络连通性 | `curl https://api.llama.fi/tvl/pancakeswap` |

---

## Skill Routing

当以下条件满足时调用：
- 用户询问 BSC 协议 TVL（PancakeSwap、Venus、Alpaca Finance、Biswap、Beefy）
- C2C 流程中需要原始数据作为证明输入
- Worker FastAPI `POST /task` 内部自动调用

**不应调用**：需要密码学证明时（路由到 `proof-generator`）；需要验证已有数据时（路由到 `verifier`）。

---

## Command Index

```bash
# 获取 PancakeSwap TVL（默认）
python {baseDir}/scraper.py

# 获取指定协议 TVL
python {baseDir}/scraper.py --protocol venus

# JSON 机器可读输出
python {baseDir}/scraper.py --protocol pancakeswap --json
```

### 参数说明

| 参数 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `--protocol` | 否 | `pancakeswap` | 协议 slug（见支持列表） |
| `--json` | 否 | — | 输出原始 JSON DataResult |

### 支持的 BSC 协议

| slug | 协议名 |
|------|--------|
| `pancakeswap` | PancakeSwap V3 |
| `venus` | Venus Protocol |
| `alpaca-finance` | Alpaca Finance |
| `biswap` | Biswap |
| `beefy` | Beefy Finance |
| `radiant` | Radiant V2 |

---

## Operation Flow

```
Step 1 → 解析 protocol slug（支持别名映射）
Step 2 → GET https://api.llama.fi/tvl/{protocol}
Step 3 → 解析 TVL 数值（float）
Step 4 → 计算 SHA256(DataResult JSON) 作为 data_hash
Step 5 → 返回 DataResult {protocol, tvl_usd, chain, fetched_at, source_url, data_hash}
```

---

## Input / Output Examples

**Input:**
```bash
python scraper.py --protocol pancakeswap --json
```

**Output (DataResult):**
```json
{
  "protocol": "pancakeswap",
  "tvl_usd": 1823456789.0,
  "chain": "bsc",
  "fetched_at": "2026-03-20T10:00:00+00:00",
  "source_url": "https://api.llama.fi/tvl/pancakeswap",
  "data_hash": "a1b2c3d4e5f6..."
}
```

---

## Edge Cases

- **协议不存在**：DefiLlama 返回 404 → 抛出 `HTTPError`，上层捕获
- **网络超时**：10 秒超时 → 抛出 `Timeout`
- **TVL 为 0**：正常返回，由 `verifier` 的 sanity check 标记

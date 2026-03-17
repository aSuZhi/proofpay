# BNBTask Demo Runner
# Usage: .\run_demo.ps1

$ErrorActionPreference = "Stop"

Write-Host "=== BNBTask Demo ===" -ForegroundColor Cyan

# Check .env exists
if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "[!] .env created from .env.example — fill in your keys before running." -ForegroundColor Yellow
    exit 1
}

# Load .env
Get-Content ".env" | ForEach-Object {
    if ($_ -match "^\s*([^#][^=]*)=(.*)$") {
        [System.Environment]::SetEnvironmentVariable($matches[1].Trim(), $matches[2].Trim(), "Process")
    }
}

Write-Host "[1] Starting Worker Node..." -ForegroundColor Green
$worker = Start-Process -FilePath "python" `
    -ArgumentList "worker_node/main.py" `
    -PassThru -NoNewWindow
Start-Sleep -Seconds 2

Write-Host "[2] Health check Worker..." -ForegroundColor Green
try {
    $health = Invoke-RestMethod -Uri "http://localhost:8001/health" -Method Get
    Write-Host "    Worker: $($health.status) | TEE: $($health.tee_type)" -ForegroundColor Green
} catch {
    Write-Host "    Worker not ready: $_" -ForegroundColor Red
    Stop-Process -Id $worker.Id -Force
    exit 1
}

Write-Host "[3] Running scraper (PancakeSwap TVL)..." -ForegroundColor Green
python worker_node/skills/bsc-defi-scraper/scraper.py --protocol pancakeswap

Write-Host "[4] Generating ProofBundle..." -ForegroundColor Green
$bundleJson = python worker_node/skills/proof-generator/generator.py --protocol pancakeswap --json
$bundleJson | Out-File -FilePath "proof_bundle.json" -Encoding utf8
Write-Host "    Saved to proof_bundle.json"

Write-Host "[5] Verifying ProofBundle..." -ForegroundColor Green
Get-Content "proof_bundle.json" | python client_node/skills/verifier/verifier.py

Write-Host "[6] Full delegate flow via API..." -ForegroundColor Green
$client = Start-Process -FilePath "python" `
    -ArgumentList "client_node/main.py" `
    -PassThru -NoNewWindow
Start-Sleep -Seconds 2

try {
    $result = Invoke-RestMethod -Uri "http://localhost:8002/delegate" `
        -Method Post `
        -ContentType "application/json" `
        -Body '{"protocol":"pancakeswap","payment_amount":0.01}'
    Write-Host "    is_valid : $($result.verify.is_valid)" -ForegroundColor Green
    Write-Host "    payment  : $($result.payment | ConvertTo-Json -Compress)"
} catch {
    Write-Host "    Delegate call failed: $_" -ForegroundColor Yellow
}

Write-Host "[7] Cleanup..." -ForegroundColor Green
Stop-Process -Id $worker.Id -Force -ErrorAction SilentlyContinue
Stop-Process -Id $client.Id -Force -ErrorAction SilentlyContinue

Write-Host "=== Demo complete ===" -ForegroundColor Cyan

# QuitCode Sandbox - Windows 構建腳本
# 在 PowerShell 中執行

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ImageName = "quitcode-sandbox"
$ImageTag = "latest"

Write-Host "🐳 Building QuitCode Sandbox Docker Image..." -ForegroundColor Cyan
Write-Host "   Image: ${ImageName}:${ImageTag}" -ForegroundColor Gray
Write-Host ""

# 檢查 Docker 是否可用
try {
    docker version | Out-Null
} catch {
    Write-Host "❌ Docker is not running or not installed!" -ForegroundColor Red
    Write-Host "   Please install Docker Desktop and start it." -ForegroundColor Yellow
    exit 1
}

# 構建 Docker image
Set-Location $ScriptDir
docker build -t "${ImageName}:${ImageTag}" .

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "✅ Build complete!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Test the image:" -ForegroundColor Cyan
    Write-Host '  echo ''{"code": "print(1+1)"}'' | docker run -i --rm quitcode-sandbox:latest' -ForegroundColor Gray
    Write-Host ""
    Write-Host "Test with matplotlib:" -ForegroundColor Cyan
    Write-Host '  $code = @"' -ForegroundColor Gray
    Write-Host '{"code": "import matplotlib.pyplot as plt\nplt.plot([1,2,3])\nprint(\"done\")"}' -ForegroundColor Gray
    Write-Host '"@' -ForegroundColor Gray
    Write-Host '  echo $code | docker run -i --rm quitcode-sandbox:latest' -ForegroundColor Gray
} else {
    Write-Host ""
    Write-Host "❌ Build failed!" -ForegroundColor Red
    exit 1
}

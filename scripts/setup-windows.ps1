param(
    [string]$PngRootDir = "C:\data\company-png",
    [string]$ThumbnailCacheDir = "C:\png-browser-cache",
    [string]$ExportRootDir = "C:\png-browser-exports",
    [string]$BackendPort = "8000",
    [string]$FrontendPort = "5173"
)

$ErrorActionPreference = "Stop"
$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$BackendDir = Join-Path $RepoRoot "backend"
$FrontendDir = Join-Path $RepoRoot "frontend"
$VenvDir = Join-Path $RepoRoot ".venv"

function Require-Command($Name, $InstallHint) {
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "$Name 명령을 찾을 수 없습니다. $InstallHint"
    }
}

Require-Command "python" "Python 3.11 이상을 설치한 뒤 새 PowerShell을 열어주세요."
Require-Command "npm" "Node.js LTS를 설치한 뒤 새 PowerShell을 열어주세요. 예: winget install --id OpenJS.NodeJS.LTS -e"

New-Item -ItemType Directory -Force $PngRootDir | Out-Null
New-Item -ItemType Directory -Force $ThumbnailCacheDir | Out-Null
New-Item -ItemType Directory -Force $ExportRootDir | Out-Null

if (-not (Test-Path $VenvDir)) {
    python -m venv $VenvDir
}

$Python = Join-Path $VenvDir "Scripts\python.exe"
& $Python -m pip install --upgrade pip
& $Python -m pip install -r (Join-Path $RepoRoot "requirements-dev.txt")

Push-Location $FrontendDir
try {
    npm install
} finally {
    Pop-Location
}

$BackendEnv = Join-Path $BackendDir ".env"
$DatabaseUrl = "sqlite:///$((Join-Path $BackendDir 'png_browser.db').Replace('\', '/'))"
$CorsOrigins = "http://localhost:$FrontendPort,http://127.0.0.1:$FrontendPort"

@"
PNG_ROOT_DIR=$PngRootDir
THUMBNAIL_CACHE_DIR=$ThumbnailCacheDir
EXPORT_ROOT_DIR=$ExportRootDir
DATABASE_URL=$DatabaseUrl
SQLITE_BUSY_TIMEOUT_SECONDS=30
SQLITE_JOURNAL_MODE=WAL
SQLITE_SYNCHRONOUS=NORMAL
MAX_EXPORT_ITEMS=5000
AUTO_SCAN_ON_STARTUP=true
PERIODIC_SCAN_INTERVAL_SECONDS=300
ALLOW_SYMLINKS=false
PUBLIC_SHOW_ABSOLUTE_PATH=false
ENABLE_WATCHDOG=false
USE_FTS5=true
SUPPORTED_IMAGE_EXTENSIONS=.png,.jpg,.jpeg,.jpe,.jfif,.bmp,.gif,.tif,.tiff,.webp,.ico,.jp2,.j2k,.tga
AUTH_ENABLED=true
AUTH_USERNAME=admin
AUTH_PASSWORD=admin
AUTH_PASSWORD_HASH=
AUTH_SECRET_KEY=change-this-secret-for-local-dev
CORS_ORIGINS=$CorsOrigins
"@ | Set-Content -Encoding UTF8 $BackendEnv

Write-Host ""
Write-Host "설정 완료"
Write-Host "백엔드 실행:"
Write-Host "  .\.venv\Scripts\activate"
Write-Host "  cd backend"
Write-Host "  uvicorn app.main:app --host 0.0.0.0 --port $BackendPort"
Write-Host ""
Write-Host "프론트엔드 실행:"
Write-Host "  cd frontend"
Write-Host "  npm run dev -- --host 0.0.0.0 --port $FrontendPort"
Write-Host ""
Write-Host "접속: http://localhost:$FrontendPort"
Write-Host "로그인: admin / admin"

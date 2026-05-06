param(
    [string]$PngRootDir = "C:\data\company-png",
    [string]$AppPort = "8080",
    [string]$MinioConsolePort = "9001",
    [string]$LakefsPort = "8001",
    [string]$MinioUser = "minioadmin",
    [string]$MinioPassword = "minioadmin",
    [string]$MinioBucket = "medical-images",
    [string]$LakefsAccessKey = "AKIAIOSFODNN7EXAMPLE",
    [string]$LakefsSecretKey = "lakefs-local-secret"
)

$ErrorActionPreference = "Stop"
$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$EnvPath = Join-Path $RepoRoot ".env"

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw "Docker CLI was not found. Install Docker Desktop, start it, then run this script again."
}

New-Item -ItemType Directory -Force $PngRootDir | Out-Null
$HostPngRootDir = (Resolve-Path $PngRootDir).Path.Replace("\", "/")

if (Test-Path $EnvPath) {
    $BackupPath = "$EnvPath.backup-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
    Copy-Item -LiteralPath $EnvPath -Destination $BackupPath
    Write-Host "Existing .env backed up to $BackupPath"
}

@"
APP_PORT=$AppPort
HOST_PNG_ROOT_DIR=$HostPngRootDir
PNG_ROOT_DIR=/data/company-png
THUMBNAIL_CACHE_DIR=/var/cache/png-browser-thumbnails
EXPORT_ROOT_DIR=/var/lib/png-browser/exports
EXPORT_STORAGE_BACKEND=object
OBJECT_STORAGE_ENDPOINT_URL=http://minio:9000
OBJECT_STORAGE_ACCESS_KEY_ID=$MinioUser
OBJECT_STORAGE_SECRET_ACCESS_KEY=$MinioPassword
OBJECT_STORAGE_REGION=us-east-1
OBJECT_STORAGE_BUCKET=$MinioBucket
OBJECT_STORAGE_PREFIX=exports
OBJECT_STORAGE_FORCE_PATH_STYLE=true
OBJECT_STORAGE_ALLOW_REMOTE_ENDPOINT=false
MINIO_ROOT_USER=$MinioUser
MINIO_ROOT_PASSWORD=$MinioPassword
MINIO_BUCKET=$MinioBucket
MINIO_CONSOLE_PORT=$MinioConsolePort
LAKEFS_PORT=$LakefsPort
LAKEFS_AUTH_ENCRYPT_SECRET_KEY=local-lakefs-change-me
LAKEFS_BLOCKSTORE_SIGNING_SECRET_KEY=local-lakefs-signing-change-me
LAKEFS_INSTALLATION_USER_NAME=admin
LAKEFS_INSTALLATION_ACCESS_KEY_ID=$LakefsAccessKey
LAKEFS_INSTALLATION_SECRET_ACCESS_KEY=$LakefsSecretKey
DATABASE_URL=sqlite:////var/lib/png-browser/app.db
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
AUTH_SECRET_KEY=change-this-secret-for-local-docker
CORS_ORIGINS=http://localhost:5173,http://localhost:$AppPort,http://127.0.0.1:$AppPort
"@ | Set-Content -Encoding UTF8 $EnvPath

Push-Location $RepoRoot
try {
    docker compose up -d --build
} finally {
    Pop-Location
}

Write-Host ""
Write-Host "Local stack is starting."
Write-Host "App:          http://localhost:$AppPort"
Write-Host "MinIO API:    http://localhost:9000"
Write-Host "MinIO Console:http://localhost:$MinioConsolePort"
Write-Host "lakeFS UI:    http://localhost:$LakefsPort"
Write-Host ""
Write-Host "App login:    admin / admin"
Write-Host "MinIO login:  $MinioUser / $MinioPassword"
Write-Host "lakeFS login: $LakefsAccessKey / $LakefsSecretKey"

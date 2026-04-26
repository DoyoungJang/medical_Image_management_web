#!/usr/bin/env bash
set -euo pipefail

PNG_ROOT_DIR="${PNG_ROOT_DIR:-/data/company-png}"
THUMBNAIL_CACHE_DIR="${THUMBNAIL_CACHE_DIR:-/var/cache/png-browser-thumbnails}"
EXPORT_ROOT_DIR="${EXPORT_ROOT_DIR:-/var/lib/png-browser/exports}"
DATABASE_PATH="${DATABASE_PATH:-/var/lib/png-browser/app.db}"
BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
BACKEND_DIR="${REPO_ROOT}/backend"
FRONTEND_DIR="${REPO_ROOT}/frontend"
VENV_DIR="${REPO_ROOT}/.venv"

need_command() {
  local name="$1"
  if ! command -v "${name}" >/dev/null 2>&1; then
    return 1
  fi
}

if ! need_command python3 || ! need_command npm; then
  if ! need_command sudo; then
    echo "python3/npm 설치가 필요하지만 sudo 명령을 찾을 수 없습니다." >&2
    exit 1
  fi
  sudo apt-get update
  sudo apt-get install -y python3 python3-venv python3-pip nodejs npm
fi

sudo mkdir -p "${PNG_ROOT_DIR}" "${THUMBNAIL_CACHE_DIR}" "$(dirname "${DATABASE_PATH}")" "${EXPORT_ROOT_DIR}"
sudo chown -R "$(id -u):$(id -g)" "${PNG_ROOT_DIR}" "${THUMBNAIL_CACHE_DIR}" "$(dirname "${DATABASE_PATH}")" "${EXPORT_ROOT_DIR}"

if [ ! -d "${VENV_DIR}" ]; then
  python3 -m venv "${VENV_DIR}"
fi

"${VENV_DIR}/bin/python" -m pip install --upgrade pip
"${VENV_DIR}/bin/python" -m pip install -r "${REPO_ROOT}/requirements-dev.txt"

(cd "${FRONTEND_DIR}" && npm install)

cat > "${BACKEND_DIR}/.env" <<EOF
PNG_ROOT_DIR=${PNG_ROOT_DIR}
THUMBNAIL_CACHE_DIR=${THUMBNAIL_CACHE_DIR}
EXPORT_ROOT_DIR=${EXPORT_ROOT_DIR}
DATABASE_URL=sqlite:///${DATABASE_PATH}
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
CORS_ORIGINS=http://localhost:${FRONTEND_PORT},http://127.0.0.1:${FRONTEND_PORT}
EOF

cat <<EOF

설정 완료

백엔드 실행:
  source .venv/bin/activate
  cd backend
  uvicorn app.main:app --host 0.0.0.0 --port ${BACKEND_PORT}

프론트엔드 실행:
  cd frontend
  npm run dev -- --host 0.0.0.0 --port ${FRONTEND_PORT}

접속: http://localhost:${FRONTEND_PORT}
로그인: admin / admin
EOF

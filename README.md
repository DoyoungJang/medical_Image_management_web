# PNG Browser

사내 Ubuntu 서버에 저장된 PNG 파일을 안전하게 탐색하기 위한 내부 웹 애플리케이션입니다.

이 프로젝트는 다음 기능을 제공합니다.

- `PNG_ROOT_DIR` 아래의 폴더 트리 탐색
- PNG 썸네일과 원본 미리보기
- PNG 메타데이터 추출 및 검색
- 텍스트 메타데이터(`tEXt`, `zTXt`, `iTXt`) 인덱싱
- 관리자 재스캔과 인덱스 상태 확인
- 경로 순회 방지, symlink escape 방지, read-only 원본 보호

## 1. Stack

- Backend: Python 3.11+, FastAPI, SQLAlchemy, SQLite
- Frontend: React + TypeScript + Vite
- Image handling: Pillow
- Optional watcher: watchdog
- Deployment: Docker Compose + Nginx reverse proxy
- Tests: pytest, Vitest

## 2. Main Features

- Folder tree browser rooted at `PNG_ROOT_DIR`
- Relative-path-only exposure to the frontend
- Lazy thumbnail generation and caching in `THUMBNAIL_CACHE_DIR`
- Safe original file streaming through backend endpoints
- SQLite metadata index with optional FTS5 full-text search
- Structured filters by path, size, dimensions, alpha, status, metadata key/value
- App-level authentication for protected and admin endpoints

## 3. Project Structure

```text
.
├─ backend/
│  ├─ app/
│  │  ├─ api/
│  │  ├─ core/
│  │  ├─ services/
│  │  ├─ container.py
│  │  ├─ db.py
│  │  ├─ dependencies.py
│  │  ├─ main.py
│  │  ├─ models.py
│  │  └─ schemas.py
│  ├─ tests/
│  ├─ Dockerfile
│  └─ pyproject.toml
├─ frontend/
│  ├─ src/
│  │  ├─ components/
│  │  ├─ hooks/
│  │  ├─ types/
│  │  └─ utils/
│  ├─ Dockerfile
│  ├─ nginx.conf
│  └─ package.json
├─ deployment/
│  └─ nginx/
│     └─ default.conf
├─ .env.example
├─ docker-compose.yml
└─ README.md
```

## 4. Environment Variables

`.env.example`를 복사해서 `.env`를 만들고 값을 채워 주세요.

| Variable | Description |
|---|---|
| `APP_PORT` | 외부에서 접속할 포트 |
| `PNG_ROOT_DIR` | 원본 PNG 루트 디렉터리 |
| `THUMBNAIL_CACHE_DIR` | 썸네일 캐시 디렉터리 |
| `DATABASE_URL` | SQLite 데이터베이스 경로 |
| `AUTO_SCAN_ON_STARTUP` | 서버 시작 시 자동 스캔 여부 |
| `ALLOW_SYMLINKS` | symlink 추적 허용 여부, 기본 `false` |
| `PUBLIC_SHOW_ABSOLUTE_PATH` | UI에 절대 경로 표시 여부 |
| `ENABLE_WATCHDOG` | watchdog 기반 자동 감시 여부 |
| `USE_FTS5` | SQLite FTS5 사용 여부 |
| `AUTH_ENABLED` | 앱 로그인 사용 여부 |
| `AUTH_USERNAME` | 로그인 사용자명 |
| `AUTH_PASSWORD_HASH` | bcrypt 비밀번호 해시 |
| `AUTH_SECRET_KEY` | 세션 서명 키 |
| `CORS_ORIGINS` | 허용할 Origin 목록 |

예시:

```env
APP_PORT=8080
PNG_ROOT_DIR=/data/company-png
THUMBNAIL_CACHE_DIR=/var/cache/png-browser-thumbnails
DATABASE_URL=sqlite:////var/lib/png-browser/app.db
AUTO_SCAN_ON_STARTUP=true
ALLOW_SYMLINKS=false
PUBLIC_SHOW_ABSOLUTE_PATH=false
ENABLE_WATCHDOG=false
USE_FTS5=true
AUTH_ENABLED=true
AUTH_USERNAME=admin
AUTH_PASSWORD_HASH=$2b$12$replace.this.with.a.real.bcrypt.hash
AUTH_SECRET_KEY=change-this-secret-for-production
CORS_ORIGINS=http://localhost:5173,http://<SERVER_IP>:8080
```

## 5. Password Hash

### Ubuntu / Linux / macOS

```bash
python3 - <<'PY'
import bcrypt
print(bcrypt.hashpw(b"change-me", bcrypt.gensalt()).decode())
PY
```

### Windows PowerShell

```powershell
@'
import bcrypt
print(bcrypt.hashpw(b"change-me", bcrypt.gensalt()).decode())
'@ | python -
```

## 6. Windows Installation and Usage

이 섹션은 Windows PC에서 로컬 개발 또는 사내 테스트용으로 실행하는 방법입니다.

### 6.1 Prerequisites

다음을 먼저 설치해 주세요.

- Python 3.11+
- Node.js 20+
- Git

권장 확인 명령:

```powershell
python --version
node --version
npm --version
git --version
```

### 6.2 Clone Repository

```powershell
git clone <YOUR_REPOSITORY_URL> medical_Image_management_web
cd medical_Image_management_web
```

### 6.3 Prepare PNG Source Directory

예를 들어 아래처럼 PNG 루트를 준비합니다.

```powershell
New-Item -ItemType Directory -Force C:\data\company-png
New-Item -ItemType Directory -Force C:\png-browser-cache
```

원본 PNG 파일은 `C:\data\company-png` 아래에 넣습니다.

### 6.4 Backend Setup on Windows

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -e .[dev]
```

환경 변수 설정:

```powershell
$env:PNG_ROOT_DIR="C:\data\company-png"
$env:THUMBNAIL_CACHE_DIR="C:\png-browser-cache"
$env:DATABASE_URL="sqlite:///./png_browser.db"
$env:AUTO_SCAN_ON_STARTUP="true"
$env:ALLOW_SYMLINKS="false"
$env:PUBLIC_SHOW_ABSOLUTE_PATH="false"
$env:AUTH_ENABLED="true"
$env:AUTH_USERNAME="admin"
$env:AUTH_PASSWORD_HASH="<bcrypt_hash>"
$env:AUTH_SECRET_KEY="change-this-secret"
$env:CORS_ORIGINS="http://localhost:5173"
```

서버 실행:

```powershell
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

헬스체크:

```powershell
Invoke-RestMethod http://localhost:8000/api/health
```

### 6.5 Frontend Setup on Windows

새 터미널에서 실행:

```powershell
cd frontend
npm install
npm run dev -- --host 0.0.0.0 --port 5173
```

브라우저 접속:

```text
http://localhost:5173
```

### 6.6 How to Use on Windows

1. 로그인 화면에서 `AUTH_USERNAME` 계정으로 로그인합니다.
2. 좌측 폴더 트리에서 원하는 폴더를 선택합니다.
3. 가운데 검색 영역에서 파일명, 경로, 메타데이터를 검색합니다.
4. 썸네일 카드를 클릭하면 우측 상세 패널에서 큰 미리보기와 전체 메타데이터를 볼 수 있습니다.
5. 우측 관리자 패널에서 인덱스 상태를 확인하고 `재스캔`을 눌러 다시 스캔할 수 있습니다.

### 6.7 Run Tests on Windows

백엔드 테스트:

```powershell
cd backend
.\.venv\Scripts\activate
pytest
```

프런트엔드 테스트:

```powershell
cd frontend
npm run test
npm run build
```

## 7. Ubuntu Installation and Usage

이 섹션은 Ubuntu 서버 또는 Ubuntu 개발 머신에서 실행하는 방법입니다.

### 7.1 Prerequisites

```bash
sudo apt-get update
sudo apt-get install -y python3 python3-venv python3-pip nodejs npm git
```

버전 확인:

```bash
python3 --version
node --version
npm --version
git --version
```

Node.js 최신 LTS가 필요하다면 사내 표준 저장소 또는 NodeSource 방식으로 20.x를 설치하세요.

### 7.2 Clone Repository

```bash
git clone <YOUR_REPOSITORY_URL> png-browser
cd png-browser
```

### 7.3 Prepare Directories

```bash
sudo mkdir -p /data/company-png
sudo mkdir -p /var/cache/png-browser-thumbnails
sudo chown -R $USER:$USER /data/company-png /var/cache/png-browser-thumbnails
```

원본 PNG 파일은 `/data/company-png` 아래에 복사합니다.

### 7.4 Backend Setup on Ubuntu

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .[dev]
```

환경 변수 설정:

```bash
export PNG_ROOT_DIR=/data/company-png
export THUMBNAIL_CACHE_DIR=/var/cache/png-browser-thumbnails
export DATABASE_URL=sqlite:////var/lib/png-browser/app.db
export AUTO_SCAN_ON_STARTUP=true
export ALLOW_SYMLINKS=false
export PUBLIC_SHOW_ABSOLUTE_PATH=false
export AUTH_ENABLED=true
export AUTH_USERNAME=admin
export AUTH_PASSWORD_HASH='<bcrypt_hash>'
export AUTH_SECRET_KEY='change-this-secret'
export CORS_ORIGINS=http://localhost:5173,http://<SERVER_IP>:8080
```

SQLite 위치 준비:

```bash
sudo mkdir -p /var/lib/png-browser
sudo chown -R $USER:$USER /var/lib/png-browser
```

서버 실행:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

헬스체크:

```bash
curl http://localhost:8000/api/health
```

### 7.5 Frontend Setup on Ubuntu

새 터미널에서 실행:

```bash
cd frontend
npm install
npm run dev -- --host 0.0.0.0 --port 5173
```

브라우저 접속:

```text
http://localhost:5173
```

### 7.6 How to Use on Ubuntu

1. 브라우저에서 로그인합니다.
2. 자동 스캔이 켜져 있으면 시작 시 인덱싱이 진행됩니다.
3. 자동 스캔이 꺼져 있으면 관리자 패널의 `재스캔` 버튼으로 수동 스캔합니다.
4. 검색창에 파일명, 상대 경로, 메타데이터 값을 입력해 결과를 찾습니다.
5. 조건 필터로 해상도, 파일 크기, alpha 여부, 상태를 조합합니다.
6. 상세 패널에서 원본 이미지 열기와 메타데이터 검토를 진행합니다.

### 7.7 Run Tests on Ubuntu

백엔드 테스트:

```bash
cd backend
source .venv/bin/activate
pytest
```

프런트엔드 테스트:

```bash
cd frontend
npm run test
npm run build
```

## 8. Docker Compose Deployment on Ubuntu

운영 서버에서는 Docker Compose 방식이 가장 간단합니다.

### 8.1 Install Docker

```bash
sudo apt-get update
sudo apt-get install -y docker.io docker-compose-plugin ufw
sudo systemctl enable --now docker
```

### 8.2 Prepare Project

```bash
git clone <YOUR_REPOSITORY_URL> png-browser
cd png-browser
cp .env.example .env
```

`.env`를 열어서 다음 값을 실제 서버 기준으로 수정합니다.

- `PNG_ROOT_DIR=/data/company-png`
- `THUMBNAIL_CACHE_DIR=/var/cache/png-browser-thumbnails`
- `DATABASE_URL=sqlite:////var/lib/png-browser/app.db`
- `AUTH_USERNAME=admin`
- `AUTH_PASSWORD_HASH=<real bcrypt hash>`
- `AUTH_SECRET_KEY=<long random string>`
- `APP_PORT=8080`

### 8.3 Start Services

```bash
docker compose build
docker compose up -d
docker compose ps
```

브라우저 접속:

```text
http://<SERVER_IP>:8080
```

### 8.4 UFW / Firewall

```bash
sudo ufw allow 22/tcp
sudo ufw allow 8080/tcp
sudo ufw enable
sudo ufw status
```

포트를 변경했다면 `8080` 대신 `APP_PORT` 값을 허용하세요.

## 9. Daily Usage Guide

### 9.1 Initial Scan

자동 스캔:

```bash
AUTO_SCAN_ON_STARTUP=true
```

수동 재스캔:

```bash
curl -X POST http://localhost:8000/api/admin/rescan
```

실제 보호 환경에서는 로그인 세션이 필요합니다.

### 9.2 Search Examples

- 파일명 검색: `report`
- 경로 검색: `team-a/project-x`
- 메타데이터 값 검색: `scanner`
- 메타데이터 키 필터: `textual_metadata.Author`
- 상태 필터: `corrupted`

### 9.3 Safe Access Rules

- 프런트엔드는 절대 경로를 직접 보내지 않습니다.
- 파일 접근은 `image_id` 또는 검증된 상대 경로만 사용합니다.
- `../`, 절대 경로, encoded traversal, symlink escape는 차단됩니다.
- 원본 PNG는 수정하지 않고 읽기 전용으로 취급합니다.

## 10. API Summary

- `GET /api/health`
- `GET /api/config/public`
- `GET /api/tree`
- `GET /api/images`
- `GET /api/images/{image_id}`
- `GET /api/images/{image_id}/thumbnail`
- `GET /api/images/{image_id}/file`
- `GET /api/metadata/keys`
- `GET /api/metadata/facets`
- `POST /api/admin/rescan`
- `GET /api/admin/index-status`
- `GET /api/auth/session`
- `POST /api/auth/login`
- `POST /api/auth/logout`

## 11. Architecture Notes

- `FileSystemService`: 루트 경계 검증, 상대 경로 정규화, 안전한 PNG 탐색
- `MetadataExtractor`: Pillow 기반 메타데이터 추출
- `PNGChunkParser`: PNG textual chunk 안전 파싱
- `IndexService`: 전체 스캔, 증분 재인덱싱, missing 처리
- `SearchService`: 목록 조회, 필터, facet, FTS
- `ThumbnailService`: 썸네일 생성과 캐시
- `AuthService`: bcrypt 기반 인증과 세션 쿠키

## 12. Database Backup

컨테이너 내부 SQLite 파일 백업:

```bash
docker compose exec backend sh -lc 'cp /var/lib/png-browser/app.db /var/lib/png-browser/app-$(date +%F-%H%M%S).db'
```

호스트로 복사:

```bash
docker compose cp backend:/var/lib/png-browser/app.db ./app.db.backup
```

## 13. Troubleshooting

- `PNG_ROOT_DIR does not exist`
  - 지정한 디렉터리가 실제로 존재하는지 확인하세요.
- 썸네일이 보이지 않음
  - `THUMBNAIL_CACHE_DIR` 쓰기 권한과 PNG 읽기 권한을 확인하세요.
- 검색 결과가 없음
  - 초기 스캔이 완료되었는지, `재스캔`이 성공했는지 확인하세요.
- 재스캔이 `409` 반환
  - 이미 스캔이 진행 중이거나 너무 짧은 간격으로 요청한 상태입니다.
- 절대 경로가 보이지 않음
  - `PUBLIC_SHOW_ABSOLUTE_PATH=true`를 명시적으로 설정해야 합니다.
- Windows에서 `node` 또는 `npm` 인식 안 됨
  - Node.js 설치 후 새 PowerShell을 다시 열어 주세요.
- Ubuntu에서 `Permission denied`
  - PNG 루트, 썸네일 캐시, DB 디렉터리 권한을 확인하세요.

## 14. Known Limitations

- 디렉터리 필터는 현재 선택한 폴더 이하 subtree 기준입니다.
- 메타데이터 값 비교는 MVP 기준으로 `contains` 중심입니다.
- 매우 큰 데이터셋에서는 PostgreSQL 마이그레이션을 권장합니다.

## 15. PostgreSQL Migration Note

대용량 환경에서는 SQLite 대신 PostgreSQL 전환을 권장합니다.

- `DATABASE_URL`을 PostgreSQL DSN으로 변경
- SQLAlchemy 모델은 대부분 그대로 재사용 가능
- FTS는 PostgreSQL `GIN + tsvector` 또는 전용 검색 인덱스로 교체
- 썸네일 캐시 구조는 그대로 유지 가능

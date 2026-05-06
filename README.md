# 이미지 탐색기 설치 가이드

사내 서버 또는 개발 PC에서 이미지 탐색기를 설치하고 실행하는 방법입니다. PNG, JPG/JPEG, BMP, GIF, TIFF, WEBP 등 일반 이미지 파일을 지원합니다. 실제 화면 사용법은 [USAGE.md](./USAGE.md)를 참고하세요.

## 1. Windows 설치

### 1.0 자동 설치 스크립트

PowerShell을 관리자 권한이 아닌 일반 권한으로 열고 저장소 루트에서 실행합니다.

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\scripts\setup-windows.ps1
```

기본값으로 `C:\data\company-png`, `C:\png-browser-cache`, `C:\png-browser-exports`를 만들고 백엔드/프런트엔드 의존성을 설치합니다. 설치 후 스크립트가 출력하는 백엔드와 프런트엔드 실행 명령을 각각 새 PowerShell에서 실행하면 됩니다.

### 1.1 사전 준비

Windows PowerShell에서 아래 명령으로 필수 도구가 설치되어 있는지 확인합니다.

```powershell
python --version
node --version
npm --version
git --version
```

필요 버전은 다음과 같습니다.

- Python 3.11 이상
- Node.js 20 이상
- Git

`node` 또는 `npm` 명령이 인식되지 않으면 Node.js LTS를 먼저 설치합니다.

```powershell
winget install --id OpenJS.NodeJS.LTS -e
```

설치가 끝나면 PowerShell을 완전히 닫고 새 PowerShell을 연 뒤 다시 확인합니다.

```powershell
node --version
npm --version
```

`winget`을 사용할 수 없는 PC에서는 Node.js 공식 설치 파일의 LTS 버전을 설치한 뒤 새 PowerShell을 열어 확인합니다.

### 1.2 저장소 받기

```powershell
git clone <YOUR_REPOSITORY_URL> medical_Image_management_web
cd medical_Image_management_web
```

### 1.3 이미지 원본 디렉터리 준비

```powershell
New-Item -ItemType Directory -Force C:\data\company-png
New-Item -ItemType Directory -Force C:\png-browser-cache
New-Item -ItemType Directory -Force C:\png-browser-exports
```

원본 이미지 파일은 `C:\data\company-png` 아래에 넣습니다. 기본 지원 확장자는 `.png`, `.jpg`, `.jpeg`, `.bmp`입니다. 애플리케이션은 이 디렉터리 밖의 파일을 탐색하지 않습니다.

초기 실행 후 관리자 화면에서도 이미지 루트 경로와 서버 저장 경로를 변경할 수 있습니다. 관리자 화면에서 변경한 경로는 SQLite DB에 저장되어 재시작 후에도 유지됩니다.

### 1.4 백엔드 설치

```powershell
python -m venv .venv
.\.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
```

위 명령은 저장소 루트에서 실행합니다. 루트의 `requirements-dev.txt`가 백엔드 개발 의존성을 함께 설치합니다.

`python -m pip install -e .[dev]`는 저장소 루트에서 실행하지 않습니다. 루트 설치는 위의 `requirements-dev.txt` 방식을 사용하세요.

editable install이 꼭 필요하면 백엔드 디렉터리에서 아래처럼 따옴표를 붙여 실행하세요.

```powershell
cd backend
python -m pip install -e ".[dev]"
cd ..
```

### 1.5 Windows 환경 변수 설정

아래 값은 현재 PowerShell 창에만 적용됩니다.

```powershell
$env:PNG_ROOT_DIR="C:\data\company-png"
$env:THUMBNAIL_CACHE_DIR="C:\png-browser-cache"
$env:EXPORT_ROOT_DIR="C:\png-browser-exports"
$env:EXPORT_STORAGE_BACKEND="object"
$env:OBJECT_STORAGE_ENDPOINT_URL="http://localhost:9000"
$env:OBJECT_STORAGE_ACCESS_KEY_ID="minioadmin"
$env:OBJECT_STORAGE_SECRET_ACCESS_KEY="minioadmin"
$env:OBJECT_STORAGE_REGION="us-east-1"
$env:OBJECT_STORAGE_BUCKET="medical-images"
$env:OBJECT_STORAGE_PREFIX="exports"
$env:OBJECT_STORAGE_FORCE_PATH_STYLE="true"
$env:OBJECT_STORAGE_ALLOW_REMOTE_ENDPOINT="false"
$env:DATABASE_URL="sqlite:///./png_browser.db"
$env:SQLITE_BUSY_TIMEOUT_SECONDS="30"
$env:SQLITE_JOURNAL_MODE="WAL"
$env:SQLITE_SYNCHRONOUS="NORMAL"
$env:MAX_EXPORT_ITEMS="5000"
$env:AUTO_SCAN_ON_STARTUP="true"
$env:PERIODIC_SCAN_INTERVAL_SECONDS="300"
$env:ALLOW_SYMLINKS="false"
$env:PUBLIC_SHOW_ABSOLUTE_PATH="false"
$env:SUPPORTED_IMAGE_EXTENSIONS=".png,.jpg,.jpeg,.jpe,.jfif,.bmp,.gif,.tif,.tiff,.webp,.ico,.jp2,.j2k,.tga"
$env:AUTH_ENABLED="true"
$env:AUTH_USERNAME="admin"
$env:AUTH_PASSWORD="admin"
$env:AUTH_PASSWORD_HASH=""
$env:AUTH_SECRET_KEY="change-this-secret"
$env:CORS_ORIGINS="http://localhost:5173"
```

### 1.6 Windows 백엔드 실행

```powershell
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

헬스체크:

```powershell
Invoke-RestMethod http://localhost:8000/api/health
```

### 1.7 Windows 프런트엔드 실행

새 PowerShell 창에서 실행합니다.

```powershell
cd frontend
npm install
npm run dev -- --host 0.0.0.0 --port 5173
```

접속 주소:

```text
http://localhost:5173
```

## 2. Ubuntu 설치

### 2.0 자동 설치 스크립트

저장소 루트에서 실행합니다.

```bash
bash scripts/setup-ubuntu.sh
```

기본값으로 `/data/company-png`, `/var/cache/png-browser-thumbnails`, `/var/lib/png-browser/exports`, `/var/lib/png-browser/app.db`를 준비하고 의존성을 설치합니다. 설치 후 스크립트가 출력하는 백엔드와 프런트엔드 실행 명령을 각각 실행하세요.

### 2.1 사전 준비

```bash
sudo apt-get update
sudo apt-get install -y python3 python3-venv python3-pip nodejs npm git
```

버전을 확인합니다.

```bash
python3 --version
node --version
npm --version
git --version
```

Node.js 20 이상이 필요합니다. Ubuntu 기본 저장소의 Node.js 버전이 낮으면 사내 표준 저장소 또는 NodeSource 방식으로 Node.js 20 이상을 설치하세요.

### 2.2 저장소 받기

```bash
git clone <YOUR_REPOSITORY_URL> png-browser
cd png-browser
```

### 2.3 이미지 원본 및 캐시 디렉터리 준비

```bash
sudo mkdir -p /data/company-png
sudo mkdir -p /var/cache/png-browser-thumbnails
sudo mkdir -p /var/lib/png-browser
sudo chown -R $USER:$USER /data/company-png /var/cache/png-browser-thumbnails /var/lib/png-browser
```

원본 이미지 파일은 `/data/company-png` 아래에 복사합니다. 기본 지원 확장자는 `.png`, `.jpg`, `.jpeg`, `.bmp`입니다.

### 2.4 백엔드 설치

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
```

위 명령은 저장소 루트에서 실행합니다. 루트의 `requirements-dev.txt`가 백엔드 개발 의존성을 함께 설치합니다.

editable install이 필요한 경우에는 백엔드 디렉터리에서 아래 명령을 사용하세요.

```bash
cd backend
python -m pip install -e ".[dev]"
cd ..
```

### 2.5 Ubuntu 환경 변수 설정

```bash
export PNG_ROOT_DIR=/data/company-png
export THUMBNAIL_CACHE_DIR=/var/cache/png-browser-thumbnails
export EXPORT_ROOT_DIR=/var/lib/png-browser/exports
export EXPORT_STORAGE_BACKEND=object
export OBJECT_STORAGE_ENDPOINT_URL=http://localhost:9000
export OBJECT_STORAGE_ACCESS_KEY_ID=minioadmin
export OBJECT_STORAGE_SECRET_ACCESS_KEY=minioadmin
export OBJECT_STORAGE_REGION=us-east-1
export OBJECT_STORAGE_BUCKET=medical-images
export OBJECT_STORAGE_PREFIX=exports
export OBJECT_STORAGE_FORCE_PATH_STYLE=true
export OBJECT_STORAGE_ALLOW_REMOTE_ENDPOINT=false
export DATABASE_URL=sqlite:////var/lib/png-browser/app.db
export SQLITE_BUSY_TIMEOUT_SECONDS=30
export SQLITE_JOURNAL_MODE=WAL
export SQLITE_SYNCHRONOUS=NORMAL
export MAX_EXPORT_ITEMS=5000
export AUTO_SCAN_ON_STARTUP=true
export PERIODIC_SCAN_INTERVAL_SECONDS=300
export ALLOW_SYMLINKS=false
export PUBLIC_SHOW_ABSOLUTE_PATH=false
export SUPPORTED_IMAGE_EXTENSIONS=.png,.jpg,.jpeg,.jpe,.jfif,.bmp,.gif,.tif,.tiff,.webp,.ico,.jp2,.j2k,.tga
export AUTH_ENABLED=true
export AUTH_USERNAME=admin
export AUTH_PASSWORD=admin
export AUTH_PASSWORD_HASH=
export AUTH_SECRET_KEY='change-this-secret'
export CORS_ORIGINS=http://localhost:5173,http://<SERVER_IP>:8080
```

### 2.6 Ubuntu 백엔드 실행

```bash
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

헬스체크:

```bash
curl http://localhost:8000/api/health
```

### 2.7 Ubuntu 프런트엔드 실행

새 터미널에서 실행합니다.

```bash
cd frontend
npm install
npm run dev -- --host 0.0.0.0 --port 5173
```

접속 주소:

```text
http://localhost:5173
```

## 3. Ubuntu Docker Compose 배포

운영 서버에서는 Docker Compose 방식을 권장합니다.

### 3.1 Docker 설치

```bash
sudo apt-get update
sudo apt-get install -y docker.io docker-compose-plugin ufw
sudo systemctl enable --now docker
```

### 3.2 프로젝트 준비

```bash
git clone <YOUR_REPOSITORY_URL> png-browser
cd png-browser
cp .env.example .env
```

`.env`에서 최소한 아래 값을 실제 환경에 맞게 수정합니다.

```env
APP_PORT=8080
PNG_ROOT_DIR=/data/company-png
THUMBNAIL_CACHE_DIR=/var/cache/png-browser-thumbnails
EXPORT_ROOT_DIR=/var/lib/png-browser/exports
EXPORT_STORAGE_BACKEND=object
OBJECT_STORAGE_ENDPOINT_URL=http://minio:9000
OBJECT_STORAGE_ACCESS_KEY_ID=minioadmin
OBJECT_STORAGE_SECRET_ACCESS_KEY=minioadmin
OBJECT_STORAGE_REGION=us-east-1
OBJECT_STORAGE_BUCKET=medical-images
OBJECT_STORAGE_PREFIX=exports
OBJECT_STORAGE_FORCE_PATH_STYLE=true
OBJECT_STORAGE_ALLOW_REMOTE_ENDPOINT=false
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=minioadmin
MINIO_BUCKET=medical-images
MINIO_CONSOLE_PORT=9001
LAKEFS_PORT=8001
LAKEFS_AUTH_ENCRYPT_SECRET_KEY=local-lakefs-change-me
DATABASE_URL=sqlite:////var/lib/png-browser/app.db
SQLITE_BUSY_TIMEOUT_SECONDS=30
SQLITE_JOURNAL_MODE=WAL
SQLITE_SYNCHRONOUS=NORMAL
MAX_EXPORT_ITEMS=5000
AUTO_SCAN_ON_STARTUP=true
PERIODIC_SCAN_INTERVAL_SECONDS=300
ALLOW_SYMLINKS=false
PUBLIC_SHOW_ABSOLUTE_PATH=false
SUPPORTED_IMAGE_EXTENSIONS=.png,.jpg,.jpeg,.jpe,.jfif,.bmp,.gif,.tif,.tiff,.webp,.ico,.jp2,.j2k,.tga
AUTH_ENABLED=true
AUTH_USERNAME=admin
AUTH_PASSWORD=admin
AUTH_PASSWORD_HASH=
AUTH_SECRET_KEY=<long-random-secret>
CORS_ORIGINS=http://<SERVER_IP>:8080
```

### 3.3 서비스 시작

로컬 서버에서 앱, MinIO, lakeFS를 한 번에 설치/구동하려면 아래 스크립트를 사용합니다. 스크립트는 루트 `.env`를 로컬 Docker용으로 생성하고 기존 `.env`가 있으면 백업한 뒤 `docker compose up -d --build`를 실행합니다.

Windows PowerShell:

```powershell
.\scripts\start-local-stack.ps1
```

Ubuntu/macOS:

```bash
bash scripts/start-local-stack.sh
```

기본 접속 주소:

```text
앱: http://localhost:8080
MinIO API: http://localhost:9000
MinIO Console: http://localhost:9001
lakeFS UI: http://localhost:8001
```

기본 계정:

```text
앱: admin / admin
MinIO: minioadmin / minioadmin
lakeFS: AKIAIOSFODNN7EXAMPLE / lakefs-local-secret
```

직접 Compose를 실행할 때는 아래 명령을 사용합니다.

```bash
docker compose build
docker compose up -d
docker compose ps
```

접속 주소:

```text
http://<SERVER_IP>:8080
```

### 3.4 방화벽 설정

```bash
sudo ufw allow 22/tcp
sudo ufw allow 8080/tcp
sudo ufw enable
sudo ufw status
```

`APP_PORT`를 변경했다면 `8080` 대신 해당 포트를 허용하세요.

## 4. 비밀번호 설정

로컬 개발 기본 계정은 아래처럼 설정하면 됩니다.

```env
AUTH_USERNAME=admin
AUTH_PASSWORD=admin
AUTH_PASSWORD_HASH=
```

운영 서버에서는 `admin / admin`을 그대로 사용하지 말고, `AUTH_PASSWORD`를 더 강한 비밀번호로 바꾸거나 `AUTH_PASSWORD_HASH`를 사용하세요. `AUTH_PASSWORD_HASH`를 사용할 때는 평문 비밀번호 대신 bcrypt 해시를 넣습니다. 관리자 페이지의 수동 재스캔은 `AUTH_USERNAME`으로 설정된 관리자 계정만 실행할 수 있습니다.

관리자 페이지의 `이미지 루트 경로`에서는 현재 탐색 루트를 변경할 수 있습니다. `서버 저장 경로`에서는 필터 결과를 서버에 저장할 때 사용하는 루트도 변경할 수 있습니다. 변경한 경로는 환경변수 파일을 직접 수정하지 않고 SQLite DB의 런타임 설정으로 저장됩니다. 서버 재시작 후에도 관리자 설정이 우선 적용되며, 이미지 루트가 새 경로로 변경되면 기존 이미지 목록 레코드는 DB에서 삭제되고 백그라운드 재스캔이 요청됩니다.

MinIO/lakeFS는 로컬 서버 또는 사설망 endpoint만 사용하도록 기본 설정되어 있습니다. Docker Compose는 로컬 MinIO(`http://localhost:9000`, 콘솔 `http://localhost:9001`)와 `medical-images` 버킷을 함께 띄우며, 백엔드는 Compose 내부 주소인 `http://minio:9000`으로 업로드합니다. lakeFS도 같은 Compose 스택에서 함께 실행되며, local database/local blockstore와 초기 admin access key를 환경변수로 자동 설정합니다. lakeFS S3 Gateway를 사용할 때는 `OBJECT_STORAGE_ENDPOINT_URL=http://lakefs:8000`, `OBJECT_STORAGE_BUCKET=<repository>`, `OBJECT_STORAGE_PREFIX=<branch>/exports`처럼 로컬 Compose 네트워크 주소와 repository/branch 경로를 지정하세요. 공개 인터넷 endpoint를 쓰려면 명시적으로 `OBJECT_STORAGE_ALLOW_REMOTE_ENDPOINT=true`를 설정해야 합니다.

### Windows PowerShell

백엔드 가상환경을 활성화하고 실행합니다.

```powershell
@'
import bcrypt
print(bcrypt.hashpw(b"change-me", bcrypt.gensalt()).decode())
'@ | python -
```

### Ubuntu

```bash
python3 - <<'PY'
import bcrypt
print(bcrypt.hashpw(b"change-me", bcrypt.gensalt()).decode())
PY
```

## 5. 테스트 실행

### Windows

```powershell
.\.venv\Scripts\activate
cd backend
pytest
```

```powershell
cd frontend
npm run test
npm run build
```

### Ubuntu

```bash
source .venv/bin/activate
cd backend
pytest
```

```bash
cd frontend
npm run test
npm run build
```

## 6. 문제 해결

### `python -m pip install -e .[dev]`가 실패하는 경우

저장소 루트에는 `pyproject.toml`이 없으므로 editable install을 루트에서 실행하면 실패합니다. 일반 설치는 저장소 루트에서 아래 명령을 사용하세요.

```powershell
python -m pip install -r requirements-dev.txt
```

editable install이 꼭 필요하면 백엔드 디렉터리에서 실행하세요. Windows PowerShell에서는 `.[dev]`를 따옴표로 감싸는 편이 안전합니다.

```powershell
cd backend
python -m pip install -e ".[dev]"
cd ..
```

### `node` 또는 `npm` 명령을 찾을 수 없는 경우

Node.js가 설치되지 않았거나 PATH가 아직 갱신되지 않은 상태입니다. Windows에서는 아래 명령으로 Node.js LTS를 설치할 수 있습니다.

```powershell
winget install --id OpenJS.NodeJS.LTS -e
```

설치 후 기존 PowerShell을 닫고 새 PowerShell을 열어 다시 확인하세요.

```powershell
node --version
npm --version
```

그래도 인식되지 않으면 Windows를 재부팅하거나, Node.js 설치 경로가 시스템 `Path` 환경 변수에 포함되어 있는지 확인합니다.

### `PNG_ROOT_DIR가 존재하지 않습니다` 오류

환경 변수에 설정한 디렉터리가 실제로 존재하는지 확인하세요.

### `error parsing value for field "cors_origins"` 오류

이전 버전에서 `CORS_ORIGINS`를 JSON 배열로만 해석하려고 해서 발생할 수 있었습니다. 현재 버전은 아래처럼 일반 문자열과 쉼표 구분 문자열을 모두 지원합니다.

```powershell
$env:CORS_ORIGINS="http://localhost:5173"
```

```powershell
$env:CORS_ORIGINS="http://localhost:5173,http://192.168.0.10:8080"
```

### `Permission denied` 오류

Ubuntu에서는 PNG 루트, 썸네일 캐시, SQLite DB 디렉터리 권한을 확인하세요.

```bash
sudo chown -R $USER:$USER /data/company-png /var/cache/png-browser-thumbnails /var/lib/png-browser
```

## 7. 추가 문서

- 사용 방법: [USAGE.md](./USAGE.md)
- 환경 변수 예시: [.env.example](./.env.example)

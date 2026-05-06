# 의료 이미지 관리 웹

의료 이미지 파일을 서버의 지정 폴더에서 스캔하고, 웹 브라우저에서 폴더별 탐색, 썸네일 확인, 메타데이터 검색, 선택 이미지 내보내기를 할 수 있는 내부용 이미지 관리 도구입니다.

지원 이미지 형식은 기본값 기준 `.png`, `.jpg`, `.jpeg`, `.bmp`, `.gif`, `.tif`, `.tiff`, `.webp`, `.ico`, `.jp2`, `.j2k`, `.tga`입니다.

## 빠른 시작

Docker 없이 개발 서버로 먼저 실행해 보고 싶다면 venv를 만들고 백엔드와 프론트엔드를 각각 띄우면 됩니다.

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
```

백엔드 실행:

```powershell
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

새 PowerShell을 열어 프론트엔드 실행:

```powershell
cd frontend
npm install
npm run dev -- --host 0.0.0.0 --port 5173
```

개발 서버 접속 주소:

```text
http://localhost:5173
```

Ubuntu/macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
```

백엔드 실행:

```bash
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

새 터미널을 열어 프론트엔드 실행:

```bash
cd frontend
npm install
npm run dev -- --host 0.0.0.0 --port 5173
```

개발 서버 접속 주소:

```text
http://localhost:5173
```

MinIO와 lakeFS까지 포함해서 한 번에 실행하고 싶다면 로컬 Docker 스택을 사용합니다. 앱, 백엔드, MinIO, lakeFS가 함께 실행됩니다.

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
앱:            http://localhost:8080
MinIO API:     http://localhost:9000
MinIO Console: http://localhost:9001
lakeFS UI:     http://localhost:8001
```

기본 계정:

```text
앱:     admin / admin
MinIO:  minioadmin / minioadmin
lakeFS: AKIAIOSFODNN7EXAMPLE / lakefs-local-secret
```

처음 실행 후 이미지가 보이지 않는다면, 이미지 원본 폴더에 파일을 넣은 뒤 앱의 관리자 페이지에서 수동 재스캔을 실행하세요.

## 이 프로젝트가 하는 일

- 서버의 이미지 폴더를 재귀적으로 스캔합니다.
- 이미지 목록, 폴더 트리, 썸네일, 상세 정보를 웹에서 보여줍니다.
- PNG 텍스트 메타데이터, XMP, EXIF 등 추출 가능한 메타데이터를 검색할 수 있습니다.
- 원하는 메타데이터 키를 관리자 페이지에서 고정 표시 항목으로 등록할 수 있습니다.
- 선택한 이미지 또는 필터 결과를 PC 폴더, 서버 로컬 폴더, 로컬 MinIO/lakeFS로 내보낼 수 있습니다.
- 로그인, 회원가입, 가입 코드, 비밀번호 변경을 지원합니다.
- 실제 원본 파일이 삭제되면 다음 재스캔 때 DB 목록에서도 제거합니다.

## 구성 요소

- `backend`: FastAPI, SQLAlchemy, Pillow 기반 API 서버
- `frontend`: React, Vite 기반 웹 UI
- `docker-compose.yml`: 앱, MinIO, lakeFS 로컬 스택
- `scripts/start-local-stack.ps1`: Windows용 로컬 Docker 스택 실행 스크립트
- `scripts/start-local-stack.sh`: Linux/macOS용 로컬 Docker 스택 실행 스크립트
- `scripts/setup-windows.ps1`: Docker 없이 개발 환경을 준비하는 Windows 스크립트
- `scripts/setup-ubuntu.sh`: Docker 없이 개발 환경을 준비하는 Ubuntu 스크립트

## 권장 실행 방식

### 1. Docker로 전체 로컬 스택 실행

Docker Desktop 또는 Docker Engine이 설치되어 있어야 합니다.

Windows:

```powershell
.\scripts\start-local-stack.ps1
```

Linux/macOS:

```bash
bash scripts/start-local-stack.sh
```

스크립트가 하는 일:

- 이미지 원본 폴더를 만듭니다.
- 루트 `.env` 파일을 로컬 Docker용으로 생성합니다.
- 기존 `.env`가 있으면 `.env.backup-YYYYMMDD-HHMMSS`로 백업합니다.
- `docker compose up -d --build`를 실행합니다.
- MinIO 버킷 `medical-images`를 자동 생성합니다.
- lakeFS 초기 admin access key를 자동 설정합니다.

Windows 기본 원본 폴더:

```text
C:\data\company-png
```

Linux/macOS 기본 원본 폴더:

```text
~/medical-image-data/company-png
```

원본 폴더를 바꾸고 싶다면 실행 시 값을 넘기면 됩니다.

Windows:

```powershell
.\scripts\start-local-stack.ps1 -PngRootDir "D:\medical-images"
```

Linux/macOS:

```bash
HOST_PNG_ROOT_DIR=/data/company-png bash scripts/start-local-stack.sh
```

### 2. Docker Compose 직접 실행

직접 `.env`를 관리하고 싶다면 다음 순서로 실행합니다.

```bash
cp .env.example .env
docker compose up -d --build
docker compose ps
```

중요한 `.env` 값:

```env
APP_PORT=8080
HOST_PNG_ROOT_DIR=/data/company-png
PNG_ROOT_DIR=/data/company-png
EXPORT_STORAGE_BACKEND=object
OBJECT_STORAGE_ENDPOINT_URL=http://minio:9000
OBJECT_STORAGE_BUCKET=medical-images
OBJECT_STORAGE_PREFIX=exports
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=minioadmin
LAKEFS_PORT=8001
AUTH_USERNAME=admin
AUTH_PASSWORD=admin
```

`HOST_PNG_ROOT_DIR`는 호스트 PC의 실제 이미지 폴더입니다. `PNG_ROOT_DIR`는 컨테이너 안에서 보이는 경로이며, 기본값 그대로 두는 것을 권장합니다.

### 3. Docker 없이 개발 서버로 실행

개발 중에는 백엔드와 프론트엔드를 각각 실행해도 됩니다.

Windows 준비:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\scripts\setup-windows.ps1
```

Ubuntu 준비:

```bash
bash scripts/setup-ubuntu.sh
```

수동 실행 순서:

```bash
python -m venv .venv
```

Windows:

```powershell
.\.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Linux/macOS:

```bash
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

다른 터미널에서 프론트엔드 실행:

```bash
cd frontend
npm install
npm run dev -- --host 0.0.0.0 --port 5173
```

개발 서버 접속:

```text
http://localhost:5173
```

## MinIO와 lakeFS 로컬 구성

기본 Docker 스택은 MinIO와 lakeFS를 모두 로컬에서 실행합니다. 외부 클라우드 S3를 전제로 하지 않습니다.

MinIO:

- API: `http://localhost:9000`
- Console: `http://localhost:9001`
- 기본 버킷: `medical-images`
- 기본 계정: `minioadmin / minioadmin`

lakeFS:

- UI: `http://localhost:8001`
- 컨테이너 내부 S3 Gateway: `http://lakefs:8000`
- 기본 access key: `AKIAIOSFODNN7EXAMPLE`
- 기본 secret key: `lakefs-local-secret`
- local database와 local blockstore를 사용합니다.

앱은 기본적으로 MinIO에 저장하도록 설정되어 있습니다.

```env
OBJECT_STORAGE_ENDPOINT_URL=http://minio:9000
OBJECT_STORAGE_BUCKET=medical-images
OBJECT_STORAGE_PREFIX=exports
```

lakeFS S3 Gateway로 저장하고 싶다면 lakeFS에서 repository를 만든 뒤 `.env`를 예시처럼 바꾸세요.

```env
OBJECT_STORAGE_ENDPOINT_URL=http://lakefs:8000
OBJECT_STORAGE_BUCKET=<lakefs-repository-name>
OBJECT_STORAGE_PREFIX=main/exports
```

그 다음 컨테이너를 다시 시작합니다.

```bash
docker compose up -d
```

보안을 위해 기본값에서는 로컬 또는 사설망 endpoint만 허용합니다. 공개 인터넷 endpoint를 정말 써야 할 때만 아래 값을 명시적으로 켜세요.

```env
OBJECT_STORAGE_ALLOW_REMOTE_ENDPOINT=true
```

## 로그인과 회원가입

초기 관리자 계정은 `.env`의 `AUTH_USERNAME`, `AUTH_PASSWORD`로 정합니다.

```env
AUTH_USERNAME=admin
AUTH_PASSWORD=admin
```

운영 환경에서는 반드시 변경하세요.

관리자는 앱의 관리자 페이지에서 가입 코드를 바꿀 수 있습니다. 새 사용자는 로그인 화면의 회원가입 탭에서 사용자명, 비밀번호, 가입 코드를 입력해야 가입할 수 있습니다.

로그인한 사용자는 화면 상단의 `비밀번호 변경`에서 자기 비밀번호를 직접 바꿀 수 있습니다.

## 스캔과 DB 동작

백엔드는 이미지 루트 폴더를 스캔해 SQLite DB에 이미지 정보와 메타데이터를 저장합니다.

자동 스캔:

```env
AUTO_SCAN_ON_STARTUP=true
PERIODIC_SCAN_INTERVAL_SECONDS=300
```

- 백엔드 시작 시 한 번 스캔합니다.
- 기본값으로 5분마다 재스캔합니다.
- 관리자 페이지에서 수동 재스캔을 실행할 수 있습니다.
- 일반 사용자는 현재 선택한 폴더만 재스캔할 수 있습니다.

삭제된 원본 파일:

- 실제 이미지 파일이 삭제되어도 DB가 즉시 바뀌지는 않습니다.
- 다음 전체/폴더/단일 이미지 재스캔 때 해당 DB 레코드를 삭제합니다.
- 예전처럼 `missing` 상태로 남기지 않습니다.

이미지 루트 변경:

- 관리자 페이지에서 이미지 루트 경로를 바꿀 수 있습니다.
- 루트를 바꾸면 기존 이미지 목록 레코드는 DB에서 삭제됩니다.
- 새 루트에 대해 백그라운드 재스캔이 요청됩니다.

## 주요 환경 변수

| 변수 | 설명 | 예시 |
| --- | --- | --- |
| `HOST_PNG_ROOT_DIR` | Docker 실행 시 호스트의 실제 이미지 폴더 | `/data/company-png` |
| `PNG_ROOT_DIR` | 백엔드가 읽는 이미지 루트 경로 | `/data/company-png` |
| `THUMBNAIL_CACHE_DIR` | 썸네일 캐시 저장 경로 | `/var/cache/png-browser-thumbnails` |
| `EXPORT_ROOT_DIR` | 서버 로컬 내보내기 루트 | `/var/lib/png-browser/exports` |
| `DATABASE_URL` | SQLAlchemy DB URL | `sqlite:////var/lib/png-browser/app.db` |
| `AUTH_USERNAME` | 관리자 사용자명 | `admin` |
| `AUTH_PASSWORD` | 관리자 비밀번호 | `admin` |
| `AUTH_PASSWORD_HASH` | bcrypt 해시 비밀번호 | 비워두거나 해시값 |
| `AUTH_SECRET_KEY` | 로그인 세션 서명 키 | 긴 랜덤 문자열 |
| `SIGNUP_CODE` | 초기 가입 코드 | 비워둘 수 있음 |
| `EXPORT_STORAGE_BACKEND` | 기본 저장 백엔드 | `local` 또는 `object` |
| `OBJECT_STORAGE_ENDPOINT_URL` | MinIO/lakeFS S3 endpoint | `http://minio:9000` |
| `OBJECT_STORAGE_BUCKET` | MinIO 버킷 또는 lakeFS repository | `medical-images` |
| `OBJECT_STORAGE_PREFIX` | 저장 prefix | `exports` |

## 테스트와 빌드

백엔드 테스트:

```bash
pytest backend/tests
```

프론트엔드 테스트:

```bash
cd frontend
npm test
```

프론트엔드 빌드:

```bash
cd frontend
npm run build
```

## 자주 생기는 문제

### Docker 명령을 찾을 수 없습니다

Docker Desktop 또는 Docker Engine이 설치되어 있고 실행 중인지 확인하세요. Windows에서는 Docker Desktop을 실행한 뒤 새 PowerShell을 열어 다시 시도하는 것이 좋습니다.

### 앱은 뜨지만 이미지가 없습니다

이미지 원본 폴더에 파일이 있는지 확인하세요. Docker 스택에서는 `HOST_PNG_ROOT_DIR`가 호스트 실제 폴더입니다. 파일을 넣은 뒤 관리자 페이지에서 수동 재스캔을 실행하세요.

### MinIO 저장이 실패합니다

MinIO 컨테이너와 버킷 초기화 컨테이너가 정상 종료되었는지 확인하세요.

```bash
docker compose ps
docker compose logs minio
docker compose logs minio-init
```

### lakeFS 로그인이 안 됩니다

기본 계정은 access key와 secret key로 로그인합니다.

```text
AKIAIOSFODNN7EXAMPLE / lakefs-local-secret
```

기존 `lakefs-data` 볼륨이 이미 만들어진 뒤 `.env`의 lakeFS 초기 계정을 바꾸면 새 값이 적용되지 않을 수 있습니다. 테스트 환경에서 초기화해도 괜찮다면 볼륨을 삭제하고 다시 시작하세요.

```bash
docker compose down -v
docker compose up -d --build
```

### 포트가 이미 사용 중입니다

`.env`에서 포트를 바꾸세요.

```env
APP_PORT=8081
MINIO_CONSOLE_PORT=9002
LAKEFS_PORT=8002
```

MinIO API 포트 `9000`은 현재 Compose에 고정되어 있습니다. 이미 사용 중이라면 `docker-compose.yml`의 `9000:9000` 매핑을 바꾸면 됩니다.

## 더 자세한 사용법

실제 화면 사용법은 [USAGE.md](./USAGE.md)를 참고하세요.

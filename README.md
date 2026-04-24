# PNG Browser

사내 Ubuntu 서버의 PNG 파일을 안전하게 탐색하는 내부용 웹 애플리케이션입니다. 폴더 트리 탐색, 썸네일/원본 미리보기, PNG 메타데이터 추출, 텍스트 메타데이터 검색, 관리자 재스캔을 제공합니다.

## 기술 스택

- Backend: Python 3.11+, FastAPI, SQLAlchemy, SQLite
- Frontend: React + TypeScript + Vite
- Image metadata / thumbnails: Pillow
- Optional watcher: watchdog
- Deployment: Docker Compose + Nginx reverse proxy
- Tests: pytest, Vitest

## 가정 사항

- 이 도구는 `PNG_ROOT_DIR` 아래의 PNG만 읽습니다.
- 원본 PNG 파일은 절대 수정하지 않습니다.
- 썸네일 캐시는 `THUMBNAIL_CACHE_DIR`에만 저장됩니다.
- 기본 UI 언어는 한국어입니다.
- 폴더 클릭 시 우측 검색 결과는 해당 폴더 이하 subtree 기준으로 표시합니다.
- 기본 인증 방식은 앱 내 로그인 세션 쿠키입니다. 필요하면 Nginx Basic Auth를 추가로 겹칠 수 있습니다.

## 주요 기능

- 루트 기준 상대 경로만 노출하는 폴더 트리
- PNG 썸네일 지연 생성 및 캐시
- 원본 이미지 안전 스트리밍
- Pillow + 안전한 PNG 청크 파서 기반 메타데이터 추출
- 텍스트 메타데이터 `tEXt`, `zTXt`, `iTXt` 인덱싱
- SQLite FTS5 기반 전문 검색, 미지원 시 LIKE 폴백
- 구조화 필터: 디렉터리, 크기, 파일 사이즈, 수정일, 알파 채널, 상태, 메타데이터 키/값
- 관리자 재스캔 및 인덱스 상태 확인
- 경로 순회, 절대경로 접근, symlink escape 차단

## 저장소 구조

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
│  │  ├─ models.py
│  │  ├─ schemas.py
│  │  └─ main.py
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

## 백엔드 아키텍처

- `FileSystemService`: 루트 경계 검증, 상대경로 정규화, symlink 정책 적용, PNG 재귀 탐색
- `MetadataExtractor`: Pillow 메타데이터 추출 + PNG 청크 파서 결과 병합
- `PNGChunkParser`: `IHDR`, `gAMA`, `iCCP`, `tEXt`, `zTXt`, `iTXt`, `eXIf` 안전 파싱
- `IndexService`: 전체 스캔, 증분 재인덱싱, 삭제 파일 `missing` 처리, 검색 인덱스/폴더 테이블 재생성
- `SearchService`: 목록 조회, FTS 검색, 구조화 필터, 폴더 트리, facet 집계
- `ThumbnailService`: 썸네일 생성/캐시
- `AuthService`: bcrypt 해시 기반 로그인과 세션 쿠키

## 환경 변수

`.env.example`를 복사해서 `.env`를 만드세요.

| 변수 | 설명 |
|---|---|
| `APP_PORT` | 외부 공개 포트 |
| `PNG_ROOT_DIR` | PNG 원본 루트 디렉터리 |
| `THUMBNAIL_CACHE_DIR` | 썸네일 캐시 디렉터리 |
| `DATABASE_URL` | SQLite DB 경로 |
| `AUTO_SCAN_ON_STARTUP` | 서버 시작 시 자동 스캔 여부 |
| `ALLOW_SYMLINKS` | symlink 추적 허용 여부, 기본 `false` |
| `PUBLIC_SHOW_ABSOLUTE_PATH` | UI에 절대경로 표시 여부 |
| `ENABLE_WATCHDOG` | watchdog 기반 백그라운드 감시 여부 |
| `USE_FTS5` | SQLite FTS5 사용 여부 |
| `AUTH_ENABLED` | 앱 인증 사용 여부 |
| `AUTH_USERNAME` | 로그인 사용자명 |
| `AUTH_PASSWORD_HASH` | bcrypt 해시 비밀번호 |
| `AUTH_SECRET_KEY` | 세션 서명 키 |
| `CORS_ORIGINS` | 개발/외부 접근 허용 Origin 목록 |

## 비밀번호 해시 생성

Linux/macOS:

```bash
python3 - <<'PY'
import bcrypt
print(bcrypt.hashpw(b"change-me", bcrypt.gensalt()).decode())
PY
```

Windows PowerShell:

```powershell
@'
import bcrypt
print(bcrypt.hashpw(b"change-me", bcrypt.gensalt()).decode())
'@ | python -
```

## 로컬 개발 실행

### 1. 백엔드

```powershell
cd backend
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -e .[dev]
$env:PNG_ROOT_DIR="C:\data\company-png"
$env:THUMBNAIL_CACHE_DIR="C:\png-browser-cache"
$env:DATABASE_URL="sqlite:///./png_browser.db"
$env:AUTO_SCAN_ON_STARTUP="true"
$env:AUTH_ENABLED="true"
$env:AUTH_USERNAME="admin"
$env:AUTH_PASSWORD_HASH="<bcrypt_hash>"
$env:AUTH_SECRET_KEY="change-this-secret"
$env:CORS_ORIGINS="http://localhost:5173"
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Bash:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .[dev]
export PNG_ROOT_DIR=/data/company-png
export THUMBNAIL_CACHE_DIR=/var/cache/png-browser-thumbnails
export DATABASE_URL=sqlite:////var/lib/png-browser/app.db
export AUTO_SCAN_ON_STARTUP=true
export AUTH_ENABLED=true
export AUTH_USERNAME=admin
export AUTH_PASSWORD_HASH='<bcrypt_hash>'
export AUTH_SECRET_KEY='change-this-secret'
export CORS_ORIGINS=http://localhost:5173
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 2. 프런트엔드

```bash
cd frontend
npm install
npm run dev -- --host 0.0.0.0 --port 5173
```

개발 중 프런트엔드는 `/api`를 `http://localhost:8000`으로 프록시합니다.

## 초기 스캔

앱 시작 시 자동 스캔:

```bash
export AUTO_SCAN_ON_STARTUP=true
```

수동 재스캔:

```bash
curl -X POST http://localhost:8000/api/admin/rescan -b cookies.txt -c cookies.txt
```

또는 UI 오른쪽 패널의 `재스캔` 버튼을 사용하세요.

## Ubuntu 서버 배포

### 1. 사전 준비

```bash
sudo apt-get update
sudo apt-get install -y docker.io docker-compose-plugin ufw
sudo systemctl enable --now docker
```

### 2. 프로젝트 배치

```bash
git clone <YOUR_REPOSITORY_URL> png-browser
cd png-browser
cp .env.example .env
```

`.env`에서 최소한 다음 값을 실제 서버에 맞게 수정하세요.

- `PNG_ROOT_DIR=/data/company-png`
- `THUMBNAIL_CACHE_DIR=/var/cache/png-browser-thumbnails`
- `DATABASE_URL=sqlite:////var/lib/png-browser/app.db`
- `AUTH_USERNAME=admin`
- `AUTH_PASSWORD_HASH=<실제 bcrypt 해시>`
- `AUTH_SECRET_KEY=<충분히 긴 랜덤 문자열>`
- `APP_PORT=8080`

### 3. Docker Compose 실행

```bash
docker compose build
docker compose up -d
docker compose ps
```

접속 주소:

```text
http://<SERVER_IP>:8080
```

### 4. 방화벽(UFW)

```bash
sudo ufw allow 22/tcp
sudo ufw allow 8080/tcp
sudo ufw enable
sudo ufw status
```

포트를 바꿨다면 `8080` 대신 `APP_PORT` 값으로 허용하세요.

## Nginx 뒤에 배치하는 방법

이 저장소의 `docker-compose.yml`은 이미 gateway Nginx를 포함합니다. 별도 사내 L7 프록시가 있다면 해당 프록시에서 이 앱의 포트로 전달하면 됩니다.

추가로 Nginx Basic Auth를 쓰고 싶다면 `deployment/nginx/default.conf`의 아래 주석을 해제하세요.

```nginx
# auth_basic "Restricted";
# auth_basic_user_file /etc/nginx/.htpasswd;
```

## 데이터베이스 백업

컨테이너 내부 SQLite 파일 백업:

```bash
docker compose exec backend sh -lc 'cp /var/lib/png-browser/app.db /var/lib/png-browser/app-$(date +%F-%H%M%S).db'
```

호스트로 복사:

```bash
docker compose cp backend:/var/lib/png-browser/app.db ./app.db.backup
```

## 테스트 실행

백엔드:

```bash
cd backend
python -m pip install -e .[dev]
pytest
```

프런트엔드:

```bash
cd frontend
npm install
npm run test
npm run build
```

## PostgreSQL 마이그레이션 가이드

수십만 건 이상으로 늘어나면 SQLite 대신 PostgreSQL 전환을 권장합니다.

- `DATABASE_URL`을 PostgreSQL DSN으로 변경합니다.
- SQLAlchemy 모델은 그대로 재사용 가능합니다.
- FTS는 PostgreSQL `GIN + tsvector` 또는 dedicated search index로 대체합니다.
- 썸네일 캐시 전략은 그대로 유지할 수 있습니다.

## 트러블슈팅

- `PNG_ROOT_DIR does not exist`: 루트 디렉터리 경로가 실제 컨테이너/호스트에 존재하는지 확인하세요.
- 썸네일이 안 보임: `THUMBNAIL_CACHE_DIR` 쓰기 권한과 원본 PNG 읽기 권한을 확인하세요.
- 검색이 느림: 초기 스캔 완료 여부와 FTS5 사용 가능 여부를 확인하세요.
- 재스캔 409 응답: 이미 스캔이 진행 중이거나 너무 짧은 간격으로 재요청한 상태입니다.
- 손상 파일이 많음: `status=corrupted` 필터로 먼저 분류해 확인하세요.
- 절대경로가 안 보임: `PUBLIC_SHOW_ABSOLUTE_PATH=true`로 명시적으로 활성화해야 합니다.

## 알려진 제한사항

- 현재 디렉터리 필터는 선택한 폴더 이하 subtree 기준입니다.
- 메타데이터 값 비교는 현재 `contains` 방식입니다.
- 매우 큰 스캔은 MVP 기준으로 단일 프로세스에서 수행합니다.

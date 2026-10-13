# HippoBox 0.2 배포

프론트엔드는 이미지 빌드 시 포함되고 FastAPI가 SPA와 API를 함께 제공합니다.
별도 프론트엔드 서버는 필요하지 않습니다. 이 구성은 PostgreSQL, Redis, Qdrant,
API, Celery worker/beat를 실행합니다. 실제 서비스 서버 배포는 별도 운영 작업입니다.

## 새 설치

저장소 루트에서:

```sh
cp docker/.env.release.example docker/.env
python3 -c 'import secrets; print(secrets.token_urlsafe(48))'
# 생성한 값을 docker/.env의 SECRET_KEY에 기록합니다.
# DB_PASSWORD도 별도로 생성하고 OPENAI_API_KEY, PUBLIC_APP_URL을 설정합니다.
make release-config
make release-pull
make release-up
make release-status
```

소스 없이 GitHub 릴리즈의 `compose.release.yml`, `default.env.release.example`만 받은 경우:

```sh
cp default.env.release.example .env
# 위 필수 값을 설정한 뒤 실행합니다.
docker compose --env-file .env -f compose.release.yml pull
docker compose --env-file .env -f compose.release.yml up -d --wait
```

기본 주소는 `http://127.0.0.1:8000`입니다. 포트는 `.env`의 `PORT=8080`처럼
바꿀 수 있습니다. 기본 바인딩은 루프백이며, 공개 서비스는 HTTPS 리버스 프록시와
`PUBLIC_APP_URL`/`PUBLIC_API_URL`을 설정합니다. DB·Redis·Qdrant는 호스트에
포트를 공개하지 않습니다. GHCR 패키지가 비공개이면 read:packages 권한으로
`docker login ghcr.io`가 필요합니다.

`VDB_ENABLED=false`로 임베딩 없이 기동할 수 있습니다. 벡터 검색을 사용하려면
유효한 `OPENAI_API_KEY`와 임베딩 모델 설정이 필요합니다. 기존 컬렉션과 다른 모델이나
차원을 사용하면 별도 데이터 재색인이 필요합니다.

메일은 기본 비활성입니다. `EMAIL_ENABLED=true`와 SMTP 또는 Resend 설정을 함께
지정합니다. OAuth와 Stripe도 기본 비활성이며 각각 외부 서비스 설정이 필요합니다.
worker/beat는 메일 outbox 재시도와 정기 작업을 담당합니다.

## 기존 0.1 데이터 업그레이드

1. 기존 서버·worker를 중지하고 SQL DB, Qdrant 저장소, 첨부파일을 백업합니다.
2. 운영 데이터 복제본에서 먼저 검증합니다. 이 Compose 구성은 새 PostgreSQL 볼륨을
   만듭니다. 기존 SQLite 데이터를 PostgreSQL로 자동 복사하지 않습니다.
3. 기존 DB를 유지하려면 동일한 DB 설정/볼륨을 연결합니다. Qdrant도 기존 저장소와
   컬렉션을 유지합니다. 운영 `SECRET_KEY`를 바꾸지 않습니다.
4. 첫 기동에만 `PLATFORM_MIGRATE_LEGACY=true`를 설정합니다. 기존 사용자·지식 ID와
   API 키는 유지되고 새 플랫폼 테이블 및 인증 식별자가 추가됩니다. SQLite는 자동
   `.pre-platform-*.bak`도 생성하지만 외부 백업을 대체하지 않습니다.
5. 정상 시작 후 플래그를 `false`로 되돌립니다. 사용자는 재로그인하고 이전 이메일
   인증/비밀번호 재설정 링크는 재발급합니다.

오래된 PostgreSQL은 먼저 0.1의 기존 HippoBox Alembic 이력까지 적용한 뒤 전환합니다.
`hippobox/platform/alembic`은 upstream 참고 자료입니다. HippoBox DB에 실행하지 마세요.
플랫폼 전환 이후 `create_all`을 임의의 향후 스키마 변경 도구로 사용해서는 안 됩니다.

## 점검·업데이트·복구

```sh
make release-status
make release-logs
curl --fail http://127.0.0.1:8000/health/ready
# .env의 HIPPOBOX_IMAGE를 검증한 버전 태그/다이제스트로 변경합니다.
make release-pull
make release-up
```

`/health/live`는 프로세스, `/health/ready`는 DB·Redis와 활성화된 Qdrant 연결을 확인합니다.
외부 메일·OAuth·Stripe·OpenAI의 실제 유효성까지 보증하지 않습니다. 첫 운영 전에는
가입·로그인·지식 생성/검색·MCP 호출과 필요한 외부 기능을 실제 설정으로 확인합니다.

볼륨을 삭제하는 `down -v`는 운영 환경에서 사용하지 않습니다. 스키마 전환 후 이전
버전으로 되돌릴 때는 이전 이미지뿐 아니라 전환 전 SQL/Qdrant/첨부파일 백업을 함께
복원합니다. PostgreSQL은 `pg_dump`, Qdrant는 스냅샷, 첨부파일은 objects 볼륨을
각각 백업하고 복구 절차를 검증합니다.

## 릴리즈 만들기

패키지와 프론트엔드 버전, 배포 기본 태그 및 `docs/release-notes.md`를 갱신하고 커밋합니다.
`v0.2.0` 같은 버전 태그를 푸시하면 GitHub Actions가 `make verify`를 실행한 뒤
GHCR의 amd64/arm64 이미지를 게시하고 GitHub 릴리즈에 wheel/sdist/배포 파일을 첨부합니다.
검증이나 이미지 빌드가 실패하면 릴리즈 생성은 진행하지 않습니다. 릴리즈 후 같은
wheel/sdist를 해시 검증하고 PyPI Trusted Publishing으로 게시합니다. 이미 게시된
GitHub 릴리즈는 `workflow_dispatch`의 `pypi_only=true`로 이미지 재빌드 없이 게시할 수 있습니다.
실제 서비스 서버 업데이트는 이 워크플로에 포함하지 않습니다.

## hippobox.org / Resend 운영 설정

운영 환경파일은 저장소 사용 시 `docker/.env`, 릴리즈 파일만 사용하는 경우
Compose 파일 옆의 `.env`에 둡니다. 두 경로 중 하나만 사용하면 됩니다.

```dotenv
PUBLIC_APP_URL=https://hippobox.org
PUBLIC_API_URL=https://hippobox.org
BIND_ADDRESS=127.0.0.1
PORT=8000
# 아래 값은 포트가 호스트 루프백에만 공개되고 신뢰하는 프록시가 접근하는 구성용입니다.
FORWARDED_ALLOW_IPS=*
EMAIL_ENABLED=true
RESEND_API_KEY=re_REPLACE_WITH_YOUR_KEY
EMAIL_FROM='HippoBox <no-reply@hippobox.org>'
```

Resend에서 도메인 인증을 완료하고 해당 도메인의 발송 권한이 있는 API 키를 사용합니다.
API 키가 설정되면 SMTP 대신 Resend를 사용하므로 SMTP 항목은 비워 둡니다.
인증/비밀번호 메일 링크는 `PUBLIC_APP_URL`을 기준으로 생성합니다. Redis와 worker가
실행되어야 실제 메일이 발송됩니다. 환경파일을 변경한 뒤에는 `restart` 대신
`docker compose --env-file .env -f compose.release.yml up -d --wait`로 컨테이너를 재생성합니다.

파일 권한은 `chmod 600 .env`로 제한합니다. 새 설치 시 생성한 `SECRET_KEY`와
`DB_PASSWORD`는 이후 업데이트에서도 유지합니다. 기존 데이터 업그레이드에는 기존
운영 키와 DB 비밀번호를 사용하며, 새 환경파일의 무작위 값으로 교체하지 않습니다.

호스트에 Nginx와 Certbot이 설치된 Ubuntu/Debian 기준으로 DNS를 서버 IP에 연결하고
[nginx.conf.example](../docker/nginx.conf.example)을 `/etc/nginx/sites-available/hippobox`
에 복사한 후 활성화합니다. 기존 동일 도메인의 설정이 있다면 중복으로 추가하지 않고
그 설정에 프록시 블록을 반영합니다.

```sh
sudo ln -s /etc/nginx/sites-available/hippobox /etc/nginx/sites-enabled/hippobox
sudo nginx -t
sudo systemctl reload nginx
sudo certbot --nginx -d hippobox.org
```

서버/클라우드 방화벽에서는 80·443을 허용합니다. 앱의 8000 포트와 DB·Redis·Qdrant는
외부에 공개할 필요가 없습니다. 이 예제는 Nginx가 Docker 호스트에서 실행되는 구성입니다.
Nginx 자체가 컨테이너라면 `127.0.0.1` upstream 대신 공유 Docker 네트워크를 구성해야 합니다.

설정 확인:

```sh
docker compose --env-file .env -f compose.release.yml ps
curl --fail http://127.0.0.1:8000/health/ready
docker compose --env-file .env -f compose.release.yml logs --tail=100 hippobox worker
```

가입 인증 또는 비밀번호 재설정을 수행해 받은 메일의 도메인과 링크를 확인합니다.
Resend 대시보드에서도 발송 결과를 확인할 수 있습니다. 시작 시 설정 검증 통과는
실제 메일 전달 성공을 의미하지 않습니다.

## 기존 SQLite + HippoBox 컨테이너만 실행

`compose.release.yml`은 PostgreSQL 전용입니다. `DB_DRIVER`를 `.env`에서 바꾸거나
`--no-deps`를 사용해도 SQLite로 전환되지 않습니다. 기존 Redis/Qdrant 컨테이너를
유지하면서 SQLite를 사용하는 경우 [compose.sqlite.yml](../docker/compose.sqlite.yml)을
단독으로 사용합니다. 이 파일은 DB_PASSWORD를 요구하지 않으며 다른 서비스를 시작하지 않습니다.

```dotenv
# 실제 SQLite 파일의 부모 디렉터리와 파일명을 지정합니다.
HIPPOBOX_DATA_DIR=/absolute/path/to/existing-data
SQLITE_DB_FILENAME=hippobox.db
# 기존 Redis/Qdrant가 연결된 Docker 네트워크
HIPPOBOX_NETWORK=hippobox-net
REDIS_IN_MEMORY=false
REDIS_HOST=redis
QDRANT_MODE=docker
QDRANT_URL=http://qdrant:6333
```

먼저 기존 SQLite 파일과 네트워크가 실제로 존재하는지 확인하세요. 기존 앱을 중지하고
백업한 뒤 데이터 디렉터리를 컨테이너 UID/GID 10001이 읽고 쓸 수 있도록 설정합니다.
디렉터리 쓰기 권한도 SQLite journal/WAL 및 사전 백업에 필요합니다. 기존 DB가 컨테이너
내부에만 있다면 먼저 꺼내서 영속 디렉터리에 보존해야 합니다. 빈 경로를 지정해 기존
데이터가 자동 복사된다고 가정하지 마세요. 0.1 DB는 앞의 전환 절차를 따릅니다.

```sh
docker compose --env-file .env -f compose.sqlite.yml config --quiet
docker compose --env-file .env -f compose.sqlite.yml up -d --no-deps hippobox
```

`.env`의 기존 SECRET_KEY, Resend/OpenAI 키, 공개 URL 등은 유지합니다. 기존 Compose와
동일한 프로젝트 이름을 사용해야 같은 프로젝트의 HippoBox 서비스를 갱신합니다.
기존 컨테이너에 별도 이름/프로젝트가 있다면 교체 전에 실행 중인 구성을 확인하세요.
이 구성은 API만 실행하므로 메일 발송용 worker는 기존 worker를 유지하거나 별도로
실행해야 합니다. 이 파일을 PostgreSQL용 Compose와 병합해서 사용하지 않습니다.

## 단일 컨테이너 / 모든 저장소 로컬

[compose.local.yml](../docker/compose.local.yml)은 HippoBox 하나만 실행합니다.
SQLite·Qdrant·첨부파일은 `HIPPOBOX_DATA_DIR`에 저장하며, 외부 DB/Redis 컨테이너가
필요하지 않습니다. 메모리 Redis를 사용하므로 재시작 시 세션 갱신·로그인 제한 등
일시적인 인증 상태는 초기화됩니다. 사용자와 지식 데이터는 디스크에 유지됩니다.
메일·OAuth·결제는 이 구성에서 비활성화합니다. Resend 키를 보관해도 메일을 보내지 않습니다.

새 설치의 환경변수 예시:

```dotenv
HIPPOBOX_DATA_DIR=/home/ubuntu/hippobox-data
SQLITE_DB_FILENAME=hippobox.db
PORT=8001
BIND_ADDRESS=127.0.0.1
VDB_ENABLED=true
# 기존 또는 별도로 생성한 운영 키와 OpenAI 키도 설정합니다.
```

새 데이터 디렉터리는 먼저 만들고 컨테이너 UID/GID 10001에 쓰기 권한을 줍니다.
기존 데이터라면 백업과 경로 확인을 먼저 수행하며, 임의로 새 빈 디렉터리로 바꾸지 않습니다.

```sh
docker compose --env-file .env -f compose.local.yml config --quiet
docker compose --env-file .env -f compose.local.yml up -d --wait
docker compose --env-file .env -f compose.local.yml logs --tail=100 hippobox
```

기존 서비스가 8000번을 쓰는 서버에서는 8001번을 사용합니다. 외부 접근은 HTTPS
프록시를 연결합니다. 일시적으로 IP:포트를 직접 열어 확인하는 경우에만
`BIND_ADDRESS=0.0.0.0`으로 설정하고 해당 포트의 클라우드 방화벽 접근을 확인합니다.

## 여러 앱의 HTTPS를 한 곳에서 관리

Blueprint 등 다른 앱과 서버를 공유한다면 앱별 Caddy 대신
[공용 Caddy 구성](../docker/shared-caddy/README.md)을 사용합니다.
Blueprint 원본을 수정하지 않고 프록시·인증서 볼륨·관리 명령을 별도 경로로 분리합니다.

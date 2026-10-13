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

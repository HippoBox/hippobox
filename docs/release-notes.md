## HippoBox 0.2.0

Blueprint B4FastAPI 기반을 HippoBox 내부에 고정 버전으로 통합했습니다.
기존 HippoBox 디자인, 지식·주제·태그, MCP, 벡터 검색과 기존 API 키를 유지합니다.

- 계정·세션·권한·프로필을 Blueprint 서비스/저장소 기반으로 통합
- 기존 설정 화면에 소개 편집, 계정 보안 및 알림 연결
- OAuth, 객체 저장소, 문의, 결제, 메일 outbox 및 worker/beat 기반 포함
- 기존 SQL 데이터 업그레이드 가드, SQLite 사전 백업 및 사용자 ID 재사용 방지
- 프론트엔드를 포함한 비루트 Docker 이미지, PostgreSQL/Redis/Qdrant Compose 제공
- 검증 후 GHCR 멀티아키텍처 이미지와 배포 파일 자동 게시

### 실행

이미지: `ghcr.io/hippobox/hippobox:0.2.0`

첨부된 Compose 파일과 환경변수 예제를 같은 디렉터리에 저장하고 예제를 `.env`로
복사합니다. SECRET_KEY, DB_PASSWORD, 공개 URL 및 필요한 API 키를 설정한 뒤:

```sh
docker compose --env-file .env -f compose.release.yml up -d --wait
```

기존 데이터는 반드시 백업하고 첫 전환에만 `PLATFORM_MIGRATE_LEGACY=true`를 지정합니다.
업데이트 후 재로그인과 기존 인증/비밀번호 재설정 링크 재발급이 필요합니다.
SQLite→PostgreSQL 데이터 이동은 자동 수행하지 않습니다.

외부 OAuth·메일·Stripe는 기본 비활성이며 별도 공급자 설정이 필요합니다.
기존 HippoBox 화면을 유지하며 모든 Blueprint 화면을 복제하지는 않습니다.
PyPI 게시나 실제 운영 서버 배포는 포함하지 않습니다.

자세한 절차: [배포 안내](https://github.com/HippoBox/hippobox/blob/v0.2.0/docs/deployment.md)

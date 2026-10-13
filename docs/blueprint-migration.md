# Blueprint 플랫폼 마이그레이션

## 0.2 기반 전환 (이전 선택적 적용 범위를 대체)

사용자의 전체 기반 전환 요청에 따라 B4FastAPI `b0ac500619d51cb64e4f0f494687b72d549df51e`를
`hippobox/platform`에 가져왔습니다. 원본은 읽기 전용이며 MIT 고지와 기준 커밋은
`platform/LICENSE`, `platform/UPSTREAM`에 보존합니다. B4React의 CSS·화면·서브모듈은
가져오지 않고 기존 HippoBox UI와 Query 상태 계층을 새 백엔드에 연결합니다.

- 가입/로그인/프로필/세션은 Blueprint 서비스와 저장소를 사용합니다.
- 권한, OAuth, 프로필 사진, 메일 outbox, 알림, 문의, 결제, 운영 API도 같은 기반으로 포함합니다.
- HippoBox 전용 지식·주제·태그·MCP·Qdrant·임베딩과 기존 정적 파일/CLI 배포는 유지합니다.
- 공통 Settings·DB·Redis는 단일 인스턴스로 공유합니다.
- `user`, `credential` 및 모든 지식 테이블·ID를 유지하며 인증 식별자는 `auth_identities`로 옮깁니다.
- 기존 API 키는 `/api/v1/api_key`와 `Bearer sk-…`로 계속 사용할 수 있습니다.
  새 플랫폼 API 키는 `/api/v1/api-keys`와 `X-API-Key`를 사용합니다.
- 사용자 ID 재사용을 막아 삭제 전 JWT가 새 계정에 접근하지 못하게 합니다.
- 비밀번호 최대 64자와 이름 고유 제약을 유지합니다.
- 기존 refresh/이메일 인증/재설정 토큰은 새 저장 형식으로 자동 변환하지 않습니다.
  업그레이드 후 재로그인 또는 메일 재발급이 필요합니다.
- 기존 DB는 기본적으로 시작을 거절합니다. SQL/Qdrant 백업 후 첫 기동에만
  `PLATFORM_MIGRATE_LEGACY=true`를 지정합니다. SQLite는 변환 전 `.bak`도 생성합니다.
- Blueprint 자체 Alembic 이력은 HippoBox DB에 실행하지 않습니다.
- SMTP 또는 기존 Resend를 사용하며 메일 기능 활성화 시 worker/beat와 실제 Redis가 필요합니다.
- 외부 OAuth·SMTP·Resend·Stripe 계정 연결은 운영자가 환경변수를 설정해야 합니다.

검증: SQLite 기존 데이터 보존, PostgreSQL 기존 이력 전환, 기존/신규 API 키 및 MCP,
라이트/다크 브라우저 흐름, 설치 wheel·sdist, Docker Compose 가입·로그인과 worker 반복 실행을 확인했습니다.
실제 외부 공급자의 메일·OAuth·Stripe·OpenAI 호출과 운영 DB 전환은 수행하지 않았습니다.

배포와 업그레이드 절차는 [deployment.md](deployment.md)를 참조합니다.

<details>
<summary>0.1 선택적 적용 기록 (현재 범위는 위의 0.2 기준)</summary>

# Blueprint 패턴의 선택적 적용

HippoBox의 현재 코드 구조·도메인·테마를 유지하면서 Blueprint의 유용한 개발
패턴만 적용합니다. 전체 템플릿 교체나 B4React 서브모듈 연결은 하지 않습니다.
아이콘은 변경하지 않습니다.

## 참조 기준과 경계

- B4FastAPI: `16c115c492fa2a8145e378e26b6122cf97b9f40d`
- 해당 커밋의 B4React: `6e08cde1aa86aa033c4a8faf18894d6ec5b6ed7a`
- Blueprint4Agent는 읽기 전용입니다. 해당 경로에서 설치·빌드·포맷·Git 변경을 실행하지 않습니다.
- 참조 저장소의 미커밋 변경은 가져오지 않습니다.

## 적용 범위

| 단계 | 적용 내용 |
| --- | --- |
| 기준 고정 | 위 커밋을 참고하되 변경은 HippoBox에서만 수행 |
| 회귀 보호 | 긴 비밀번호 로그인, 기존 API 키, CRUD·소유자 격리, 세션, MCP 호출 테스트 |
| 개발 구성 | 작은 Makefile, Ruff, uv lock, 서버 실행이 필요 없는 OpenAPI 생성·검사 |
| 데이터 호환 | 기존 테이블·Alembic 이력·사용자/지식 ID·SHA-256 키·Bearer 인증 유지 |
| 프론트엔드 | Query·라우트·테마·아이콘 유지, 간격/컨트롤 정돈과 연결 실패 복구 |
| 배포 | wheel/CLI/정적 파일 유지, 독립 sdist 재빌드, Docker의 잠긴 의존성 설치 |

결제·OAuth·데스크톱·Celery·공유 서브모듈·복잡한 변경 범위 분류기는 추가하지 않습니다.
기존 release 워크플로의 배포 방식도 유지합니다.

## 설정과 호환성

- `APP_MODE=development`가 기본값입니다. 기존 로컬 동작은 유지됩니다.
- `APP_MODE=production`은 로그인과 32자 이상의 고유 `SECRET_KEY`가 필요합니다.
- 개발용 기본 서명 키는 기존 세션 호환을 위해 유지합니다. 운영 서명 키를
  변경하면 기존 JWT는 만료되므로 재로그인이 필요합니다. API 키 해시는 변경하지 않습니다.
- 비활성 계정은 JWT/API 키 접근을 거절합니다.
- `/config` 실패나 잘못된 응답은 기본 설정으로 진행하지 않고 기존 UI 구성요소로
  재시도 화면을 표시합니다.
- 검색은 SQL에서 소유자·주제·태그에 맞는 ID를 선택한 뒤 Qdrant 검색에 전달합니다.
  기존 벡터 payload와 포인트 ID를 유지하며 재임베딩을 요구하지 않습니다.
  개인 지식 저장소 규모를 위한 방식이며, 매우 큰 데이터셋은 payload 필터 도입을 별도로 검토합니다.
- 기존 Alembic 정규화 이력은 PostgreSQL 전용입니다. SQLite는 현재 모델을 통한
  초기화와 재시작 시 데이터 보존을 검증합니다. 오래된 SQLite 스키마 변환을
  지원한다고 가정하거나 임의로 stamp하지 않습니다.

## 검증과 실행

```sh
make install
cd src/frontend && npx playwright install chromium && cd ../..
make verify-plan
make verify
make test-migrations-postgres
```

`verify`는 기존 DB에 접속하지 않습니다. 테스트 서버는 임시 SQLite와 메모리 Redis를
사용합니다. PostgreSQL 검증은 새 임시 컨테이너를 만들고 종료 시 제거합니다.
패키지 검증은 임시 환경에 wheel을 설치하고 CLI·정적 경로·API 404를 확인하며,
프론트엔드 checkout 없이 sdist를 재빌드합니다.

실제 데이터 변경은 수행하지 않았습니다. `make db-current`와 `make db-migrate`는
현재 환경 설정의 DB를 사용하는 명시적 운영 명령이며, PostgreSQL 운영 DB에 적용하기
전에는 백업과 복제 DB 검증이 필요합니다.

## English summary

Selectively adapt Blueprint patterns while retaining HippoBox's structure, schema,
Bearer API keys, MCP, Query state, theme and icons. Verification and packaging are
self-contained. The frontend keeps its original composition with compact spacing,
responsive actions and configuration recovery. No production data is modified.

## 검증 결과

- `make verify`: 통과. 백엔드 10건, 라이트/다크 브라우저 4건, 계약·타입·빌드·설치 패키지 검사 포함.
- `make test-migrations-postgres`: 임시 PostgreSQL에서 기존 이력과 데이터 보존 1건 통과.
- 기본 테스트에서 PostgreSQL 항목 1건은 별도 명령으로 분리됩니다.
- SQLite 재시작 시 계정·API 키 보존, 기존 키로 실제 MCP 지식 생성 확인.
- Docker 이미지 빌드와 임시 컨테이너의 ping·config·SPA·MCP 초기화 통과.
- 실제 운영 서비스 연결, 운영 DB 변환, 원격 배포는 수행하지 않습니다.

## 인증 처리 구조 보완

위 참조 커밋의 `UserRepository.create_signup_user`, `AuthService.signup`,
프론트엔드 `api/auth/authError.ts`를 기준으로 HippoBox 인증 경계를 정리했습니다.

- 모델의 저장소 메서드 `Users.create_signup_user`가 중복 사전 검사와 사용자·비밀번호·인증 레코드의 단일 트랜잭션을 담당합니다.
- `AuthService.signup`은 비밀번호 해시, 저장소 호출, 커밋 충돌의 도메인 오류 변환, 가입 후 이메일 흐름을 조율합니다.
- 프론트엔드 `api/authError.ts`에서 오류 코드와 번역 문구를 연결하며 가입·로그인·재전송·비밀번호 재설정 화면이 공유합니다.
- 기존 `detail.error` 응답 형식, 이름·이메일 고유 제약, 테이블과 화면 테마는 유지합니다. Blueprint의 OAuth/다중 인증 테이블은 도입하지 않습니다.
- SQLite/PostgreSQL 제약 오류를 구분하며, 알 수 없는 서버 메시지는 UI에서 원문 대신 화면별 기본 안내로 표시합니다.


</details>

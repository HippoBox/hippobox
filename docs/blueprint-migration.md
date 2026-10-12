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

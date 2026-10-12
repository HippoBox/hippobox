# HippoBox

Personal knowledge store with FastAPI, semantic search and MCP tools.
The Python package includes the React frontend and provides `hippobox run`.

```sh
hippobox run --host 127.0.0.1 --port 8000
```

Configure the environment before starting. SQLite and local Qdrant are supported;
set `VDB_ENABLED=false` to use the SQL knowledge store without embeddings.
Redis is required for login sessions; `REDIS_IN_MEMORY=true` is for local development.
Production requires `APP_MODE=production`, `LOGIN_ENABLED=true` and a unique
`SECRET_KEY` of at least 32 characters. Rotating it invalidates existing JWTs.

MCP is served at `/mcp`. Existing `Authorization: Bearer sk-...` clients remain
supported without reissuing keys.

## 개발

저장소 루트에서 `make install`, `make verify-plan`, `make verify`를 실행합니다.
기존 테마·UI·DB 스키마·API 키 형식은 유지합니다. 실제 데이터를 변경하는
`make db-migrate`는 운영자가 명시적으로 실행할 때만 수행합니다.
기존 Alembic 정규화 이력은 PostgreSQL 전용입니다. SQLite의 현재 스키마는
서버 초기화로 생성되며, 오래된 SQLite 스키마는 별도의 변환 설계가 필요합니다.

회원가입은 사용자·비밀번호·인증 레코드를 하나의 트랜잭션으로 저장합니다.
이름과 이메일은 고유해야 하며, SQLite/PostgreSQL에서 중복되면 HTTP 409와
`NAME_ALREADY_EXISTS` 또는 `EMAIL_ALREADY_EXISTS`를 반환합니다.
가입 실패 응답에는 SQL 문이나 입력값을 포함하지 않습니다.

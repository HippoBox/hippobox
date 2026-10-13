# ChatGPT MCP 연결

HippoBox는 기존 API 키 연결과 별도로 OAuth authorization code + PKCE(S256)를 지원합니다.
Google/GitHub 로그인용 `OAUTH_ENABLED`와는 다른 기능입니다. Resend, Celery worker 없이
SQLite 단일 컨테이너에서도 사용할 수 있습니다.

## 서버 설정

공개 HTTPS 주소가 준비된 서버의 `.env`에 다음을 설정하고 새 이미지를 실행하세요.
이 문서의 설정은 배포 시 적용할 값이며, 릴리즈 발행만으로 운영 서버가 변경되지는 않습니다.

```dotenv
MCP_OAUTH_ENABLED=true
PUBLIC_APP_URL=https://hippobox.org
PUBLIC_API_URL=https://hippobox.org
LOGIN_ENABLED=true
```

`PUBLIC_API_URL`은 경로 없는 서버 origin입니다. 프론트엔드와 API는 같은 origin으로
제공하는 것을 권장합니다. Caddy는 `/.well-known/*`, `/oauth/*`, `/mcp`를 백엔드로 전달해야 합니다.
저장된 토큰의 대상 주소를 검증하므로 도메인을 바꾸면 MCP 클라이언트에서 다시 연결하세요.

단일 컨테이너 배포는 기존 `compose.local.yml`을 사용합니다. SQLite의
`mcp_oauth_record` 테이블에 클라이언트·동의 요청·코드·토큰을 저장합니다. 새 테이블만
추가하며 기존 사용자·지식 데이터는 변경하지 않습니다. 업데이트 전 데이터 디렉터리를
백업하고, `/data`를 기존 영속 디렉터리에 계속 연결하세요.

```sh
cd ~/hippobox/docker
docker compose --env-file .env -f compose.local.yml pull
docker compose --env-file .env -f compose.local.yml up -d --wait
```

## ChatGPT에 입력할 값

| 항목 | 값 |
| --- | --- |
| 이름 | HippoBox |
| 아이콘 | `hippobox-mcp-icon.png` — 256×256, 4,654바이트 |
| 서버 URL | `https://hippobox.org/mcp` |
| 인증 | OAuth |
| 고급 OAuth → 클라이언트 등록 | **동적 클라이언트 등록(DCR)** |
| 클라이언트 ID / 시크릿 | 입력하지 않음 — 자동 등록 |
| 토큰 엔드포인트 인증 방식(표시되는 경우) | `none` (공개 클라이언트 + PKCE) |
| 기본 권한 범위 | `knowledge:read knowledge:write` |

현재 화면의 **사용자 정의 OAuth 클라이언트**를 DCR로 변경하세요. API 키를 클라이언트
ID나 시크릿에 넣지 않습니다. 생성 후 HippoBox 로그인 화면에서 로그인하고, 요청한 지식
접근 권한을 확인한 뒤 **연결 허용**을 누르면 ChatGPT로 돌아갑니다. 조회만 허용하려면
권한 범위를 `knowledge:read`로 설정합니다.

아이콘은 HippoBox의 MCP 안내 화면 또는 GitHub 릴리즈에서 내려받을 수 있습니다.
서버의 `/hippobox-mcp-icon.png`에서도 제공됩니다(프론트엔드 기본 경로 사용 시).

OAuth 설정을 찾지 못한다면 **새 버전 적용 여부**, `MCP_OAUTH_ENABLED`, 공개 HTTPS 주소를 확인하고
ChatGPT에서 탐색을 다시 시도하세요. 다음 URL은 HTML 대신 JSON을 반환해야 합니다.

```sh
curl -fsS https://hippobox.org/.well-known/oauth-authorization-server
curl -fsS https://hippobox.org/.well-known/oauth-protected-resource/mcp
curl -i https://hippobox.org/mcp
```

마지막 요청은 인증 정보가 없으므로 `401`과 `WWW-Authenticate: Bearer resource_metadata=...`를
반환하는 것이 정상입니다.

## 로컬 개발·검증

로컬 브라우저에서 OAuth 화면을 확인할 수 있습니다. ChatGPT의 원격 연결에는 외부에서
접근 가능한 HTTPS 서버가 필요합니다. localhost만으로 ChatGPT 원격 연결이 완료되지는 않습니다.

```sh
make frontend-build
MCP_OAUTH_ENABLED=true PUBLIC_APP_URL=http://127.0.0.1:8000 \
  PUBLIC_API_URL=http://127.0.0.1:8000 make backend-dev-local
```

실제 개발 DB 대신 임시 SQLite·임시 계정으로 검증하려면:

```sh
cd src/backend
.venv/bin/python -m pytest tests/test_mcp_oauth.py
cd ../frontend
npx playwright test tests/mcp-oauth.spec.ts
```

기본 등록 허용 콜백은 ChatGPT의 `https://chatgpt.com/connector_platform_oauth_redirect`와
`https://chatgpt.com/connector/oauth/{callback_id}`입니다. 다른 클라이언트의 콜백을 추가하려면
`MCP_OAUTH_REDIRECT_URIS`에 **정확한 URL을 공백으로 구분**하여 넣으세요. 와일드카드는 지원하지 않습니다.
`CIMD` 및 고정 시크릿 클라이언트 방식은 현재 지원하지 않습니다.

## 연결 해제와 토큰 수명

- HippoBox → MCP 안내 → 연결된 MCP 클라이언트 → **연결 해제**로 해당 연결의 모든 토큰을 폐기합니다.
- 인증 코드는 2분, 로그인·동의 요청은 10분, 액세스 토큰은 1시간, 갱신 토큰은 30일 동안 유효합니다.
- 갱신 토큰은 사용할 때 교체합니다. 이미 사용한 코드·갱신 토큰이 다시 제출되면 해당 연결의 토큰을 폐기합니다.
- 코드·토큰은 원문 대신 SHA-256 해시로 조회합니다. 토큰은 지식 API에만 사용할 수 있고 계정·관리 API에는 사용할 수 없습니다.
- 기존 `Authorization: Bearer sk-...`와 `X-API-Key` 연결은 계속 사용할 수 있습니다. 이제 MCP 도구 목록 조회에도 유효한 인증이 필요합니다.

구현 기준: [OpenAI 공식 MCP OAuth 안내](https://developers.openai.com/plugins/build/auth).

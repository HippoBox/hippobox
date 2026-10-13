## HippoBox 0.3.0

ChatGPT에서 HippoBox 계정으로 로그인하고 MCP 지식 접근을 승인할 수 있습니다.
기존 API 키 연결과 HippoBox 테마·벡터 검색은 유지합니다.

### 변경 사항

- MCP OAuth 검색 메타데이터, 동적 클라이언트 등록(DCR), PKCE S256 인증 코드 교환.
- HippoBox 로그인 후 명시적인 접근 동의, 조회/쓰기 권한 분리.
- SQLite/PostgreSQL에 OAuth 연결 저장, 갱신 토큰 교체 및 재사용 감지, 연결 해제.
- MCP 토큰의 계정·관리 API 접근 차단, 모든 MCP HTTP 요청의 인증 검증.
- 기존 화면에 ChatGPT 연결 안내·연결 해제 UI 추가.
- 256×256 PNG 아이콘(4,654바이트)을 앱과 릴리즈에 포함.
- 단일 컨테이너·SQLite 배포 파일도 릴리즈에 자동 첨부.

### 실행 및 업데이트

이미지: `ghcr.io/hippobox/hippobox:0.3.0` (amd64 / arm64)

PyPI: `pip install hippobox==0.3.0`

OAuth를 사용할 때 `.env`에 설정하세요.

```dotenv
HIPPOBOX_IMAGE=ghcr.io/hippobox/hippobox:0.3.0
MCP_OAUTH_ENABLED=true
PUBLIC_APP_URL=https://hippobox.org
PUBLIC_API_URL=https://hippobox.org
```

ChatGPT에서 서버 URL `https://hippobox.org/mcp`, 인증 `OAuth`, 클라이언트 등록 **DCR**을
선택합니다. 클라이언트 ID·시크릿은 입력하지 않습니다. 기본 권한 범위는
`knowledge:read knowledge:write`입니다. 소셜 로그인용 `OAUTH_ENABLED`와는 별도입니다.

0.2.0에서 업데이트하면 새로운 `mcp_oauth_record` 테이블만 생성합니다. 기존 사용자·지식·API 키를
유지하며 재임베딩이 필요하지 않습니다. 업데이트 전 영속 데이터 디렉터리를 백업하세요.
0.1에서 직접 업데이트할 때는 기존 플랫폼 마이그레이션 절차가 필요합니다.

OAuth는 기본 비활성화입니다. 릴리즈 발행이 실행 중인 운영 서버를 자동 업데이트하지는 않습니다.
ChatGPT의 실제 계정 연결은 공개 HTTPS 서버에 적용한 뒤 진행해야 합니다.

검증: 격리된 SQLite에서 OAuth·기존 인증·지식 회귀 테스트, 라이트/다크 브라우저에서
로그인→동의→콜백→토큰 교환·연결 해제, 패키지 설치·정적 프론트엔드 검증.

[ChatGPT 연결 안내](https://github.com/HippoBox/hippobox/blob/v0.3.0/docs/mcp-chatgpt.md) ·
[배포 안내](https://github.com/HippoBox/hippobox/blob/v0.3.0/docs/deployment.md)

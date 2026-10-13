# 공용 Caddy (Linux)

Caddy는 앱 저장소/Compose 밖의 `~/shared-caddy`에서 독립적으로 운영합니다.
호스트 네트워크로 80/443을 받고 호스트의 루프백 앱 포트에 연결하므로 앱별
Docker 네트워크의 생성/삭제와 분리됩니다.

| 주소 | upstream |
| --- | --- |
| `BLUEPRINT_DOMAIN` | `127.0.0.1:8000` |
| `HIPPOBOX_DOMAIN` | `127.0.0.1:8001` |
| `http://PREVIEW_HOST` | HippoBox 임시 IP 미리보기 |

두 앱의 포트는 `127.0.0.1`에만 바인딩하고 신뢰하는 프록시 헤더를 허용합니다.
Caddy의 관리 API는 호스트 루프백에만 열립니다. 이 구성은 Linux 서버용입니다.

## 설치와 기존 Caddy 전환

이 디렉터리의 파일들을 `~/shared-caddy`로 복사하고 `.env.example`을 `.env`로
복사해 도메인과 IP를 설정합니다. 비밀키/인증서를 저장소에 넣지 않습니다.

```sh
cd ~/shared-caddy
docker volume create shared_caddy_data
docker volume create shared_caddy_config
docker compose config --quiet
docker compose run --rm --no-deps caddy caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile
```

기존 Caddy가 있다면 기존 `/data`(인증서)와 `/config`를 백업한 뒤 위 공용 볼륨으로
복사합니다. 설정 검증 이후에만 기존 Caddy를 중지하고 공용 Caddy를 실행합니다.
같은 80/443 포트를 두 프록시가 동시에 사용할 수 없습니다.

```sh
docker compose up -d --wait
docker compose ps
```

기존 서비스의 실제 HTTPS 응답과 새 앱 라우팅을 확인한 뒤 이전 Caddy 컨테이너와
전용 볼륨을 제거합니다. Blueprint 앱·DB·Redis 컨테이너와 원본 소스 파일은 변경할
필요가 없습니다. 전환 실패 시 공용 Caddy를 중지하고 이전 컨테이너/인증서 백업으로
복구합니다. 공용 볼륨은 external이므로 Compose 종료로 삭제되지 않습니다.

## 운영

```sh
cd ~/shared-caddy
docker compose logs --tail=100 caddy
docker compose exec caddy caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile
docker compose exec caddy caddy reload --config /etc/caddy/Caddyfile --adapter caddyfile
```

공용 프록시로 전환한 서버에서는 Blueprint의 `docker-compose.https.yml`을 다시
함께 실행하지 않습니다. 원본 저장소 수정 없이 애플리케이션만 관리하도록 제공된
wrapper를 사용합니다. 다른 경로/프로젝트라면 BLUEPRINT_ROOT/BLUEPRINT_PROJECT를 지정합니다.

```sh
~/shared-caddy/blueprint-apps.sh ps
~/shared-caddy/blueprint-apps.sh up -d --no-build app celery-worker

cd ~/hippobox/docker
docker compose --env-file .env -f compose.local.yml up -d --wait
```

기존 Blueprint `make docker-deploy`가 HTTPS overlay를 선택하도록 설정되어 있다면
Caddy를 다시 생성할 수 있으므로 이 서버에서는 위 앱 전용 명령을 사용합니다.

## HippoBox 도메인 연결

`hippobox.org`의 A 레코드를 서버 IPv4에 연결해야 공인 인증서가 발급됩니다.
DNS가 아직 없으면 Blueprint HTTPS는 계속 제공되지만 HippoBox 인증서 발급은 실패 후
재시도합니다. 이 상태에서는 IP HTTP 경로로 화면만 점검하고, 실제 계정/지식 입력은
HTTPS가 준비된 뒤 진행합니다.

DNS/TLS가 확인되면 HippoBox `.env`의 PUBLIC_APP_URL/PUBLIC_API_URL을
`https://hippobox.org`로 변경하고 앱을 재생성합니다. 마지막으로 Caddyfile의 임시
`http://PREVIEW_HOST` 블록을 제거한 뒤 validate/reload합니다.

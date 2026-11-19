# 구조

운영 콘솔은 두 부분으로 되어 있다.

- **admin API**(`map_project_admin/`, FastAPI): 브라우저용 JSON API. 계정·세션·감사를 소유하고, 나머지는 다른 서비스에 위임하거나 읽기만 한다.
- **admin-web**(`web/`, React + Vite → nginx): 같은 출처의 `/api/` 를 admin API 로 넘기는 정적 SPA.

```
브라우저 ──▶ admin-web(nginx) ──/api/──▶ admin API ──┬─▶ control DB (admin_data: 계정·세션·감사, 읽기·쓰기)
                                                     ├─▶ 대상 DB (hub_data, 읽기 전용)
                                                     ├─▶ Redis (스트림·쿼터·캐시 진단, 읽기 전용)
                                                     ├─▶ user  /internal/admin/*  (회원·작업·실패 큐·신고)
                                                     ├─▶ hub   /internal/*        (기상청 갱신·격자·금지구역)
                                                     ├─▶ user·agent·hub·OSRM 헬스
                                                     └─▶ 외부 API 6종(수동 점검 때만)
```

## 1. 요청 처리 순서
1. **환경 선택**(`main.py` 의 `target_environment` 미들웨어): `X-Map-Environment` 헤더(또는 `environment` 쿼리)로 대상 환경을 고른다. 인증·운영자 관리·`/environments`·헬스·지표 요청은 대상을 고르지 않고 control 설정만 쓴다. 모르는 환경이면 400.
2. **인증**(`security.py` 의 `require_operator`): 세션 쿠키로 운영자를 찾고 역할(owner·operator·viewer)과 허용 환경을 확인한다.
3. **쓰기 전 감사**: GET·HEAD·OPTIONS 가 아닌 요청은 viewer 를 거부하고, `X-Map-Environment` 헤더가 선택 환경과 같은지 확인한 뒤, 감사 행(`request.started`)을 먼저 저장한다. 저장하지 못하면 요청을 실행하지 않는다.
4. **라우터**(`routers/`): DB·Redis 를 읽거나 `upstream.py` 로 다른 서비스에 위임한다.
5. **감사 완료**: 응답 상태코드로 감사 행을 마무리한다(`audit.finish`).
6. **응답 헤더**: 실제로 쓴 환경 이름(`X-Map-Environment`)과 `Cache-Control: no-store` 를 붙인다.

## 2. 실행 모드
| 모드 | 설정 | control DB | 대상 |
|---|---|---|---|
| 단일 호스트 | `ADMIN_CONTROL_DATABASE_URL` 비움 | `ADMIN_DATABASE_URL` 하나를 control 과 기본 대상이 함께 쓴다 | 기본 환경(`ADMIN_ENVIRONMENT`) 하나. 빠른 시작이 이 모드다. |
| 중앙 | `ADMIN_CONTROL_DATABASE_URL` 설정 | 전용 DB, 런타임 역할은 DDL·감사 삭제 권한 없음 | 기본 환경을 포함한 모든 대상을 `ADMIN_TARGETS` 에 적는다. 대상 설정은 control 설정을 물려받지 않는다. |

`ADMIN_TARGETS` 는 환경 이름 → 그 환경의 연결 값 사전(JSON)이다. 안쪽 키는 환경변수 이름과 같다. 필수 키는 `ADMIN_USER_BASE_URL`·`MAP_PROJECT_AGENT_BASE_URL`·`MAP_PROJECT_HUB_BASE_URL`·`MAP_PROJECT_INTERNAL_SERVICE_TOKEN` 이고, DB·Redis 를 빼면 그 대상은 위임 API 만 쓴다(SQL 화면은 503).

```json
{
  "test": {
    "ADMIN_USER_BASE_URL": "http://user:8080",
    "MAP_PROJECT_AGENT_BASE_URL": "http://agent:8000",
    "MAP_PROJECT_HUB_BASE_URL": "http://hub:8000",
    "MAP_PROJECT_INTERNAL_SERVICE_TOKEN": "<그 환경의 내부 토큰>",
    "MAP_PROJECT_USER_ADMIN_INTERNAL_TOKEN": "<그 환경 user 의 관리 전용 토큰>",
    "MAP_PROJECT_HUB_ADMIN_INTERNAL_TOKEN": "<그 환경 hub 의 관리 전용 토큰>",
    "ADMIN_DATABASE_URL": "<읽기 전용 계정의 DSN — 생략 가능>"
  }
}
```
`.env` 에는 한 줄 JSON 으로 넣는다. 빈 값(`ADMIN_TARGETS=`)은 설정하지 않은 것(`{}`)으로 본다([T-CFG-01](troubleshooting.md#t-cfg-01)).

## 3. 모듈 역할
| 모듈 | 역할 |
|---|---|
| `main.py` | 앱 생성, 환경 선택 미들웨어, CORS(설정했을 때만), Prometheus 지표, 라우터 등록, `/health`·`/health/ready`, 세션 보호 Swagger |
| `config.py` | 설정(`Settings`), 요청별 대상 설정 선택(`select_environment`), 대상 키·비밀 목록 |
| `security.py` | 세션 인증, 역할·환경 권한, 쓰기 전 감사 |
| `accounts.py` | 운영자 계정(bcrypt), 세션, 로그인 시도 제한(DB 공유 카운터), 최초 계정 생성 |
| `audit.py` | 감사 로그 기록·마무리·조회(환경별로 나눠 보임) |
| `db.py` | control 읽기·쓰기 풀과 대상 읽기 전용 풀 |
| `repo.py` | `hub_data` 집계와 DB 뷰어(테이블 목록·스키마·행·CSV) |
| `redis_probe.py` | Redis 진단(스트림 길이·미확인 수, Gemini 쿼터, 캐시 키 개수) — 값은 읽지 않는다 |
| `health_client.py` | user·agent·hub HTTP 헬스, PostgreSQL·Redis, OSRM 두 프로필 |
| `external_status.py`, `gemini_client.py` | 외부 API 설정 여부·마스킹한 키, 수동 연결 점검 |
| `upstream.py`, `bff_client.py`, `hub_client.py` | 위임 호출: 관리 전용 자격, 주소·경로 제한, 오류 본문 고정값 변환 |
| `routers/*` | `/api/v1` 경로별 처리 |

## 4. 저장소와 권한
- **control DB**(`admin_data` 스키마): `audit_logs`, `admin_accounts`, `admin_sessions`, `login_attempts`. Alembic 마이그레이션(`migrations/revisions/0001`~`0003`)이 테이블을 만든다. 스키마는 미리 있어야 한다(마이그레이션이 만들지 않는다).
  - 중앙 모드에서는 마이그레이션 역할과 런타임 역할을 나눈다: `scripts/bootstrap-control-db.sql`(스키마·역할 준비) → 일회성 `alembic upgrade head`(마이그레이션 역할) → `scripts/grant-control-runtime.sql`(런타임 권한). 서빙 프로세스는 `ADMIN_RUN_MIGRATIONS=false` 로 마이그레이션 비밀을 받지 않는다.
- **대상 DB**(`hub_data`): 읽기 전용 트랜잭션(`default_transaction_read_only=on`), 연결 2개·overflow 없음, statement·lock·connect 타임아웃. DB 뷰어는 `hub_data` 의 실제 테이블 목록만 허용하고, 정렬·필터 컬럼은 카탈로그와 대조한다.
- **Redis**: 정의 서비스의 키를 읽기만 한다([계약](contracts.md#4-읽기-전용-저장소-키)).

## 5. 외부 의존성
| 대상 | 쓰는 곳 | 없으면 |
|---|---|---|
| PostgreSQL(control) | 로그인·감사 | 기동 실패(계정이 비어 있고 최초 계정 값이 없을 때도 실패) |
| PostgreSQL(대상) | 운영 지표·DB 뷰어 | 해당 화면 503 |
| Redis | 진단 | `configured: false` |
| user·hub | 위임 | 502 `upstream_unavailable` |
| OSRM | 헬스·수동 점검 | 헬스 항목 `ok: null, configured: false` |
| 외부 API(기상청·카카오·네이버·두루누비·OSRM·Gemini) | `POST /ops/external/{p}/probe` | `configured: false` |

외부 API 점검은 사람이 버튼을 눌렀을 때만 키 주인의 실제 쿼터로 1회 요청한다. 화면의 자동 새로고침은 외부 API 를 부르지 않는다. 키는 앞 4자·뒤 2자만 보인다.

## 6. 타임아웃과 한도
| 항목 | 기본값 | 환경변수 |
|---|---|---|
| DB 문장·잠금·연결 타임아웃 | 5초 | `ADMIN_DB_TIMEOUT_SEC` |
| 헬스 요청 | 3초 | `ADMIN_HEALTH_TIMEOUT_SEC` |
| Redis 요청 | 2초 | `ADMIN_REDIS_TIMEOUT_SEC` |
| 위임 요청 | 5초 | `ADMIN_INTERNAL_TIMEOUT_SEC` |
| Gemini 연결 점검 | 5초 | `ADMIN_GEMINI_TIMEOUT_SEC` |
| 외부 API 수동 점검 | 6초 | `ADMIN_EXTERNAL_PROBE_TIMEOUT_SEC` |
| 세션 수명 | 720분 | `ADMIN_SESSION_TTL_MIN` |
| 로그인 시도 | 300초에 10회(모든 프로세스 합산) | `ADMIN_LOGIN_MAX_ATTEMPTS`, `ADMIN_LOGIN_WINDOW_SECONDS` |
| DB 뷰어 페이지 | 기본 50, 최대 500행 | `ADMIN_DB_PAGE_SIZE_DEFAULT`, `ADMIN_DB_PAGE_SIZE_MAX` |
| CSV 내보내기 | 50000행 | `ADMIN_DB_EXPORT_MAX_ROWS` |
| 운영자 비밀번호 | 12자 이상, 72바이트 이하(bcrypt 한도) | — |
| 채팅 전송 제한 조치 | 1~720시간 | — |
| 모니터링 패널 iframe 높이 | 120~2000px 로 보정 | `ADMIN_MONITORING_PANELS` |

## 7. 기동과 마이그레이션
`entrypoint.sh` 는 `ADMIN_RUN_MIGRATIONS` 가 `true` 이거나, `auto`(기본)이면서 단일 호스트 모드일 때 `alembic upgrade head` 를 먼저 실행하고 uvicorn 을 띄운다. 권한이나 스키마가 없으면 여기서 바로 멈춘다([T-DB-03](troubleshooting.md#t-db-03)). 컨테이너 헬스체크는 `/health/ready` 로, control DB 에 활성 owner 가 있어야 정상이다.

## 8. 설계 메모
- **revision ID 길이**: Alembic 버전 표의 `version_num` 은 32자다. revision ID 는 그 안에 들어가게 짧게 짓는다(`0002_admin_accounts_sessions`).
- **기상청 점검**: 전날 05시 발표분을 1건 조회한다. `NO_DATA(03)` 도 키·연결이 정상인 응답으로 본다.
- **헬스 `ok` 는 세 값**: `true`(정상), `false`(장애), `null`(미구성·판단 불가). 알 수 없는 응답 본문은 정상으로 세지 않는다.
- **위임 응답 원문 비노출**: 업스트림 오류 본문은 브라우저로 넘기지 않고 고정 코드로 바꾼다. 성공 응답도 형식 검증을 통과해야 내보낸다.

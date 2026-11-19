# 계약

운영 콘솔(admin)이 브라우저에 내놓는 API, 다른 서비스에 위임하는 호출, 읽기만 하는 저장소 키를 정리한다. 코드 위치는 `map_project_admin/` 기준이다.

## 1. 소유 관계

| 대상 | 소유 | admin 의 권한 |
|---|---|---|
| `admin_data` 스키마(`audit_logs`, `admin_accounts`, `admin_sessions`, `login_attempts`) | admin(Alembic 마이그레이션) | 읽기·쓰기. 런타임 역할은 DDL·감사 행 삭제 권한이 없다(`scripts/grant-control-runtime.sql`). |
| `hub_data` 스키마 | hub | 읽기 전용(`SELECT`). 대상 환경별 읽기 전용 트랜잭션 풀. 쓰기는 hub 내부 API 로 위임. |
| `user_service`·`langgraph` 스키마 | user·agent | 접근하지 않는다. DB 뷰어 화이트리스트에도 없다. |
| 회원·추천 작업·실패 큐·신고 | user | `/internal/admin/*` 로 위임 |
| 격자·금지구역·기상청 갱신 | hub | `/internal/*` 로 위임 |
| Redis 스트림·쿼터·캐시 | agent·hub·user | 읽기 전용 진단(값은 읽지 않고 길이·개수만) |

## 2. 브라우저용 API (`/api/v1`)

### 공통 규칙
- 인증: `POST /api/v1/auth/login` 이 세션 쿠키(`admin_session`, HttpOnly, SameSite=Lax, `Secure` 는 `ADMIN_SESSION_COOKIE_SECURE`)를 준다. 나머지 `/api/v1/*` 는 세션이 없으면 401.
- 환경 선택: 요청 헤더 `X-Map-Environment`(또는 쿼리 `environment`)로 대상 환경을 고른다. 없으면 `ADMIN_ENVIRONMENT`. 모르는 환경이거나 연결 설정이 덜 됐으면 400 `{"detail": "unknown or incomplete environment"}`. 응답에는 실제로 쓴 환경 이름이 `X-Map-Environment` 로 돌아온다.
- 인증·운영자 관리·`/environments`·`/health`·`/health/ready`·`/metrics` 는 대상 환경을 고르지 않고 control DB 만 쓴다.
- 쓰기(GET·HEAD·OPTIONS 가 아닌 요청):
  - viewer 는 403 `read-only operator`.
  - `X-Map-Environment` 헤더가 실제 선택 환경과 같아야 한다(없으면 403). 브라우저 폼만으로는 이 헤더를 붙일 수 없어 교차 사이트 요청을 막는다.
  - 서비스 호출 전에 감사 행(`request.started`)을 먼저 저장한다. 저장에 실패하면 요청도 실패한다.
- 환경 권한: owner 가 아닌 운영자는 `allowed_environments` 에 있는 환경만 쓸 수 있다(그 밖은 403).
- 응답 헤더: `Cache-Control: no-store`.
- 오류 형식: FastAPI 기본 `{"detail": …}`. 위임 실패는 `detail` 이 `{"code", "message"}` 객체다([오류 변환](#33-오류-변환) 참고). DB 예외는 503 `{"detail": "database unavailable"}`(원문 비노출).

### 경로
| 메서드·경로 | 역할 | 설명 |
|---|---|---|
| `POST /auth/login` | 없음 | 본문 `{username(1~100자), password(1~1024자)}`. 응답 `{username, role}`. 실패 401, 시도 제한 초과 429(`Retry-After`). 결과(성공·실패·차단)를 감사에 남긴다. |
| `POST /auth/logout` | 없음 | 204. 실제 세션이 있을 때만 감사에 남긴다. |
| `GET /auth/me` | 운영자 | 현재 운영자와 역할 |
| `GET /environments` | 운영자 | 쓸 수 있는 환경 이름 목록(연결 값은 내보내지 않음) |
| `GET /operators` · `POST /operators` · `PATCH /operators/{id}` | owner | 운영자 계정 관리. 역할 `owner`·`operator`·`viewer`, 환경 최대 20개, 비밀번호 12자 이상·72바이트 이하, username `^[A-Za-z0-9_.@-]{1,100}$` |
| `GET /ops/overview` | 운영자 | 헬스·폴링·Gemini 쿼터·스트림 요약 |
| `GET /ops/health` | 운영자 | 서비스·인프라·라우팅 헬스. 항목의 `ok` 는 `true`·`false`·`null`(미구성·판단 불가) |
| `GET /ops/polling` · `/ops/forecast-rows` · `/ops/places-stats` | 운영자 | `hub_data` 집계 |
| `GET /ops/gemini` | 운영자 | 연결 점검(모델 목록 메타 호출) + 일일 쿼터 |
| `GET /ops/streams` | 운영자 | 추천 작업 스트림·실패 큐·미확인 메시지 수 |
| `GET /ops/external` | 운영자 | 외부 API 6종 설정 여부·마스킹한 키·캐시 키 수. 외부 호출 없음 |
| `POST /ops/external/{provider}/probe` | operator 이상 | 외부 API 에 최소 요청 1회(실제 쿼터 사용). provider = `kma`·`kakao`·`naver`·`durunubi`·`osrm`·`gemini` |
| `GET /ops/monitoring` | 운영자 | `ADMIN_MONITORING_PANELS` 슬롯 |
| `GET /db/tables` · `/db/tables/{t}/schema` · `/db/tables/{t}` · `/db/tables/{t}/export.csv` | 운영자 | `hub_data` 화이트리스트 테이블만(그 밖 404). 정렬·필터 컬럼은 카탈로그와 대조(틀리면 422). `limit` 은 `ADMIN_DB_PAGE_SIZE_MAX` 로 자름, CSV 는 `ADMIN_DB_EXPORT_MAX_ROWS` 까지 |
| `GET /users` · `/users/{id}` | 운영자 | 회원 목록(마스킹)·상세(원문). `page`≥0, `size` 1~100. 목록 조회는 검색어 원문 없이 감사, 상세는 감사 후 열람. viewer 는 상세 원문 불가 |
| `GET /jobs/stats` · `/jobs` · `/jobs/dlq` | 운영자 | 추천 작업 통계·목록(`size` 1~100)·실패 큐(`limit` 1~500) |
| `POST /actions/kma/run-now?which=short\|mid\|housekeep` | operator 이상 | 기상청 강제 갱신 |
| `PATCH /actions/grids/{id}` | operator 이상 | 본문 `{is_active}`. 감사에 변경 전후 |
| `GET /actions/forbidden-zones[/{id}]` | 운영자 | 금지구역 조회 |
| `POST` · `PUT /actions/forbidden-zones[/{id}]` | operator 이상 | 본문 `{name(1~200자), reason(≤1000자), geometry(GeoJSON)}` |
| `DELETE /actions/forbidden-zones/{id}` | operator 이상 | 삭제 |
| `POST /actions/dlq/reprocess` · `/actions/dlq/discard` | operator 이상 | 본문 `{ids: [..]}`(1개 이상) |
| `GET /audit` | 운영자 | 필터 `actor`·`action`·`from`·`to`, `limit` 은 `ADMIN_DB_PAGE_SIZE_MAX` 로 자름 |
| `GET /moderation/reports?status=&limit=` | 운영자 | 신고 접수 메타데이터. `status` = `OPEN`·`IN_REVIEW`·`ACTIONED`·`DISMISSED`, `limit` 1~100. owner 도 `X-Map-Environment` 필수 |
| `GET /moderation/reports/{id}` | operator 이상 | 신고 설명·현재 메시지 원문. 감사 저장 후 열람, `no-store` |
| `POST /moderation/reports/{id}/actions` | 조치별 | 본문 `{action_id(UUID), action, restriction_hours?}`(추가 필드 거부). `REVIEW`·`DISMISS`·`RESOLVE` 는 operator 이상, `HIDE_CHAT_MESSAGE`·`RESTRICT_CHAT`·`LIFT_CHAT_RESTRICTION` 은 owner. `restriction_hours`(1~720)는 `RESTRICT_CHAT` 에만. 화면은 결과가 애매한 실패를 다시 시도할 때 같은 `action_id` 를 보낸다(`web/src/pages/ModerationPage.tsx`) — 중복 조치를 거르는 것은 user 서비스의 몫이다 |
| `GET /health` | 없음 | liveness |
| `GET /health/ready` | 없음 | control DB 에 활성 owner 계정이 있으면 200, 아니면 503 |
| `GET /metrics` | 없음 | Prometheus 지표. 인증이 없으므로 API 포트를 밖에 열지 않는다. 함께 배포하는 nginx(`web/nginx.conf`)는 `/api/` 만 넘기고 `/metrics` 는 넘기지 않는다 |
| `GET /docs` · `/openapi.json` | 운영자 | Swagger UI |

### 신고 응답 필드 길이
| 필드 | 제한 |
|---|---|
| `reason` | ≤32자 |
| `resolution` | ≤24자 |
| `description` | ≤1000자 |
| `current_message` | ≤10000자 |
| `admin_actor` | ≤96자 |
| `actions` | ≤1000개 |
| `content_type` | `CHAT_MESSAGE`·`TRIP`·`VISION`·`REVIEW_SUMMARY` |

업스트림 응답이 이 형식을 벗어나면 본문을 내보내지 않고 502 로 바꾼다.

## 3. 위임 호출 (admin → user·hub)

### 3.1 경로
| 대상 | 메서드·경로 | 자격 |
|---|---|---|
| user | `GET /internal/admin/users`, `/internal/admin/users/{id}` | `MAP_PROJECT_USER_ADMIN_INTERNAL_TOKEN` |
| user | `GET /internal/admin/recommend-jobs/stats`, `/internal/admin/recommend-jobs`, `/internal/admin/dlq` | 같음 |
| user | `POST /internal/admin/dlq/reprocess`, `/internal/admin/dlq/discard` | 같음 |
| user | `GET·POST /internal/admin/moderation/reports[/{id}[/actions]]` | 같음 + `X-Admin-Actor` |
| hub | `POST /internal/kma/run-now?which=…` | `MAP_PROJECT_HUB_ADMIN_INTERNAL_TOKEN` |
| hub | `PATCH /internal/grids/{id}` | 같음 |
| hub | `GET·POST·PUT·DELETE /internal/forbidden-zones[/{id}]` | 같음 |

### 3.2 헤더
| 헤더 | 값 |
|---|---|
| `X-Internal-Token` | 관리 전용 자격. 비었거나 `MAP_PROJECT_INTERNAL_SERVICE_TOKEN`·다른 관리 자격과 같으면 요청을 보내지 않는다. 선택한 대상 주소의 정해진 경로에만 붙이고 리다이렉트는 따라가지 않는다. |
| `X-Admin-Actor` | 신고 조치의 행위자. 운영자 이름 대신 불투명한 `admin_<control 계정 id>` |

### 3.3 오류 변환
업스트림 본문은 브라우저로 넘기지 않는다. 상태코드는 그대로, 본문은 아래 고정값으로 바꾼다.

| 업스트림 | 브라우저 `detail.code` |
|---|---|
| 400 · 422 | `invalid_request` |
| 401 | `upstream_unauthorized` |
| 403 | `upstream_forbidden` |
| 404 | `upstream_not_found` |
| 409 | `upstream_conflict` |
| 429 | `upstream_rate_limited` |
| 그 밖의 4xx·5xx | `upstream_failed` |
| 연결 실패·타임아웃 | 502 `upstream_unavailable` |

신고 관리 경로는 400·403·404·409·429·503 만 그대로 두고 나머지는 502 로 바꾸며, `detail` 은 "상태를 새로 확인한 뒤 다시 시도" 하라는 고정 문구다.

## 4. 읽기 전용 저장소 키

| 저장소 | 키·이름 | 정의 | admin 이 읽는 것 |
|---|---|---|---|
| Redis DB2 | 스트림 `agent:jobs:done`, `agent:jobs:status`, 실패 큐 `agent:jobs:done:dlq`, 소비자 그룹 `bff-result` | agent(발행), user(소비) | 길이, 그룹의 미확인 수 |
| Redis DB3 | `gemini:daily:{YYYYMMDD}`(KST), `gemini:tokens` | agent | 오늘 사용량, 토큰 버킷 |
| Redis DB4 | `kakao:places:*`, `naver:blog:*`, `osrm:*` | hub | 키 개수만(값은 읽지 않음) |

DB 번호와 스트림 이름은 환경변수로 바꿀 수 있다: `MAP_PROJECT_REDIS_DB_STREAMS`·`MAP_PROJECT_REDIS_DB_RATELIMIT`·`MAP_PROJECT_REDIS_DB_HUB_CACHE`(다른 서비스와 같은 값), `ADMIN_STREAM_DONE`·`ADMIN_STREAM_STATUS`(admin 만 읽음), `MAP_PROJECT_STREAM_DLQ`·`MAP_PROJECT_STREAM_GROUP`(user 와 같은 값). 정의 서비스가 이름을 바꾸면 admin 설정도 같이 바꾼다.

## 5. 환경변수
전체 목록과 기본값은 `.env.example` 과 `map_project_admin/config.py` 의 `Settings` 에 있다. 대상 환경별로 덮어쓸 수 있는 키는 `ADMIN_TARGETS` 의 각 항목에 넣는다. 대상 항목에는 `ADMIN_USER_BASE_URL`·`MAP_PROJECT_AGENT_BASE_URL`·`MAP_PROJECT_HUB_BASE_URL`·`MAP_PROJECT_INTERNAL_SERVICE_TOKEN` 이 필수이고, 비밀값은 control 설정에서 상속되지 않는다.

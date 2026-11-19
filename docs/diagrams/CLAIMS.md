# 다이어그램 근거표

그림의 모든 노드와 엣지가 무엇을 주장하는지, 그 근거가 어디에 있는지 적는다. 교차 검토는 이 표로 한다. 원본은 `src/`, 렌더는 `sh scripts/render_diagrams.sh`.

## console-architecture (운영 콘솔 구성)
| 그림 | 요소(노드/엣지) | 주장 | 근거 file:line | 확인 방법 |
|---|---|---|---|---|
| console-architecture | 노드 브라우저 | 운영자가 쓰는 브라우저. 모든 요청에 세션 쿠키를 보낸다 | `web/src/api/client.ts:121` | 코드 읽기 |
| console-architecture | 노드 admin-web | nginx 가 정적 SPA 를 서빙한다 | `web/Dockerfile:17-27`, `web/nginx.conf:36-38` | 코드 읽기 |
| console-architecture | 노드 admin API | FastAPI 앱, 경로는 `/api/v1` | `map_project_admin/main.py:62`, `map_project_admin/routers/*_router.py` 의 `prefix` | 코드 읽기 |
| console-architecture | 노드 control DB | `admin_data` 에 계정·세션·감사 | `migrations/revisions/001_create_audit_logs.py:46-59`, `002_create_admin_accounts_sessions.py:42-62` | 마이그레이션 읽기, `tests/test_accounts_database.py` |
| console-architecture | 노드 대상 DB | `hub_data` 를 읽기 전용으로 연다 | `map_project_admin/db.py:22`, `map_project_admin/repo.py:118-127` | 코드 읽기 |
| console-architecture | 노드 Redis | 스트림·쿼터·캐시를 읽기만 한다 | `map_project_admin/redis_probe.py:1-7`, `:37`, `:74`, `:107` | 코드 읽기 |
| console-architecture | 노드 user | 위임 경로 `/internal/admin/*` | `map_project_admin/bff_client.py:23` | 코드 읽기 |
| console-architecture | 노드 hub | 위임 경로 `/internal/*` | `map_project_admin/hub_client.py:19`, `:25` | 코드 읽기 |
| console-architecture | 노드 agent | 헬스 점검만 한다 | `map_project_admin/health_client.py:31` | 코드 읽기 |
| console-architecture | 노드 OSRM(기본 꺼짐) | 도보·자전거 두 프로필, 함께 띄우는 구성에서 기본으로 켜지지 않는다 | `map_project_admin/health_client.py:119-125`, map-project-infra `docker-compose.yml` 의 `osrm-foot`·`osrm-bicycle` `profiles: ["routing"]` | compose 렌더 |
| console-architecture | 노드 외부 API | 기상청·카카오·네이버·두루누비·Gemini(OSRM 은 별도 노드) | `map_project_admin/external_status.py:25`, 카카오 `:132`, 네이버 `:145`, 기상청 `:161`, 두루누비 `:184`, Gemini `:90-91`(`map_project_admin/gemini_client.py` 의 `check_gemini`) | 코드 읽기 |
| console-architecture | 노드 Prometheus(기본 꺼짐) | 모니터링 구성을 켤 때만 뜬다 | map-project-infra `docker-compose.admin.yml` 의 `prometheus` `profiles: ["monitoring"]` | compose 렌더 |
| console-architecture | 노드 Grafana 등(기본 꺼짐) | 설정했을 때만 화면에 iframe·링크로 붙는다 | `map_project_admin/config.py:19`, `:36`, `web/src/pages/MonitoringPage.tsx:73` | 코드 읽기 |
| console-architecture | 엣지 브라우저→admin-web | HTTPS, 로컬 실행만 http(세션 쿠키 Secure 기본) | `map_project_admin/routers/auth_router.py:41-43`, `.env.example` 의 `ADMIN_SESSION_COOKIE_SECURE` | `tests/test_security_boundaries.py::test_session_cookie_is_secure_by_default` |
| console-architecture | 엣지 admin-web→admin API | `/api/` 만 프록시 | `web/nginx.conf:24-26` | 코드 읽기 |
| console-architecture | 엣지 admin API→control DB | 읽기·쓰기(control 엔진) | `map_project_admin/db.py:14` | `scripts/verify-control-isolation.py` |
| console-architecture | 엣지 admin API→대상 DB | SELECT 만(읽기 전용 트랜잭션) | `map_project_admin/db.py:22` | 코드 읽기 |
| console-architecture | 엣지 admin API→Redis | 키 개수·스트림 길이·쿼터 | 스트림 `map_project_admin/redis_probe.py:37`, 쿼터 `:74`, 캐시 키 개수 `:114-116` | 코드 읽기, `tests/test_security_boundaries.py::test_redis_error_is_unavailable_not_empty_queue` |
| console-architecture | 엣지 admin API→user | 관리 위임, 전용 토큰 | `map_project_admin/upstream.py:57`, `:60` | `tests/test_admin_credential_isolation.py::test_all_bff_operations_use_dedicated_management_credential` |
| console-architecture | 엣지 admin API→hub | 관리 위임, 전용 토큰 | `map_project_admin/upstream.py:57`, `:73` | `tests/test_admin_credential_isolation.py::test_all_hub_operations_use_dedicated_management_credential` |
| console-architecture | 엣지 admin API→agent | 헬스 | `map_project_admin/health_client.py:31` | 코드 읽기 |
| console-architecture | 엣지 admin API→OSRM | 헬스·수동 점검 | `map_project_admin/health_client.py:119`, `map_project_admin/external_status.py:200-206` | 코드 읽기 |
| console-architecture | 엣지 admin API→외부 API | 사람이 요청할 때 1회, 사용하는 사람의 키 | `map_project_admin/routers/ops_router.py:72`, `map_project_admin/external_status.py:82` | `tests/test_smoke.py::test_external_probe_known` |
| console-architecture | 엣지 Prometheus→admin API | `/metrics` 수집 | `map_project_admin/main.py:121-122`, map-project-infra `monitoring/prometheus/prometheus.yml` 의 `admin:8000` 대상 | 코드 읽기 |
| console-architecture | 엣지 브라우저→Grafana 등 | 브라우저가 직접 iframe·링크로 연다(admin 이 중계하지 않음) | `web/src/pages/MonitoringPage.tsx:73` | 코드 읽기 |

## write-request (쓰기 요청 처리 순서)
| 그림 | 요소(노드/엣지) | 주장 | 근거 file:line | 확인 방법 |
|---|---|---|---|---|
| write-request | 레인 브라우저·admin API·control DB·hub | 쓰기 요청 하나에 관여하는 넷 | 아래 각 행 | — |
| write-request | 호출 브라우저→admin API | 세션 쿠키와 `X-Map-Environment` 헤더를 함께 보낸다 | `web/src/api/client.ts:112`, `:121` | 코드 읽기 |
| write-request | 자기 호출 admin API | 환경 선택 → 세션 확인 → viewer 거부 → 헤더 대조 | `map_project_admin/main.py:80`, `map_project_admin/security.py:39`, `:42` | `tests/test_security_boundaries.py::test_viewer_cannot_run_mutation`, `::test_mutation_requires_explicit_environment` |
| write-request | 호출 admin API→control DB(request.started) | 위임 전에 감사 행을 저장한다 | `map_project_admin/security.py:45` | — |
| write-request | 응답 control DB→admin API | 감사 저장이 실패하면 위임하지 않는다 | `map_project_admin/security.py:43-47` | `tests/test_security_boundaries.py::test_audit_failure_stops_upstream_action` |
| write-request | 호출 admin API→hub | 허브 관리 전용 토큰으로 `PATCH /internal/grids/{id}` | `map_project_admin/hub_client.py:25`, `map_project_admin/upstream.py:73` | `tests/test_admin_credential_isolation.py::test_all_hub_operations_use_dedicated_management_credential` |
| write-request | 응답 hub→admin API | 변경 전후 값, 실패는 고정 코드 | `map_project_admin/routers/actions_router.py:77`, `map_project_admin/upstream.py` 의 `UpstreamError` | `tests/test_upstream_privacy.py` |
| write-request | 호출 admin API→control DB(grids.toggle) | 변경 전후 값을 감사에 남긴다 | `map_project_admin/routers/actions_router.py:78-84` | `tests/test_smoke.py::test_action_grid_toggle_records_audit` |
| write-request | 호출 admin API→control DB(마무리) | `request.started` 행을 응답 상태코드로 마무리 | `map_project_admin/main.py:100` | `tests/test_accounts_database.py`(격리 DB) |
| write-request | 응답 admin API→브라우저 | `X-Map-Environment`, `Cache-Control: no-store` | `map_project_admin/main.py:103-104` | 코드 읽기 |

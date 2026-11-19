# 트러블슈팅

운영 콘솔을 만들고 고치면서 실제로 겪은 문제와 해결을 모았다. 항목마다 증상 / 원인(근거) / 해결 / 검증 / 교훈 / 관련 커밋 순서로 적는다. 다른 저장소에서 고친 문제는 설명만 남기고 커밋 링크는 달지 않는다.

| ID | 한 줄 요약 |
|---|---|
| [T-CFG-01](#t-cfg-01) | 목록·사전형 환경변수를 빈 값으로 두면 기동 즉시 실패 |
| [T-DB-01](#t-db-01) | 대상 환경 장애가 로그인·준비 상태까지 막음 |
| [T-DB-02](#t-db-02) | DB·Redis 자격이 없는 API 전용 대상이 거부됨 |
| [T-DB-03](#t-db-03) | 기존 PostgreSQL 볼륨에서 띄우면 마이그레이션 단계에서 종료 |
| [T-SEC-01](#t-sec-01) | 진단 응답에 예외 원문이 실림 |
| [T-SEC-02](#t-sec-02) | 업스트림 오류 본문이 브라우저까지 전달됨 |
| [T-SEC-03](#t-sec-03) | 일반 내부 토큰으로 관리 API 를 부를 수 있음 |
| [T-SEC-04](#t-sec-04) | 회원 조회·로그인이 감사에 남지 않고 읽기 전용 운영자가 원문 이메일을 봄 |
| [T-SEC-05](#t-sec-05) | 외부 API 점검 실패 응답에 예외 문장이 실림 |
| [T-AUTH-01](#t-auth-01) | 로그인 응답에 역할이 없어 화면 권한이 어긋남 |
| [T-OPS-01](#t-ops-01) | 개요의 "비정상" 수에 미구성 항목이 섞임 |
| [T-CI-01](#t-ci-01) | CI 가 설치 단계에서 실패 |
| [T-IMG-01](#t-img-01) | 이미지 스캔이 perl·setuid 바이너리를 지적 |
| [T-IMG-02](#t-img-02) | 이미지 취약점 스캔 HIGH/CRITICAL |

---

### T-CFG-01
**목록·사전형 환경변수를 빈 값으로 두면 기동 즉시 실패**
- 증상: `.env` 에 `ADMIN_MONITORING_PANELS=`, `ADMIN_CORS_ORIGINS=`, `ADMIN_TARGETS=` 처럼 값 없이 키만 두면 프로세스가 `pydantic_settings.exceptions.SettingsError: error parsing value for field "…"` 로 바로 끝난다. `ADMIN_CORS_ORIGINS=http://a,http://b` 같은 콤마 구분도 같은 오류가 난다.
- 원인: pydantic-settings 는 `list[...]`·`dict[...]` 타입 환경변수를 JSON 으로만 읽는다. 빈 문자열과 콤마 구분 문자열은 JSON 이 아니다(`map_project_admin/config.py` 의 `Settings`).
- 해결: 쓰지 않는 키는 줄을 지우거나 주석으로 둔다. 값을 줄 때는 JSON 으로 쓴다 — `ADMIN_CORS_ORIGINS=["http://localhost:5173"]`, `ADMIN_TARGETS={}`, `ADMIN_MONITORING_PANELS=[]`.
- 검증: 위 세 키에 빈 값·콤마 구분·JSON 을 각각 넣고 `Settings()` 를 만들어 보면 JSON 만 통과한다.
- 교훈: 여러 서비스가 `.env` 하나를 나눠 쓰면 다른 서비스용으로 비워 둔 키가 이 서비스를 멈출 수 있다. 예시 파일에는 복합 타입 키를 주석으로만 둔다.
- 관련 커밋: 없음(동작은 그대로 두고 설명을 바로잡았다).

### T-DB-01
**대상 환경 장애가 로그인·준비 상태까지 막음**
- 증상: 관리 대상 환경의 DB 가 내려가거나 설정이 틀리면 운영자가 로그인조차 못 하고, 준비 상태 점검도 실제와 다른 값을 보고했다.
- 원인: 운영자 계정·세션·감사 저장소와 관리 대상의 데이터 연결이 같은 연결 설정을 썼다.
- 해결: 계정·세션·감사는 독립 control DB(`ADMIN_CONTROL_DATABASE_URL`)에만 두고, 대상 DB 는 환경별 읽기 전용 풀로 분리했다. 인증·운영자 관리·`/health/ready` 요청은 대상을 고르지 않고 control 설정만 쓴다(`map_project_admin/main.py` 의 `target_environment` 미들웨어). 대상 연결은 control DSN 으로 되돌아가지 않는다.
- 검증: `tests/test_control_target_isolation.py`(`test_control_lifespan_and_login_survive_missing_or_invalid_default_target` 등), 격리 통합 점검 `scripts/verify-control-isolation.py`(대상 장애 중에도 `/health/ready`·`/auth/me`·로그아웃이 정상).
- 교훈: 관리 도구는 관리 대상이 망가졌을 때 가장 필요하다. 관리 도구 자신의 상태 저장소는 대상과 다른 장애 영역에 둔다.
- 관련 커밋: {{commit:350593d}}, {{commit:7e30690}}

### T-DB-02
**DB·Redis 자격이 없는 API 전용 대상이 거부됨**
- 증상: 위임 API 만 쓰고 DB·Redis 진단은 두지 않으려는 대상 환경이 "설정 불완전" 으로 거부됐다.
- 원인: 대상 필수 키에 `ADMIN_REDIS_URL` 이 들어 있었고, 진단 코드가 "미설정" 과 "장애" 를 구분하지 않았다.
- 해결: 필수 키를 서비스 주소와 내부 토큰으로 줄였다. Redis 가 없으면 진단은 `{"error": "not_configured", "configured": false}` 를, SQL 화면은 503 을 돌려준다(`map_project_admin/redis_probe.py`, `map_project_admin/health_client.py`).
- 검증: `tests/test_control_target_isolation.py::test_api_only_target_has_no_database_or_redis_fallback`
- 교훈: "설정하지 않음" 은 오류가 아니라 하나의 정상 상태다. 상태 값을 참·거짓 둘로만 두면 이 상태를 표현할 수 없다.
- 관련 커밋: {{commit:2eb14ff}}

### T-DB-03
**기존 PostgreSQL 볼륨에서 띄우면 마이그레이션 단계에서 종료**
- 증상: 인프라 스택을 예전 볼륨 그대로 다시 띄우면 admin 컨테이너가 `alembic upgrade head` 에서 연결 오류(역할 없음)나 권한 오류(스키마 소유자 아님)로 곧바로 끝난다.
- 원인: PostgreSQL 공식 이미지의 초기화 스크립트(`docker-entrypoint-initdb.d`)는 빈 볼륨의 첫 부팅에만 돈다. 그래서 `map_admin` 역할 생성과 `admin_data` 소유권 이전이 빠진다.
- 해결: 인프라 저장소 안내대로 초기화 스크립트를 순서대로(스키마 생성 → admin 역할) 직접 한 번 실행하거나, 버려도 되는 개발 볼륨이면 지우고 다시 띄운다.
- 검증: `alembic upgrade head` 가 통과하고 로그인 화면이 열린다.
- 교훈: admin 은 이 상황에서 일부러 바로 멈춘다(`entrypoint.sh`). 권한 문제를 기동 뒤 런타임 오류로 미루지 않기 위해서다.
- 관련 커밋: 인프라 저장소의 문제라 링크 없음.

### T-SEC-01
**진단 응답에 예외 원문이 실림**
- 증상: Redis·DB 진단이 실패하면 응답과 로그에 예외 메시지 원문이 그대로 실렸다. 연결 문자열이나 쿼리 인자가 섞일 수 있었다.
- 원인: 진단 함수가 `str(exc)` 를 응답 본문에 넣었다.
- 해결: 예외 클래스 이름만 남긴다. `SQLAlchemyError` 는 전역 처리기가 고정 문구 `database unavailable`(503)로 바꾼다(`map_project_admin/main.py`).
- 검증: `tests/test_security_boundaries.py::test_redis_error_is_unavailable_not_empty_queue`
- 교훈: 예외 메시지는 사람이 읽으라고 만든 것이지만 그 안에 무엇이 들어갈지는 라이브러리가 정한다. 경계 밖으로는 내가 만든 문구만 보낸다.
- 관련 커밋: {{commit:2eb14ff}}, {{commit:350593d}}

### T-SEC-02
**업스트림 오류 본문이 브라우저까지 전달됨**
- 증상: 회원·추천 작업·실패 큐 위임 호출이 실패하면 user·hub 서비스의 오류 본문이 그대로 관리 화면까지 왔다. 그 본문에는 사용자 자료나 내부 오류 문자열이 들어 있을 수 있었다.
- 원인: 공통 위임 모듈의 오류 객체가 업스트림 payload 를 보존해 그대로 돌려줬다.
- 해결: 상태코드만 전파하고 본문은 상태코드별 고정 코드·안내 문구로 바꾼다(`map_project_admin/upstream.py` 의 `UpstreamError`). 성공 응답이라도 형식이 깨졌으면 본문을 내보내지 않는다.
- 검증: `tests/test_upstream_privacy.py`(`test_failure_body_is_never_forwarded`, `test_malformed_success_does_not_expose_body`, `test_exception_directly_created_by_caller_is_also_sanitized`), `tests/test_moderation.py::test_error_body_and_private_upstream_address_are_never_reflected`
- 교훈: 프록시는 상대 서비스의 개인정보 정책까지 물려받는다. 그대로 전달하면 상대의 실수가 내 화면에서 새어 나간다.
- 관련 커밋: {{commit:f2a2e64}}

### T-SEC-03
**일반 내부 토큰으로 관리 API 를 부를 수 있음**
- 증상: 서비스 사이의 일반 내부 토큰 하나로 user 의 회원 관리 API 와 hub 의 격자·금지구역 변경 API 를 모두 부를 수 있었다. 그 토큰을 가진 다른 서비스가 관리자 행위자(`X-Admin-Actor`)를 꾸밀 수 있는 구조였다.
- 원인: 관리 위임이 `MAP_PROJECT_INTERNAL_SERVICE_TOKEN` 을 같이 썼다.
- 해결: 관리 호출에는 전용 자격(`MAP_PROJECT_USER_ADMIN_INTERNAL_TOKEN`, `MAP_PROJECT_HUB_ADMIN_INTERNAL_TOKEN`)만 쓴다. 전용 자격이 비었거나 일반 토큰·다른 관리 토큰과 같으면 네트워크 요청 전에 막는다. 관리 자격은 선택한 대상 주소와 정해진 경로에만 붙고, 리다이렉트를 따라가지 않으며, 대상 환경끼리 상속되지 않는다(`map_project_admin/upstream.py` 의 `_headers`).
- 검증: `tests/test_admin_credential_isolation.py` 13개 시험(`test_missing_or_reused_admin_secret_never_opens_network`, `test_redirect_does_not_forward_management_credential`, `test_concurrent_environments_never_exchange_management_secrets` 등)
- 교훈: 같은 비밀을 여러 용도로 쓰면 가장 약한 용도의 노출 범위가 전체 권한이 된다. user·hub 쪽도 같은 전용 자격을 요구하도록 함께 바꿨다.
- 관련 커밋: {{commit:0b8df10}}, {{commit:f2a2e64}}

### T-SEC-04
**회원 조회·로그인이 감사에 남지 않고 읽기 전용 운영자가 원문 이메일을 봄**
- 증상: 회원 원문 상세 열람만 감사에 남았다. 회원 목록·검색 조회, 로그인 성공·실패·차단, 로그아웃은 기록되지 않았고, 읽기 전용(viewer) 운영자도 원문 이메일 상세를 볼 수 있었다.
- 원인: 감사 대상을 "쓰기 액션 + 원문 열람" 으로만 잡았다.
- 해결: 목록 조회를 기록하되 검색어 원문은 빼고 검색 여부와 페이지 크기만 남긴다. 로그인 결과 세 가지와 로그아웃을 기록하고 비밀번호는 남기지 않는다. viewer 는 원문 상세를 받지 못한다. 감사 저장에 실패하면 요청도 실패한다(fail-closed).
- 검증: `tests/test_security_boundaries.py`(`test_member_list_lookup_is_audited_without_the_search_text`, `test_viewer_cannot_read_the_raw_email_detail`, `test_operator_still_reads_the_raw_email_detail`, `test_login_records_success_failure_and_throttling`, `test_logout_records_only_a_real_session`)
- 교훈: 감사를 fail-closed 로 바꾸면 감사 저장을 대역하지 않은 기존 시험이 503 으로 깨진다. 시험이 깨진 이유가 "새 잠금" 인지 "대역 누락" 인지 먼저 가른다. 과잉 차단을 막는 시험(운영자는 계속 열람 가능)을 같이 둔다.
- 관련 커밋: {{commit:f200150}}

### T-SEC-05
**외부 API 점검 실패 응답에 예외 문장이 실림**
- 증상: 외부 API 수동 점검이 연결 오류·타임아웃으로 실패하면 결과의 `detail` 에 예외 문장 원문(`msg`)이 들어갔고, 그 결과가 응답과 감사 기록(`after_json`) 양쪽에 남았다.
- 원인: 점검 함수가 `str(exc)` 를 결과에 담았다. 기상청·두루누비 점검은 키를 쿼리 파라미터로 보내므로, 예외 문장에 요청 주소가 섞이면 키가 남을 수 있다.
- 해결: 예외 이름만 남긴다(`map_project_admin/external_status.py` 의 `probe`). Gemini 점검과 Redis·DB 진단은 이미 같은 방식이었다.
- 검증: `tests/test_security_boundaries.py::test_external_probe_failure_keeps_only_the_error_type` — 고치기 전 코드에서는 실패하고 고친 뒤 통과한다.
- 교훈: 한 경로에서 고친 원문 노출은 같은 모양의 다른 경로에도 있는지 찾아본다([T-SEC-01](#t-sec-01)).
- 관련 커밋: {{commit:ec47d88}}

### T-AUTH-01
**로그인 응답에 역할이 없어 화면 권한이 어긋남**
- 증상: 실제 브라우저로 로그인·계정 추가·viewer 차단을 점검하다가, 로그인 직후 화면이 역할별 메뉴·버튼을 잘못 보여 주는 것을 발견했다.
- 원인: 로그인 응답에 `role` 이 없어 SPA 가 다음 `/auth/me` 호출 전까지 역할을 몰랐다.
- 해결: 로그인 응답에 `role` 을 넣었다(`map_project_admin/routers/auth_router.py`).
- 검증: `tests/test_smoke.py::test_login_success`, 브라우저에서 viewer 계정의 쓰기 버튼 비노출.
- 교훈: 권한 판단은 서버가 하지만, 화면이 첫 응답만으로 그릴 수 있게 응답 계약을 맞춰야 사용자가 헷갈리지 않는다.
- 관련 커밋: {{commit:7e30690}}

### T-OPS-01
**개요의 "비정상" 수에 미구성 항목이 섞임**
- 증상: 라우팅(OSRM) 없이 스택을 띄우면 외부 점검 스크립트가 개요 헬스에서 "비정상 2건" 을 보고했다. 실제 장애는 없었다.
- 원인: OSRM 주소가 비면 헬스 항목은 `ok: null, configured: false`(미구성)다. 화면은 이를 "알 수 없음(미구성)" 으로 그리지만, 바깥 스크립트가 `!item.ok` 로 세어 null 을 장애로 셌다.
- 해결: 헬스 항목의 `ok` 는 `true`(정상)·`false`(장애)·`null`(미구성 또는 판단 불가) 세 값이다. 바깥에서 셀 때도 `ok === false` 만 장애로 센다(`map_project_admin/health_client.py`, `web/src/lib/status.ts`).
- 검증: `MAP_PROJECT_OSRM_FOOT_BASE_URL`·`MAP_PROJECT_OSRM_BICYCLE_BASE_URL` 을 비우고 `GET /api/v1/ops/health` 를 부르면 두 라우팅 항목이 `"ok": null, "configured": false` 로 온다(`_check_osrm`). 반대로 알 수 없는 본문을 정상으로 세지 않는지는 `tests/test_security_boundaries.py::test_unknown_health_body_is_not_healthy` 가 본다.
- 교훈: 세 값 상태를 둘로 접는 순간 거짓 경보나 거짓 정상이 생긴다.
- 관련 커밋: 콘솔 자체는 바뀌지 않았다(점검 스크립트 쪽 문제).

### T-CI-01
**CI 가 설치 단계에서 실패**
- 증상: 테스트를 자동으로 돌리려고 CI 를 붙이자 `pip install -r requirements-dev.txt` 단계에서 바로 실패했다.
- 원인: `tests/` 는 있었지만 테스트 실행기(pytest)를 선언한 파일이 없었다.
- 해결: `requirements-dev.txt` 에 pytest·httpx 를 선언했다. 런타임 이미지에는 넣지 않는다.
- 검증: CI 의 `pytest -q` 통과.
- 교훈: 로컬 환경에 우연히 깔린 도구는 선언되지 않은 의존성이다. 깨끗한 환경에서 한 번 돌려 봐야 드러난다.
- 관련 커밋: {{commit:ec8e587}}, {{commit:229e60b}}

### T-IMG-01
**이미지 스캔이 perl·setuid 바이너리를 지적**
- 증상: 런타임 이미지 취약점 스캔에서 앱이 쓰지 않는 perl 과 setuid 바이너리가 지적됐다.
- 원인: slim 베이스 이미지에 남아 있는 기본 패키지.
- 해결: 스캐너에서 제외하지 않고 패키지 자체를 지운다. 모든 apt 단계가 끝난 뒤 `perl-base` 를 purge 하고 setuid·setgid 비트를 지운 다음, 같은 단계에서 결과를 확인한다(`Dockerfile`). 앱은 비루트 사용자(10001)로 돈다.
- 검증: 빌드 중 `test ! -e /usr/bin/perl`, setuid 파일 0개 확인.
- 교훈: 스캐너 예외 목록은 위험을 숨길 뿐이다. 쓰지 않는 것은 지운다.
- 관련 커밋: {{commit:3ec7419}}

### T-IMG-02
**이미지 취약점 스캔 HIGH/CRITICAL**
- 증상: 런타임 이미지 스캔에 웹 프레임워크·암호 라이브러리와 nginx 베이스 패키지의 HIGH/CRITICAL 항목이 나왔다.
- 원인: 고정 판(fastapi)과 범위 상한(prometheus-fastapi-instrumentator `<8.0`)이 낡은 판에 묶여 있었고, starlette 는 fastapi 를 따라 간접으로만 들어와 판을 통제하지 못했다. nginx 베이스 이미지는 배포판 보안 수정보다 늦었다.
- 해결: fastapi·starlette·prometheus-fastapi-instrumentator 를 고정 판으로 올리고(`requirements.txt`), nginx 단계에서 `apk upgrade --no-cache` 를 실행한다(`web/Dockerfile`).
- 검증: 재빌드 후 스캔, `pip check`.
- 교훈: 잠금 파일 없이 범위만 두면 "어떤 판이 들어갔는지" 를 이미지마다 따로 확인해야 한다. 보안 관련 의존성은 고정한다.
- 관련 커밋: {{commit:f939ce9}}

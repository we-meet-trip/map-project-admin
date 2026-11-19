# 데이터 카드

## 요약
- 이 저장소는 **데이터셋을 담지 않는다.** 내려받을 자료, 빌드 스크립트, 재배포 제한이 있는 파일이 없다.
- 운영 콘솔이 화면에 보여 주는 자료는 모두 실행 중인 다른 서비스가 소유한 것이다: 허브의 `hub_data`(읽기 전용 조회), user 의 회원·추천 작업·신고(내부 API 위임), agent·hub·user 가 쓰는 Redis 키(개수·길이만 진단).
- 시험 자료는 모두 합성 값이다(`tests/` 의 가짜 계정·UUID·날짜, 브라우저 점검의 합성 HTTP 응답).
- 비공개 운영 환경의 DB 스냅숏·설정·이미지는 제공하지 않으며 공개본과 호환되지 않는다(이름 체계와 환경변수가 다르다).

## admin 이 소유하는 저장소: `admin_data` 스키마
Alembic 마이그레이션(`migrations/revisions/`)이 만든다. 스키마 자체는 미리 있어야 한다.

| 테이블 | 열 | 담는 것 |
|---|---|---|
| `admin_accounts` | `id`, `username`(고유), `password_hash`(bcrypt), `is_active`, `role`(`owner`·`operator`·`viewer`), `allowed_environments`(JSON 배열), `created_at` | 운영자 계정. 비밀번호 원문은 저장하지 않는다. |
| `admin_sessions` | `session_id`(UUID), `account_id`, `expires_at`, `created_at` | 서버측 세션. 브라우저에는 `session_id` 만 HttpOnly 쿠키로 간다. 계정 권한이 바뀌면 그 계정의 세션을 모두 지운다. |
| `login_attempts` | `bucket`, `attempts`, `expires_at` | 로그인 시도 제한. `bucket` 은 사용자명·접속 주소의 SHA-256 이라 원문을 남기지 않는다. 기간이 지난 행은 다음 시도 때 지운다. |
| `audit_logs` | `id`, `actor`, `action`, `target_service`·`target_schema`·`target_table`·`target_id`, `params_json`, `before_json`, `after_json`, `status`, `request_ip`, `created_at` | 운영 감사 기록(아래). |

### 감사 기록에 남기는 것과 남기지 않는 것
| 남긴다 | 남기지 않는다 |
|---|---|
| 모든 쓰기 요청의 시작(`request.started`)과 결과 상태코드 | 요청·응답 본문 원문 |
| 로그인 결과(`ok`·`failed`·`throttled`)와 시도한 사용자명, 로그아웃 | 비밀번호 |
| 회원 목록 조회(검색했는지 여부, 페이지 크기), 회원 원문 상세 열람 | 검색어 원문, 회원 정보 원문 |
| 신고 상세 열람, 신고 조치 요청·완료(조치 코드, 조치 UUID, 제한 시간) | 신고 설명·메시지 원문, user 서비스의 응답 본문 |
| 격자 토글 전후 값, 외부 API 수동 점검 결과 요약 | 외부 API 키 원문(키는 마스킹한 앞뒤 몇 글자만 화면에 보인다) |

- `actor` 는 운영자 이름이다. 신고 관리에서는 운영자 이름 대신 불투명한 `admin_<계정 id>` 를 쓰고, 같은 값을 user 서비스에 `X-Admin-Actor` 로 보낸다.
- `request_ip` 는 admin API 가 받은 연결의 주소다. 프록시(nginx)를 거치면 프록시 주소이며 운영자 주소가 아니다.
- 여러 환경을 한 control DB 로 관리해도, 감사 조회는 선택한 환경의 기록만 보여 준다.
- 런타임 역할은 감사 행을 지울 수 없다(`scripts/grant-control-runtime.sql`). 이 저장소에는 감사 기록 보존 기간·자동 삭제가 없다 — 보존 정책은 운영하는 사람이 정한다.

## 읽기만 하는 외부 자료
| 출처 | 접근 | 저장 |
|---|---|---|
| `hub_data`(허브 소유) | 읽기 전용 트랜잭션, 실제 테이블 목록만 허용 | admin 은 복사해 두지 않는다. CSV 내보내기는 요청한 사람의 브라우저로만 간다 |
| user 내부 API | 관리 전용 자격으로 위임 | 저장하지 않는다(신고 원문은 화면을 닫으면 캐시에서 지운다) |
| Redis | 키 개수·스트림 길이·쿼터 카운터 | 저장하지 않는다 |
| 외부 API(기상청·카카오·네이버·두루누비·OSRM·Gemini) | 수동 점검 1회, 사용하는 사람의 키 | 응답 본문을 저장하지 않는다. 상태코드·결과 코드·지연만 화면과 감사에 남긴다 |

외부 API 의 이용 조건은 각 제공자의 약관을 따른다. 이 저장소는 그 서비스들과 제휴하지 않는다.

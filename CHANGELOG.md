# 변경 기록

이 문서는 [Keep a Changelog](https://keepachangelog.com/ko/1.1.0/) 형식을 따르고, 버전은 [유의적 버전](https://semver.org/lang/ko/)을 따른다. 공개본에는 날짜를 기록하지 않는다.

## [1.0.0]

첫 공개본이다.

### 추가
- 공개 표준 파일: `LICENSE`(MIT), `AUTHORS.md`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`, 이슈·PR 템플릿.
- `pyproject.toml`(PEP 639 라이선스 표기, Python 3.10 이상).
- 문서: `docs/architecture.md`, `docs/data.md`, `docs/contracts.md`, `docs/troubleshooting.md`, `docs/decisions/`(설계 결정 9건), 구성도·쓰기 요청 순서도와 근거표(`docs/diagrams/`), 그림 렌더 스크립트.
- CI: 단위 시험을 Python 3.10~3.14 매트릭스로, Docker 를 쓰는 control DB 격리 점검을 별도 `integration.yml` 로.
- 시험: 세션 쿠키 기본값(HTTPS 전용), 외부 API 점검 실패 응답의 예외 문장 비노출.
- `.env.example` 에 설정 46개 전부와 중앙 모드 준비 순서.

### 변경
- 파이썬 패키지 이름 `app` → `map_project_admin`(엔트리포인트 `map_project_admin.main:app`), 웹 패키지 이름 → `map-project-admin-web`.
- 환경변수 이름: admin 만 읽는 값은 `ADMIN_`, 다른 서비스와 함께 읽는 값은 `MAP_PROJECT_` 접두. 옛 이름은 더 읽지 않는다(목록은 `.env.example`). `ADMIN_TARGETS` 안쪽 키도 새 이름을 쓴다.
- 세션 쿠키는 기본으로 HTTPS 전용(`ADMIN_SESSION_COOKIE_SECURE=true`). http 로컬 실행만 예시 파일에서 끈다.
- 이미지 점검 워크플로는 PR·수동 실행 때만 돈다.
- API 서버 판 표기를 1.0.0 으로, 두루누비 요청의 앱 이름 파라미터를 새 이름으로.

### 삭제
- 출시 준비 메모(작업 날짜·다른 저장소 커밋 식별자가 든 문서). 현재 동작 설명은 docs 로 옮겼다.
- 화면에서 쓰지 않는 API 래퍼 4개와 타입 3개.
- 코드·예시 파일의 개인 경로, 날짜가 든 기본값, 문장형 비밀 자리 값, 코드 주석의 내부 작업 표기.

### 수정
- 외부 API 수동 점검이 실패하면 예외 문장 원문이 응답과 감사 기록에 남던 문제.
- 격리 점검이 HTTPS 전용 세션 쿠키에서 실패하던 문제, 시험 컨테이너가 남던 문제.
- 실제와 다른 설명: 목록형 환경변수의 콤마 구분, 마이그레이션의 스키마 생성, 개발 서버의 CORS 설정.

### 비공개 개발본과 달라진 점
- 운영 환경 전용 배포·백업·전환 도구와 운영 설정을 뺐다. 공개본은 로컬에서 직접 준비한 설정으로 실행한다.
- 공개본의 이름(저장소·패키지·이미지)은 비공개 개발본과 다르다. 비공개 운영 자료(스냅숏·설정·이미지)와 호환되지 않는다.

### 히스토리 정리 안내
- 공개 전에 커밋 히스토리를 정리했다. 실제 데이터·내부 문서·민감 정보를 히스토리에서 걷어냈고, 작성자 이메일을 GitHub noreply 주소로 통일했으며, 커밋 시각은 순서만 남긴 임의 값으로 바꿨다.
- 커밋 메시지 속 옛 이름은 현재 이름이나 중립 표현으로 바꿨다. 그래서 과거 커밋의 코드와 메시지 속 이름이 서로 다를 수 있다.

[1.0.0]: https://github.com/we-meet-trip/map-project-admin/releases/tag/v1.0.0

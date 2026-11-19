"""map-project-admin 환경설정 (운영 콘솔 JSON API).

다른 서비스(user/agent/hub)와 동일한 프로젝트 루트 `.env` 를 공유하므로
`extra="ignore"` 로 무관한 키를 무시한다(hub/config.py 와 동일 규약).

범위: hub_data 읽기전용 + admin_data 소유 RW(감사/계정/세션) + Redis 진단
RO(DB2 스트림·DB3 Gemini 쿼터·DB4 캐시) + hub/BFF `/internal` 위임 + 외부 API
상태/프로브. 인증은 admin_accounts(bcrypt) + 서버측 세션(HttpOnly 쿠키).
"""
from __future__ import annotations

from contextvars import ContextVar
from typing import Any

from pydantic import BaseModel, Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class MonitoringPanel(BaseModel):
    """외부 모니터링 연동 패널 1개(Grafana·Prometheus 등 범용).

    admin 은 대상 도구를 iframe/링크로 '연결'만 한다(직접 기동은 compose
    monitoring 프로파일이 담당). SPA 의 모니터링 화면이 본 슬롯을 렌더한다.
    """

    title: str
    url: str
    embed: bool = False
    height: int = 420
    description: str | None = None

    @field_validator("url")
    @classmethod
    def _http_only(cls, v: str) -> str:
        """http/https 스킴만 허용(javascript: 등 iframe src 주입 차단)."""
        if not v.lower().startswith(("http://", "https://")):
            raise ValueError("ADMIN_MONITORING_PANELS url must be http(s)")
        return v

    @field_validator("height")
    @classmethod
    def _sane_height(cls, v: int) -> int:
        """iframe 높이를 상식 범위(120–2000px)로 보정."""
        return max(120, min(v, 2000))


class Settings(BaseSettings):
    """환경변수/`.env` 기반 설정."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # 중앙 모드: 계정·세션·감사를 둘 control DB 의 런타임 DSN.
    # 비워 두면 단일 호스트 모드로, ADMIN_DATABASE_URL 하나를 control 과 기본 대상이 함께 쓴다.
    ADMIN_CONTROL_DATABASE_URL: str = ""
    ADMIN_DATABASE_URL: str = ""
    ADMIN_ENVIRONMENT: str = Field(default="test", pattern=r"^[a-z][a-z0-9_-]{0,31}$")
    # 다른 환경의 연결 값은 서버에만 둔다. API는 이름만 공개한다.
    ADMIN_TARGETS: dict[str, dict[str, Any]] = {}
    ADMIN_LOGIN_MAX_ATTEMPTS: int = Field(default=10, ge=1, le=1000)
    ADMIN_LOGIN_WINDOW_SECONDS: int = Field(default=300, ge=1, le=86400)
    # 쿼리 statement timeout(초). 엔진 connect_args 에 반영(느린 조회 상한).
    ADMIN_DB_TIMEOUT_SEC: float = 5.0

    # [인증 — 계정 세션] admin_accounts(bcrypt) + admin_sessions(HttpOnly 쿠키).
    # 최초 계정 시드: accounts 가 비었을 때만 아래 부트스트랩 자격으로 1회 생성.
    ADMIN_BOOTSTRAP_USER: str = ""
    ADMIN_BOOTSTRAP_PASSWORD: SecretStr = SecretStr("")
    ADMIN_SESSION_COOKIE_NAME: str = "admin_session"
    ADMIN_SESSION_TTL_MIN: int = 720  # 12h
    # 기본 True: 세션 쿠키를 HTTPS 로만 보낸다. http://127.0.0.1 로 띄우는 로컬 실행에서만
    # False 로 바꾼다(.env.example 참고).
    ADMIN_SESSION_COOKIE_SECURE: bool = True

    # [CORS] dev SPA origin 목록. JSON 배열만 받는다(콤마 구분·빈 값은 기동 오류). 프로덕션은 nginx
    # same-origin 프록시라 비워 둔다. 세션 쿠키를 위해 allow_credentials=True.
    ADMIN_CORS_ORIGINS: list[str] = []

    # [헬스 롤업 대상 — 컨테이너 내부 포트]
    ADMIN_USER_BASE_URL: str = "http://user:8080"
    MAP_PROJECT_AGENT_BASE_URL: str = "http://agent:8000"
    MAP_PROJECT_HUB_BASE_URL: str = "http://hub:8000"
    ADMIN_HEALTH_TIMEOUT_SEC: float = 3.0

    # [OSRM 프로브] hub 와 동일 키 재사용. 비면 프로브 skip.
    MAP_PROJECT_OSRM_FOOT_BASE_URL: str = ""
    MAP_PROJECT_OSRM_BICYCLE_BASE_URL: str = ""

    # [Redis 진단 RO] 스트림/쿼터/캐시 조회. hub/BFF 와 동일 인스턴스.
    ADMIN_REDIS_URL: str = "redis://redis:6379"
    MAP_PROJECT_REDIS_DB_STREAMS: int = 2
    MAP_PROJECT_REDIS_DB_RATELIMIT: int = 3
    MAP_PROJECT_REDIS_DB_HUB_CACHE: int = 4
    # 스트림/DLQ/컨슈머 이름(agent·BFF 규약과 일치).
    ADMIN_STREAM_DONE: str = "agent:jobs:done"
    ADMIN_STREAM_STATUS: str = "agent:jobs:status"
    MAP_PROJECT_STREAM_DLQ: str = "agent:jobs:done:dlq"
    MAP_PROJECT_STREAM_GROUP: str = "bff-result"
    ADMIN_REDIS_TIMEOUT_SEC: float = 2.0

    # [내부 위임] 일반 Hub와 User 관리자 권한은 별도 비밀이다.
    MAP_PROJECT_INTERNAL_SERVICE_TOKEN: SecretStr = SecretStr("")
    MAP_PROJECT_USER_ADMIN_INTERNAL_TOKEN: SecretStr = SecretStr("")
    MAP_PROJECT_HUB_ADMIN_INTERNAL_TOKEN: SecretStr = SecretStr("")
    ADMIN_INTERNAL_TIMEOUT_SEC: float = 5.0

    # [Gemini 연결 점검] 무료 메타 호출(models.list). 생성 미사용.
    MAP_PROJECT_GEMINI_API_KEY: SecretStr = SecretStr("")
    ADMIN_GEMINI_MODELS_URL: str = (
        "https://generativelanguage.googleapis.com/v1beta/models"
    )
    ADMIN_GEMINI_TIMEOUT_SEC: float = 5.0
    MAP_PROJECT_GEMINI_RPD_CAP: int = 200  # agent 의 일일 쿼터 상한(표시용)

    # [외부 API 키 존재 여부/프로브] hub 소유 키를 공유 .env 에서 읽어 상태
    # 표시·수동 프로브에 사용한다. 값은 마스킹해서만 노출한다.
    MAP_PROJECT_KAKAO_REST_API_KEY: SecretStr = SecretStr("")
    MAP_PROJECT_KMA_SERVICE_KEY: SecretStr = SecretStr("")
    MAP_PROJECT_TOUR_API_SERVICE_KEY: SecretStr = SecretStr("")
    MAP_PROJECT_NAVER_CLIENT_ID: SecretStr = SecretStr("")
    MAP_PROJECT_NAVER_CLIENT_SECRET: SecretStr = SecretStr("")
    ADMIN_EXTERNAL_PROBE_TIMEOUT_SEC: float = 6.0

    # [DB 뷰어(hub_data 한정)]
    ADMIN_DB_PAGE_SIZE_DEFAULT: int = 50
    ADMIN_DB_PAGE_SIZE_MAX: int = 500
    ADMIN_DB_EXPORT_MAX_ROWS: int = 50000

    # [외부 모니터링 연동 슬롯] Grafana 등 iframe/링크. JSON 배열.
    ADMIN_MONITORING_PANELS: list[MonitoringPanel] = []


# 프로세스 단위 싱글톤. 다른 모듈은 이 객체를 직접 임포트한다.
control_settings = Settings()
_target_settings: ContextVar[Settings | None] = ContextVar("admin_target", default=None)
_target_name: ContextVar[str | None] = ContextVar("admin_target_name", default=None)

_TARGET_FIELDS = {
    "ADMIN_DATABASE_URL", "ADMIN_REDIS_URL", "ADMIN_USER_BASE_URL", "MAP_PROJECT_AGENT_BASE_URL",
    "MAP_PROJECT_HUB_BASE_URL", "MAP_PROJECT_OSRM_FOOT_BASE_URL", "MAP_PROJECT_OSRM_BICYCLE_BASE_URL",
    "MAP_PROJECT_INTERNAL_SERVICE_TOKEN", "MAP_PROJECT_USER_ADMIN_INTERNAL_TOKEN", "MAP_PROJECT_HUB_ADMIN_INTERNAL_TOKEN", "MAP_PROJECT_GEMINI_API_KEY", "MAP_PROJECT_KAKAO_REST_API_KEY",
    "MAP_PROJECT_KMA_SERVICE_KEY", "MAP_PROJECT_TOUR_API_SERVICE_KEY", "MAP_PROJECT_NAVER_CLIENT_ID",
    "MAP_PROJECT_NAVER_CLIENT_SECRET", "ADMIN_MONITORING_PANELS", "MAP_PROJECT_GEMINI_RPD_CAP",
}
_TARGET_SECRETS = {
    "MAP_PROJECT_INTERNAL_SERVICE_TOKEN", "MAP_PROJECT_USER_ADMIN_INTERNAL_TOKEN", "MAP_PROJECT_HUB_ADMIN_INTERNAL_TOKEN", "MAP_PROJECT_GEMINI_API_KEY", "MAP_PROJECT_KAKAO_REST_API_KEY",
    "MAP_PROJECT_KMA_SERVICE_KEY", "MAP_PROJECT_TOUR_API_SERVICE_KEY", "MAP_PROJECT_NAVER_CLIENT_ID", "MAP_PROJECT_NAVER_CLIENT_SECRET",
}


class _RequestSettings:
    def __getattr__(self, name: str):
        return getattr(_target_settings.get() or control_settings, name)


settings = _RequestSettings()


def environment_name() -> str:
    return _target_name.get() or control_settings.ADMIN_ENVIRONMENT


def environment_names() -> list[str]:
    return sorted({control_settings.ADMIN_ENVIRONMENT, *control_settings.ADMIN_TARGETS})


def select_environment(name: str):
    overrides = control_settings.ADMIN_TARGETS.get(name)
    if overrides is None:
        if name != control_settings.ADMIN_ENVIRONMENT:
            raise ValueError("unknown or invalid environment")
        if control_settings.ADMIN_CONTROL_DATABASE_URL:
            raise ValueError("environment connection settings incomplete")
        # 단일 호스트 모드: control 설정을 기본 대상 설정으로 그대로 쓴다.
        # 중앙 모드(control DSN 설정)에서는 위에서 거부되므로 이 경로로 오지 않는다.
        selected = control_settings
    else:
        if set(overrides) - _TARGET_FIELDS:
            raise ValueError("unknown or invalid environment")
        required = {"ADMIN_USER_BASE_URL", "MAP_PROJECT_AGENT_BASE_URL",
                    "MAP_PROJECT_HUB_BASE_URL", "MAP_PROJECT_INTERNAL_SERVICE_TOKEN"}
        if any(not overrides.get(key) for key in required):
            raise ValueError("environment connection settings incomplete")
        values = control_settings.model_dump()
        values.update({key: "" for key in _TARGET_SECRETS})
        # DB is optional for API-only targets. Never inherit the control/co-host DSN.
        values.update({"ADMIN_DATABASE_URL": "", "ADMIN_REDIS_URL": "", "MAP_PROJECT_OSRM_FOOT_BASE_URL": "",
                       "MAP_PROJECT_OSRM_BICYCLE_BASE_URL": "", "ADMIN_MONITORING_PANELS": []})
        values.update(overrides)
        selected = Settings.model_validate(values)
    return _target_settings.set(selected), _target_name.set(name)


def select_control():
    """Authentication/readiness remain available even if no target is configured."""
    return _target_settings.set(control_settings), _target_name.set(control_settings.ADMIN_ENVIRONMENT)


def reset_environment(tokens) -> None:
    _target_settings.reset(tokens[0])
    _target_name.reset(tokens[1])

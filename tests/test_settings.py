"""설정 로더: 빈 환경변수는 설정하지 않은 값으로 본다."""
from map_project_admin.config import Settings


def test_empty_environment_values_fall_back_to_defaults(monkeypatch):
    """공유 .env·compose 가 넘긴 빈 값이 목록·사전·불리언·숫자 설정의 기동을 막지 않는다."""
    for name in ("ADMIN_CORS_ORIGINS", "ADMIN_TARGETS", "ADMIN_MONITORING_PANELS",
                 "ADMIN_SESSION_COOKIE_SECURE", "ADMIN_LOGIN_MAX_ATTEMPTS", "ADMIN_ENVIRONMENT"):
        monkeypatch.setenv(name, "")
    settings = Settings(_env_file=None)
    assert settings.ADMIN_CORS_ORIGINS == []
    assert settings.ADMIN_TARGETS == {}
    assert settings.ADMIN_MONITORING_PANELS == []
    assert settings.ADMIN_SESSION_COOKIE_SECURE is True
    assert settings.ADMIN_LOGIN_MAX_ATTEMPTS == 10
    assert settings.ADMIN_ENVIRONMENT == "test"

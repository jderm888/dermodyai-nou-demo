import pytest


@pytest.fixture(autouse=True)
def _isolate_env(monkeypatch):
    """Tests must not pick up a developer key or an archived client profile."""
    for name in (
        "BD_PROFILE_PATH",
        "BD_ALLOW_ARCHIVED_PROFILES",
        "SAM_GOV_API_KEY",
        "SAM_API_KEY",
        "ANTHROPIC_API_KEY",
    ):
        monkeypatch.delenv(name, raising=False)

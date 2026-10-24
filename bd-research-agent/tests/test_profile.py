from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import main
from profile import (
    ARCHIVED_DIR,
    ArchivedProfileError,
    ProfileError,
    load_default_profile,
    load_profile_by_id,
    resolve_profile,
)

ROOT = Path(__file__).resolve().parents[1]


def test_default_profile_is_the_fictional_example():
    profile = load_default_profile()
    assert profile.id == "example_contractor"
    assert profile.example_data is True
    assert "Northwind" in profile.name
    assert "FICTIONAL" in profile.disclaimer
    assert "NOU" not in profile.to_prompt()
    assert profile.codes_for(["range_software"]) == ["541511", "541512"]
    assert "541330" not in profile.all_naics()


def test_archived_client_profile_is_preserved_but_not_selectable():
    archived = ARCHIVED_DIR / "nou_systems.yaml"
    text = archived.read_text(encoding="utf-8")
    assert "NOU Systems" in text
    assert "Huntsville" in text
    with pytest.raises(ProfileError):
        load_profile_by_id("nou_systems")


def test_archived_file_requires_an_explicit_flag(monkeypatch):
    archived = ARCHIVED_DIR / "nou_systems.yaml"
    monkeypatch.setenv("BD_PROFILE_PATH", str(archived))
    try:
        load_default_profile()
    except ArchivedProfileError as exc:
        assert "BD_ALLOW_ARCHIVED_PROFILES" in str(exc)
    else:
        raise AssertionError("archived profile was loaded without the operator flag")
    monkeypatch.setenv("BD_ALLOW_ARCHIVED_PROFILES", "1")
    loaded = load_default_profile()
    assert loaded.id == "nou_systems"


def test_inline_profile_overrides_the_default():
    profile = resolve_profile(
        inline={
            "id": "inline_example",
            "name": "Inline Example Co",
            "example_data": True,
            "disclaimer": "Made-up inline profile.",
            "naics_codes": ["541512"],
            "keywords": ["telemetry"],
            "agencies": ["Department of the Air Force"],
        }
    )
    assert profile.name == "Inline Example Co"
    assert profile.all_naics() == ["541512"]


def test_demo_pages_do_not_name_the_archived_client():
    client = TestClient(main.app)
    home = client.get("/")
    assert home.status_code == 200
    assert "NOU" not in home.text
    assert "Northwind" in home.text
    assert "Strong fit" in home.text
    assert "1–5" in home.text or "1-5" in home.text

    current = client.get("/api/profile").json()
    assert current["example_data"] is True
    assert "NOU" not in current["name"]

    listed = client.get("/api/profiles").json()["profiles"]
    assert [item["id"] for item in listed] == ["example_contractor"]
    areas = client.get("/api/naics-profiles").json()
    assert "systems_engineering" not in areas
    assert "range_software" in areas


def test_archived_profile_id_is_rejected_by_the_api():
    client = TestClient(main.app)
    response = client.post("/api/research", json={"profile_id": "nou_systems"})
    assert response.status_code == 404
    assert "NOU" not in response.text
    assert "not available" in response.text


def test_demo_source_does_not_put_the_client_on_the_default_path():
    allowed = {
        ROOT / "DEMO.md",
        ROOT / "profiles" / "archived" / "nou_systems.yaml",
    }
    offenders = []
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix not in {".py", ".html", ".yaml", ".yml", ".md", ".js"}:
            continue
        if "archived" in path.parts or path in allowed or "tests" in path.parts:
            continue
        if "NOU" in path.read_text(encoding="utf-8"):
            offenders.append(str(path.relative_to(ROOT)))
    assert offenders == []

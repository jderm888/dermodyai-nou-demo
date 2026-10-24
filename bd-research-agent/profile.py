"""Contractor profiles. The demo default is fictional example data."""

from __future__ import annotations

import os
import re
from pathlib import Path

import yaml
from pydantic import BaseModel, Field, model_validator

PACKAGE_DIR = Path(__file__).resolve().parent
PROFILES_DIR = PACKAGE_DIR / "profiles"
ARCHIVED_DIR = PROFILES_DIR / "archived"
DEFAULT_PROFILE_PATH = PROFILES_DIR / "example_contractor.yaml"

_PROFILE_ID = re.compile(r"[a-z0-9_]+")


class ProfileError(Exception):
    """The requested profile could not be loaded."""


class ArchivedProfileError(ProfileError):
    """A client profile exists on disk but is not available to the demo."""


class PastPerformance(BaseModel):
    name: str
    customer: str = ""
    period: str = ""
    summary: str = ""


class FocusArea(BaseModel):
    label: str
    codes: list[str] = Field(default_factory=list)
    description: str = ""


class ContractorProfile(BaseModel):
    id: str = "inline"
    name: str
    example_data: bool = False
    disclaimer: str = ""
    headquarters: str = ""
    business_size: str = ""
    set_asides: list[str] = Field(default_factory=list)
    competencies: list[str] = Field(default_factory=list)
    contract_size: str = ""
    agencies: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    naics_codes: list[str] = Field(default_factory=list)
    focus_areas: dict[str, FocusArea] = Field(default_factory=dict)
    past_performance: list[PastPerformance] = Field(default_factory=list)

    @model_validator(mode="after")
    def require_naics(self):
        if not self.all_naics():
            raise ValueError("Profile needs naics_codes or focus-area NAICS codes")
        return self

    def all_naics(self) -> list[str]:
        codes = {str(code) for code in self.naics_codes if str(code).strip()}
        for area in self.focus_areas.values():
            codes.update(str(code) for code in area.codes if str(code).strip())
        return sorted(codes)

    def codes_for(self, focus_area_keys: list[str] | None) -> list[str]:
        if not focus_area_keys:
            return self.all_naics()
        codes: list[str] = []
        for key in focus_area_keys:
            area = self.focus_areas.get(key)
            if area:
                codes.extend(str(code) for code in area.codes)
        deduped = sorted(set(codes))
        return deduped or self.all_naics()

    def focus_area_map(self) -> dict[str, dict]:
        return {
            key: {"label": area.label, "codes": list(area.codes), "description": area.description}
            for key, area in self.focus_areas.items()
        }

    def to_prompt(self) -> str:
        lines: list[str] = []
        if self.example_data:
            lines.append("DEMO PROFILE — FICTIONAL EXAMPLE DATA. Not a real contractor.")
        if self.disclaimer.strip():
            lines.append(self.disclaimer.strip())
        lines.append(f"Name: {self.name}")
        if self.headquarters:
            lines.append(f"Headquarters: {self.headquarters}")
        if self.business_size:
            lines.append(f"Business size: {self.business_size}")
        if self.contract_size:
            lines.append(f"Typical contract size (profile claim, not an award): {self.contract_size}")
        if self.set_asides:
            lines.append("Set-asides the contractor can pursue: " + ", ".join(self.set_asides))
        if self.competencies:
            lines.append("Competencies:")
            lines.extend(f"- {item}" for item in self.competencies)
        if self.agencies:
            lines.append("Target agencies: " + ", ".join(self.agencies))
        if self.keywords:
            lines.append("Keywords: " + ", ".join(self.keywords))
        lines.append("NAICS codes: " + ", ".join(self.all_naics()))
        if self.past_performance:
            lines.append(
                "Past performance below was typed into the profile. "
                "It is not a SAM.gov or USASpending record and must not be cited as an award."
            )
            for item in self.past_performance:
                lines.append(
                    f"- {item.name} | {item.customer} | {item.period} | {item.summary}"
                )
        return "\n".join(lines)

    def public_dict(self) -> dict:
        payload = self.model_dump()
        payload["naics_codes"] = self.all_naics()
        return payload


def _is_archived(path: Path) -> bool:
    try:
        path.resolve().relative_to(ARCHIVED_DIR.resolve())
        return True
    except ValueError:
        return False


def load_profile_file(path: Path, *, allow_archived: bool = False) -> ContractorProfile:
    path = Path(path)
    if not path.is_file():
        raise ProfileError(f"Profile file not found: {path.name}")
    if _is_archived(path) and not allow_archived:
        raise ArchivedProfileError(
            f"{path.name} is an archived client profile and is not available to the demo. "
            "The default profile is profiles/example_contractor.yaml."
        )
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ProfileError(f"Profile file {path.name} must be a mapping")
    try:
        return ContractorProfile.model_validate(data)
    except Exception as exc:
        raise ProfileError(f"Profile file {path.name} is invalid: {exc}") from exc


def load_profile_by_id(profile_id: str) -> ContractorProfile:
    if not _PROFILE_ID.fullmatch(profile_id or ""):
        raise ProfileError("profile_id must be a lowercase name made of letters, numbers, and underscores")
    path = (PROFILES_DIR / f"{profile_id}.yaml").resolve()
    if path.parent != PROFILES_DIR.resolve() or not path.is_file() or _is_archived(path):
        raise ProfileError(
            "That profile is not available in the demo. "
            "Use example_contractor or pass an inline profile."
        )
    return load_profile_file(path, allow_archived=False)


def load_default_profile() -> ContractorProfile:
    override = os.getenv("BD_PROFILE_PATH", "").strip()
    if override:
        allow_archived = os.getenv("BD_ALLOW_ARCHIVED_PROFILES") == "1"
        try:
            return load_profile_file(Path(override), allow_archived=allow_archived)
        except ArchivedProfileError:
            raise ArchivedProfileError(
                "BD_PROFILE_PATH points at an archived client profile. "
                "The demo will not load it unless BD_ALLOW_ARCHIVED_PROFILES=1. "
                "Leave both unset to use the fictional example profile."
            ) from None
    return load_profile_file(DEFAULT_PROFILE_PATH, allow_archived=False)


def list_demo_profiles() -> list[dict]:
    """Profiles a demo may select. Archived client files are excluded."""
    found = []
    for path in sorted(PROFILES_DIR.glob("*.yaml")):
        if _is_archived(path):
            continue
        profile = load_profile_file(path, allow_archived=False)
        found.append(
            {
                "id": profile.id,
                "name": profile.name,
                "example_data": profile.example_data,
            }
        )
    return found


def resolve_profile(
    *,
    profile_id: str | None = None,
    inline: dict | None = None,
) -> ContractorProfile:
    """Resolve a request profile. Inline input wins, then a demo profile id, then the default.

    Filesystem paths are not accepted from a request. Operators set BD_PROFILE_PATH locally.
    """
    if inline:
        try:
            return ContractorProfile.model_validate(inline)
        except Exception as exc:
            raise ProfileError(f"Inline profile is invalid: {exc}") from exc
    if profile_id:
        return load_profile_by_id(profile_id)
    return load_default_profile()

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

# Optional import: allow running without python-dotenv installed
try:
    from dotenv import load_dotenv  # type: ignore
except Exception:  # pragma: no cover - fallback when library isn't installed yet
    def load_dotenv(*args, **kwargs):  # type: ignore
        return False

# Load environment variables from the project root .env, if present
# Determine repository root as two levels up from this file's parent (…/src/youtrack_api_services/)
_REPO_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(dotenv_path=_REPO_ROOT / ".env")


@dataclass(frozen=True)
class Settings:
    # Base configuration with sensible defaults; can be overridden by CLI
    base_url: str = field(default_factory=lambda: os.getenv("BASE_URL", "https://youtrack.jetbrains.com"))

    # Default tag and query parts per the issue description
    default_tag_label: str = "customer: Canva"
    default_projects: tuple[str, ...] = (
        "Toolbox App",
        "IntelliJ IDEA",
        "IntelliJ Platform",
        "Support",
        "Enterprise Support",
    )
    include_unresolved: bool = True

    # Fields to request from YouTrack
    # Note: YouTrack represents custom fields in the `customFields` array
    # We include common value subfields such as name, login, fullName to cover typical cases
    fields: str = (
        "idReadable,summary,description,created,updated,"
        "project(name,shortName),"
        "customFields(name,value(name,login,fullName,localizedName))"
    )

    # Path to the file containing the YouTrack permanent token
    token_file: Path = field(default_factory=lambda: _REPO_ROOT / "youtrack_api_token.txt")


def build_default_query(tag_label: str | None = None,
                        projects: tuple[str, ...] | None = None,
                        include_unresolved: bool | None = None) -> str:
    """Compose the default YouTrack query string.

    Example output:
    tag: {customer: Canva} #Unresolved project: {Toolbox App} project: {IntelliJ IDEA} ...
    """
    s = Settings()
    tag_label = tag_label or s.default_tag_label
    projects = projects or s.default_projects
    include_unresolved = s.include_unresolved if include_unresolved is None else include_unresolved

    parts: list[str] = []
    if tag_label:
        parts.append(f"tag: {{{tag_label}}}")
    if include_unresolved:
        parts.append("#Unresolved")
    for proj in projects:
        parts.append(f"project: {{{proj}}}")
    return " ".join(parts)

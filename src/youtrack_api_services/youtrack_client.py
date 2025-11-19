from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import requests

from .config import Settings


class YouTrackError(RuntimeError):
    pass


@dataclass
class YouTrackClient:
    base_url: str
    token: str
    fields: str

    @classmethod
    def from_settings(cls, settings: Optional[Settings] = None) -> "YouTrackClient":
        s = settings or Settings()
        token = load_token(s.token_file)
        return cls(base_url=s.base_url, token=token, fields=s.fields)

    @property
    def headers(self) -> Dict[str, str]:
        return {"Authorization": f"Bearer {self.token}", "Accept": "application/json"}

    def fetch_issues(self, query: str, batch_size: int = 200) -> List[Dict[str, Any]]:
        """Fetch all issues for a query, handling pagination.

        Args:
            query: YouTrack search query string.
            batch_size: Number of issues per request (max usually 100/200 depending on server config).
        """
        issues: List[Dict[str, Any]] = []
        skip = 0
        while True:
            params = {
                "fields": self.fields,
                "query": query,
                "$skip": skip,
                "$top": batch_size,
            }
            url = f"{self.base_url}/api/issues"
            resp = requests.get(url, headers=self.headers, params=params, timeout=60)
            if resp.status_code != 200:
                # Provide a helpful error with details
                raise YouTrackError(
                    f"Failed to fetch issues: {resp.status_code} {resp.text[:500]}"
                )
            batch = resp.json()
            if not isinstance(batch, list):
                raise YouTrackError(
                    f"Unexpected response format: {json.dumps(batch)[:500]}"
                )
            if not batch:
                break
            issues.extend(batch)
            if len(batch) < batch_size:
                break
            skip += batch_size
        return issues


def load_token(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(
            f"Token file not found at {path.resolve()}. Create it with your permanent token on the first line."
        )
    token = path.read_text(encoding="utf-8").strip().splitlines()[0].strip()
    if not token:
        raise YouTrackError("Token file is empty. Put your permanent token on the first line.")
    return token


def flatten_issues(raw_issues: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Flatten YouTrack issues into simple dicts suitable for DataFrame/CSV.

    - Pulls idReadable, summary, description, created, updated
    - Extracts common custom fields (Assignee, State, Priority) when present
    """
    rows: List[Dict[str, Any]] = []
    for it in raw_issues:
        row: Dict[str, Any] = {
            "idReadable": it.get("idReadable"),
            "summary": it.get("summary"),
            "description": it.get("description"),
            "created": it.get("created"),
            "updated": it.get("updated"),
        }

        # Extract project name (fallback to shortName)
        proj = it.get("project") or {}
        if isinstance(proj, dict):
            row["project"] = proj.get("name") or proj.get("shortName")
        else:
            row["project"] = None

        # Map common custom fields from customFields array
        for cf in it.get("customFields", []) or []:
            name = cf.get("name")
            val = cf.get("value")
            if not name:
                continue
            # Value can be primitive or object; we try common shapes
            v = None
            if isinstance(val, dict):
                v = val.get("name") or val.get("fullName") or val.get("login") or val.get("localizedName")
            else:
                v = val
            # Write into well-known columns for common fields, else keep original name
            key = name
            if name.lower() in {"assignee", "assigned to"}:
                key = "Assignee"
            elif name.lower() == "state":
                key = "State"
            elif name.lower() == "priority":
                key = "Priority"
            row[key] = v

        rows.append(row)
    return rows

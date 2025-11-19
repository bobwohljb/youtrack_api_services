from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd

from .config import Settings, build_default_query
from .youtrack_client import YouTrackClient, flatten_issues


def sanitize_filename_component(s: str) -> str:
    # Keep alnum and replace others with underscores; collapse repeats
    import re

    s = re.sub(r"[^A-Za-z0-9]+", "_", s).strip("_")
    return s or "issues"


def parse_args() -> argparse.Namespace:
    s = Settings()
    p = argparse.ArgumentParser(description="Export YouTrack issues to CSV for Google Sheets")
    p.add_argument("--base-url", default=s.base_url, help="YouTrack base URL")
    p.add_argument("--tag", default=s.default_tag_label, help="Tag label used in query and filename base")
    p.add_argument("--query", default=None, help="Override full YouTrack query (when set, --tag only affects filename)")
    p.add_argument("--output-dir", default="outputs", help="Directory to write CSV files")
    return p.parse_args()


def build_query(args: argparse.Namespace) -> str:
    if args.query:
        return args.query
    # Build the default query using the tag and preset projects
    return build_default_query(tag_label=args.tag)


def main(argv: Optional[list[str]] = None) -> int:
    args = parse_args()
    settings = Settings()
    # Allow overriding base url via CLI
    settings = Settings(base_url=args.base_url)

    client = YouTrackClient.from_settings(settings)
    query = build_query(args)

    issues = client.fetch_issues(query)
    rows = flatten_issues(issues)

    df = pd.DataFrame(rows)

    # Sort by created date (newest to oldest) before any formatting
    # We expect `created` to be epoch milliseconds from YouTrack. If missing, skip sorting.
    if not df.empty and "created" in df.columns:
        # Convert to datetime for robust sorting; NaT values will be placed last
        created_dt = pd.to_datetime(df["created"], unit="ms", errors="coerce")
        df = df.assign(_created_dt=created_dt).sort_values(
            by="_created_dt", ascending=False, na_position="last"
        ).drop(columns=["_created_dt"])  # drop helper column

    # Keep only the required columns in the specified order, with formatting
    # 1) Build ticket hyperlink using the base URL and idReadable
    if not df.empty:
        base_issue_url = settings.base_url.rstrip("/") + "/issue/"
        # Ensure idReadable exists even if missing in some rows
        if "idReadable" not in df.columns:
            df["idReadable"] = ""
        df["ticket ID"] = df["idReadable"].apply(
            lambda x: f'=HYPERLINK("{base_issue_url}{x}","{x}")' if isinstance(x, str) and x else ""
        )

        # 2) Human-friendly dates DD/MM/YYYY
        for col in ("created", "updated"):
            if col in df.columns:
                # YouTrack timestamps are epoch millis
                df[col] = pd.to_datetime(df[col], unit="ms", errors="coerce").dt.strftime("%d/%m/%Y")
            else:
                df[col] = ""

        # 3) Normalize field names/casing
        # Summary -> capitalized column name
        if "summary" in df.columns:
            df["Summary"] = df["summary"]
        elif "Summary" not in df.columns:
            df["Summary"] = ""

        # Type custom field may arrive as "Type" (from customFields). Create lowercase "type" column.
        if "Type" in df.columns:
            df["type"] = df["Type"]
        elif "type" not in df.columns:
            df["type"] = ""

        # Ensure Project, Priority and State columns exist
        for needed in ("project", "Priority", "State"):
            if needed not in df.columns:
                df[needed] = ""

        # 4) Select only the requested columns in the requested order
        desired_cols = [
            "ticket ID",
            "project",
            "Summary",
            "created",
            "updated",
            "Priority",
            "State",
            "type",
        ]
        df = df.loc[:, desired_cols]
    else:
        # Ensure even empty exports have only the requested columns
        df = pd.DataFrame(columns=[
            "ticket ID",
            "project",
            "Summary",
            "created",
            "updated",
            "Priority",
            "State",
            "type",
        ])

    # Prepare outputs directory and filename
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d_%H%M")
    base = sanitize_filename_component(args.tag)
    filename = f"{base}_{ts}.csv"
    out_path = out_dir / filename

    df.to_csv(out_path, index=False)
    print(f"Exported {len(df)} issues to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

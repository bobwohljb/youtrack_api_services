YouTrack Issues Exporter

Overview

This small tool fetches issues from JetBrains YouTrack using a permanent token stored in youtrack_api_token.txt at the repository root, and exports results to a CSV ready for import into Google Sheets.

Key features
- Reads the YouTrack permanent token from youtrack_api_token.txt (root of the repo)
- Uses a configurable search query (set via variables or CLI flags)
- Handles pagination to fetch all matching issues
- Flattens common custom fields (Assignee, State, Priority)
- Writes a timestamped CSV file into the outputs directory named after the tag

Project layout
- src/youtrack_api_services/
  - __init__.py
  - config.py
  - youtrack_client.py
  - export_issues.py (CLI entry)
- outputs/ (created automatically on first run)
- youtrack_api_token.txt (your permanent token; do not commit publicly)
- requirements.txt

Prerequisites
- Python 3.9+

Setup
1) Create or verify your token file exists at the repo root:
   youtrack_api_token.txt
   The file should contain only the token string on the first line.

2) Install dependencies:
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
   pip install -r requirements.txt

Running the exporter
The default query matches the request from the issue:
  tag: {customer: Canva} #Unresolved project: {Toolbox App} project: {IntelliJ IDEA} project: {IntelliJ Platform} project: Support project: {Enterprise Support}

Run with defaults:
  PYTHONPATH=src python -m youtrack_api_services.export_issues

Optional arguments:
  --base-url BASE_URL       YouTrack base URL (default: https://youtrack.jetbrains.com)
  --tag TAG                 Tag label used in the query and as filename base (default: "customer: Canva")
  --query QUERY             Full YouTrack search query (overrides the default query)
  --output-dir DIR         Output directory (default: outputs)

Examples
- Use the default query and tag:
  python -m youtrack_api_services.export_issues

- Override just the tag (and keep default composed query):
  PYTHONPATH=src python -m youtrack_api_services.export_issues --tag "customer: ACME"

- Provide a fully custom query:
  PYTHONPATH=src python -m youtrack_api_services.export_issues --query "project: {My Project} #Unresolved"

Output
CSV file will be written to outputs with a name like:
  customer_Canva_2025-11-19_1010.csv

Notes
- If you need more fields, adjust FIELDS_BASE and SELECTED_CUSTOM_FIELDS in src/youtrack_api_services/youtrack_client.py
- The tool flattens the common custom fields Assignee, State, and Priority when present.

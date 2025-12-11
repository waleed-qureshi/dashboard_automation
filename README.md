# AI ReportsTeam Performance

Minimal prototype for the "AI ReportsTeam Performance" project.

Features included:
- Backend API (FastAPI) with endpoints for insights, predictions, alerts, scores, and raw data.
- SQLite database and sample data generator.
- Basic analytics/ML functions for tasks, leads, and projects (predictions, alerts, scores, insights).
- A simple static dashboard (HTML + JS) that calls the APIs and shows JSON output.

Quick start (Windows PowerShell):

1. Create a virtualenv and activate it:

```powershell
python -m venv .venv; .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

2. Initialize sample data (this also trains basic models):

```powershell
python scripts\create_sample_data.py
```

3. Run the API:

```powershell
uvicorn app.main:app --reload
```

4. Open the dashboard in your browser:

file:///%CD%/dashboard/index.html

Notes:
- This is a prototype scaffolding. Models and rules are simple and intended as a starting point.
- Extend analytics in `app/analytics.py` and wire to real data ingestion for production.

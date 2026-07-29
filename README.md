# DataLens — Universal Data Intelligence

Upload any structured dataset (CSV, TSV, or Excel) and get an automatic
domain-aware analysis: dataset understanding, the 3 most valuable analyses,
findings, weak points, and recommendations — not just a sales dashboard.
Backend and frontend are a single process — no separate terminals to run.

## First-time setup (Windows)

Just **double-click `start.bat`**.

The first time you run it, it will:
1. Create a Python virtual environment (`venv`)
2. Install everything in `requirements.txt`
3. Launch the server and open your browser automatically at `http://127.0.0.1:8000`

Every time after that, double-clicking `start.bat` just launches it directly
(skips the setup since `venv` already exists) and opens your browser
automatically — no typing, no manual URLs.

## Manual setup (if you'd rather run it yourself)

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python run.py
```

## Supported file formats
`.csv`, `.tsv`, `.xlsx`, `.xls` — column roles (date, revenue, profit,
category, region, customer, etc.) are auto-detected from the header names or
inferred from the data if the names don't match anything known.

## Project structure

```
sales-insights-app/
  app/
    main.py              — FastAPI app: serves both the API and the frontend
    column_detector.py   — maps arbitrary column names to semantic roles
    kpi.py                — KPI/trend/breakdown computation
    insights.py           — ranked insight engine
    static/                — the BUILT frontend (do not hand-edit — see below)
  frontend/                — frontend SOURCE CODE (edit here, then rebuild)
  requirements.txt
  run.py                   — launches the server + opens your browser
  start.bat                — Windows one-click launcher
```

## If you want to change the frontend design or behavior

Edit files under `frontend/src/`, then rebuild and re-copy into the
backend's static folder:

```powershell
cd frontend
npm install      # first time only
npm run build
cd ..
Remove-Item -Recurse -Force app\static
Copy-Item -Recurse frontend\dist app\static
```

Then just run `start.bat` (or `python run.py`) again — the server will pick
up the newly built files automatically since it serves whatever is in
`app/static`.

For active frontend development with hot-reload instead of rebuilding every
time, run the backend (`python run.py`) and, separately, `npm run dev`
inside `frontend/` — set `VITE_API_BASE=http://127.0.0.1:8000` in a
`frontend/.env` file so the dev server talks to your backend on a different
port.

## Notes
- Nothing is persisted or sent anywhere beyond your own machine — each
  upload is processed in memory and discarded after the response is sent.
- If you ever move or rename this folder, delete `venv` and let `start.bat`
  recreate it — virtual environments hard-code absolute paths and break if
  the folder moves.

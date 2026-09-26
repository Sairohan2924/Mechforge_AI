# MechForge AI — Full Build v2.0.5

Intelligent Design-for-Manufacturing decision-support prototype with drawing extraction, deterministic DFM rules, CAD geometry parsing and 3D inspection, project database, authentication, AI engineering assistant, supplier estimate workspace, reports and email integration.

## v2.0.5 update
- Context-aware local AI Assistant fallback.
- Process-choice questions now explain the actual geometry/material reasoning instead of only repeating the DFM score.
- DFM risk questions report the real HIGH/MEDIUM findings and recommendations when present.
- Score, cost/time and CAD questions return the relevant project/CAD values.
- Cloud OpenAI Responses API remains optional; the local assistant works without an API key.

## Run on Windows
```text
py -3.14 -m pip install -r requirements.txt
py -3.14 -m streamlit run app.py
```
Or double-click `run_mechforge.bat`.

Demo login:
- Email: `demo@mechforge.ai`
- Password: `demo123`

## AI configuration
Optional environment variables:
- `OPENAI_API_KEY`
- `MECHFORGE_AI_MODEL`

For Streamlit Community Cloud, put secrets in the app Secrets settings rather than committing them to GitHub.

## Important engineering note
MechForge is decision-support software. CAD geometry, DFM rules, AI suggestions and supplier estimates must be reviewed by a qualified engineer and supplier before production.

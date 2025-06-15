# Research AI Assistant Frontend

This directory contains the frontend for the Research AI Assistant project.

## Traditional Web UI

The original frontend uses standard HTML/CSS/JS with FastAPI Jinja2 templates:

- `/templates`: Contains the HTML templates
- `/static`: Contains CSS and JavaScript assets

## Streamlit UI (New)

The application now supports Streamlit as an alternative frontend:

- `streamlit_app.py`: Main Streamlit application file

### Running the Streamlit Frontend

There are three ways to run the Streamlit frontend:

1. **Independent mode** - Run Streamlit separately while the API is running:
   ```bash
   python -m streamlit run frontend/streamlit_app.py
   ```

2. **Using the helper script** - Runs only Streamlit (API must be running separately):
   ```bash
   python scripts/run_streamlit.py
   ```

3. **Integrated mode** - Launch both API and Streamlit together:
   ```bash
   python -m src.api.main --streamlit
   ```

### Accessing the UI

- Traditional Web UI: http://localhost:8000
- Streamlit UI: http://localhost:8501

## Features

The Streamlit UI includes:

- Paper search functionality
- Selection of different RAG pipelines
- System status monitoring
- arXiv data loading interface
- Responsive paper result display 
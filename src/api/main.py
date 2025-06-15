import time
import logging
import subprocess
import sys
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import PlainTextResponse

from src.config.logging_config import setup_logging
from src.monitoring.metrics import get_metrics, metrics_collector
from src.api.routes import router
from src.config.settings import settings

setup_logging()
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Research AI Assistant",
    description="AI-powered research paper analysis system",
    version="1.0.0"
)

app.mount("/static", StaticFiles(directory="frontend/static"), name="static")
templates = Jinja2Templates(directory="frontend/templates")

@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start_time = time.time()
    
    response = await call_next(request)
    
    duration = time.time() - start_time
    method = request.method
    endpoint = request.url.path
    status = str(response.status_code)
    
    metrics_collector.increment_request(method, endpoint, status)
    metrics_collector.track_request_duration(method, endpoint, duration)
    
    return response

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": time.time()}

@app.get("/metrics")
async def metrics():
    return PlainTextResponse(get_metrics(), media_type="text/plain")

@app.get("/")
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

app.include_router(router, prefix="/api/v1")

def launch_streamlit():
    """Launch the Streamlit frontend in a separate process"""
    try:
        logger.info("Launching Streamlit frontend...")
        streamlit_process = subprocess.Popen(
            [sys.executable, "-m", "streamlit", "run", "frontend/streamlit_app.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        logger.info(f"Streamlit frontend started with PID: {streamlit_process.pid}")
        return streamlit_process
    except Exception as e:
        logger.error(f"Failed to launch Streamlit: {e}")
        return None

if __name__ == "__main__":
    import uvicorn
    import argparse
    
    parser = argparse.ArgumentParser(description="Research AI Assistant")
    parser.add_argument("--streamlit", action="store_true", help="Launch Streamlit frontend")
    args = parser.parse_args()
    
    streamlit_process = None
    if args.streamlit:
        streamlit_process = launch_streamlit()
    
    try:
        uvicorn.run(
            "src.api.main:app",
            host="0.0.0.0",
            port=settings.api_port,
            reload=True,
            log_level=settings.log_level.lower()
        )
    finally:
        # Clean up streamlit process if it was launched
        if streamlit_process:
            logger.info("Shutting down Streamlit frontend...")
            streamlit_process.terminate()
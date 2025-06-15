import time
import functools
import asyncio
from typing import Callable, Any
from prometheus_client import Counter, Histogram, Gauge, generate_latest
import logging

logger = logging.getLogger(__name__)

request_count = Counter('app_requests_total', 'Total requests', ['method', 'endpoint', 'status'])
request_duration = Histogram('app_request_duration_seconds', 'Request duration', ['method', 'endpoint'])
rag_pipeline_duration = Histogram('rag_pipeline_duration_seconds', 'RAG pipeline duration', ['pipeline_type'])
llm_generation_duration = Histogram('llm_generation_duration_seconds', 'LLM generation time')
weaviate_search_duration = Histogram('weaviate_search_duration_seconds', 'Weaviate search time')
active_connections = Gauge('app_active_connections', 'Active connections')
papers_in_db = Gauge('papers_in_database_total', 'Total papers in database')

def track_time(metric: Histogram):
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start_time
                metric.observe(duration)
        return wrapper
    return decorator

def track_rag_pipeline(pipeline_type: str):
    def decorator(func: Callable):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start_time
                rag_pipeline_duration.labels(pipeline_type=pipeline_type).observe(duration)
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start_time
                rag_pipeline_duration.labels(pipeline_type=pipeline_type).observe(duration)
        
        # Определяем тип функции (синхронная или асинхронная)
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator

@track_time(llm_generation_duration)
def track_llm_call(func: Callable):
    return func

@track_time(weaviate_search_duration)
def track_weaviate_call(func: Callable):
    return func

class MetricsCollector:
    def __init__(self):
        self.timers = {}
    
    def update_paper_count(self, count: int):
        papers_in_db.set(count)
    
    def increment_request(self, method: str, endpoint: str, status: str):
        request_count.labels(method=method, endpoint=endpoint, status=status).inc()
    
    def track_request_duration(self, method: str, endpoint: str, duration: float):
        request_duration.labels(method=method, endpoint=endpoint).observe(duration)
    
    def start_timer(self, name: str) -> float:
        """Начать таймер с указанным именем"""
        start_time = time.time()
        self.timers[name] = start_time
        return start_time
    
    def stop_timer(self, name: str, start_time: float = None) -> float:
        """Остановить таймер и вернуть продолжительность"""
        if start_time is None:
            start_time = self.timers.get(name)
            if start_time is None:
                logger.warning(f"Timer {name} not found")
                return 0.0
        
        duration = time.time() - start_time
        logger.debug(f"Timer {name}: {duration:.3f} seconds")
        return duration

metrics_collector = MetricsCollector()

def get_metrics():
    return generate_latest()
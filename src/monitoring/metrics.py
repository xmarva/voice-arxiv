import time
import functools
import asyncio
from typing import Callable, Any, Dict, Optional
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
    """Collect and manage metrics for monitoring"""
    
    def __init__(self):
        # Request metrics
        self.request_counter = Counter(
            'api_requests_total', 
            'Total number of API requests', 
            ['method', 'endpoint', 'status']
        )
        
        self.request_duration = Histogram(
            'api_request_duration_seconds', 
            'Request duration in seconds', 
            ['method', 'endpoint'],
            buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0)
        )
        
        # RAG pipeline metrics
        self.rag_counter = Counter(
            'rag_operations_total', 
            'Total number of RAG operations', 
            ['operation_type', 'status']
        )
        
        self.rag_duration = Histogram(
            'rag_operation_duration_seconds', 
            'RAG operation duration in seconds', 
            ['operation_type'],
            buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0, 120.0)
        )
        
        # LLM metrics
        self.llm_counter = Counter(
            'llm_calls_total', 
            'Total number of LLM calls', 
            ['model', 'status']
        )
        
        self.llm_duration = Histogram(
            'llm_inference_time_seconds', 
            'LLM inference time in seconds',
            buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0, 120.0)
        )
        
        # Token usage metrics
        self.token_usage_counter = Counter(
            'token_usage_total',
            'Total number of tokens used by LLMs',
            ['type']  # prompt, completion, total
        )
        
        self.token_cost_counter = Counter(
            'token_cost_total',
            'Total estimated cost of tokens in USD (multiplied by 10000)',
            ['type']  # prompt, completion, total
        )
        
        # Database metrics
        self.db_operation_counter = Counter(
            'db_operations_total', 
            'Total number of database operations', 
            ['operation_type', 'status']
        )
        
        self.db_operation_duration = Histogram(
            'db_operation_duration_seconds', 
            'Database operation duration in seconds', 
            ['operation_type'],
            buckets=(0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0)
        )
        
        # System metrics
        self.paper_count_gauge = Gauge('papers_total', 'Total number of papers in the system')
        
        # Timer storage (not exposed)
        self.timers = {}
    
    def increment_request(self, method: str, endpoint: str, status: str) -> None:
        """Increment the request counter for a specific method, endpoint, and status"""
        self.request_counter.labels(method=method, endpoint=endpoint, status=status).inc()
    
    def track_request_duration(self, method: str, endpoint: str, duration: float) -> None:
        """Track the duration of a request"""
        self.request_duration.labels(method=method, endpoint=endpoint).observe(duration)
    
    def increment_rag_operation(self, operation_type: str, status: str = "success") -> None:
        """Increment the RAG operation counter"""
        self.rag_counter.labels(operation_type=operation_type, status=status).inc()
    
    def track_rag_duration(self, operation_type: str, duration: float) -> None:
        """Track the duration of a RAG operation"""
        self.rag_duration.labels(operation_type=operation_type).observe(duration)
    
    def increment_llm_call(self, model: str = "default", status: str = "success") -> None:
        """Increment the LLM call counter"""
        self.llm_counter.labels(model=model, status=status).inc()
    
    def track_llm_duration(self, duration: float) -> None:
        """Track the duration of an LLM inference"""
        self.llm_duration.observe(duration)
    
    def track_token_usage(self, prompt_tokens: int, completion_tokens: int, total_tokens: int) -> None:
        """Track token usage for LLM calls"""
        self.token_usage_counter.labels(type="prompt").inc(prompt_tokens)
        self.token_usage_counter.labels(type="completion").inc(completion_tokens)
        self.token_usage_counter.labels(type="total").inc(total_tokens)
        
        # Track estimated costs (multiplied by 10000 to store as integer)
        # Using approximate OpenAI GPT-3.5 rates
        prompt_cost = prompt_tokens * 0.0015 / 1000 * 10000  # $0.0015 per 1K tokens
        completion_cost = completion_tokens * 0.002 / 1000 * 10000  # $0.002 per 1K tokens
        total_cost = prompt_cost + completion_cost
        
        self.token_cost_counter.labels(type="prompt").inc(prompt_cost)
        self.token_cost_counter.labels(type="completion").inc(completion_cost)
        self.token_cost_counter.labels(type="total").inc(total_cost)
    
    def increment_db_operation(self, operation_type: str, status: str = "success") -> None:
        """Increment the database operation counter"""
        self.db_operation_counter.labels(operation_type=operation_type, status=status).inc()
    
    def track_db_duration(self, operation_type: str, duration: float) -> None:
        """Track the duration of a database operation"""
        self.db_operation_duration.labels(operation_type=operation_type).observe(duration)
    
    def set_paper_count(self, count: int) -> None:
        """Set the current paper count"""
        self.paper_count_gauge.set(count)
    
    def start_timer(self, name: str) -> float:
        """Start a timer for measuring operation duration"""
        start_time = time.time()
        self.timers[name] = start_time
        return start_time
    
    def stop_timer(self, name: str, start_time: Optional[float] = None) -> float:
        """Stop a timer and return the duration"""
        if start_time is None:
            start_time = self.timers.get(name)
            if start_time is None:
                logger.warning(f"Timer {name} was not started")
                return 0
        
        duration = time.time() - start_time
        
        # Clean up timer
        if name in self.timers:
            del self.timers[name]
        
        return duration

# Create a global metrics collector instance
metrics_collector = MetricsCollector()

def get_metrics() -> str:
    """Get all metrics in Prometheus format"""
    return generate_latest().decode('utf-8')

def track_rag_pipeline(operation_type: str):
    """Decorator to track RAG pipeline operations"""
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = metrics_collector.start_timer(f"rag_{operation_type}")
            metrics_collector.increment_rag_operation(operation_type)
            
            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                metrics_collector.increment_rag_operation(operation_type, "error")
                raise
            finally:
                duration = metrics_collector.stop_timer(f"rag_{operation_type}", start_time)
                metrics_collector.track_rag_duration(operation_type, duration)
        
        return wrapper
    
    return decorator
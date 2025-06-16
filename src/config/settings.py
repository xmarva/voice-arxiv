import os
from typing import List, Literal
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    weaviate_url: str = "http://localhost:8080"
    weaviate_api_key: str = ""
    
    # LLM settings
    # Type of LLM to use: "openai_api" or "local_model"
    llm_type: Literal["openai_api", "local_model"] = "openai_api"
    
    # OpenAI API settings
    openai_api_key: str = ""
    openai_model_name: str = "gpt-3.5-turbo"
    
    # Local LLM settings
    local_llm_url: str = "http://llm-service:8000"
    local_llm_model: str = "mistral-7b-instruct-v0.2-q4_0"
    local_llm_port: int = 8001
    
    # Legacy settings (kept for backwards compatibility)
    huggingface_api_key: str = ""
    llm_model_name: str = "microsoft/DialoGPT-medium"
    hf_inference_model: str = "google/flan-t5-small"
    
    # Embedding model settings
    embedding_model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    
    # Service ports
    prometheus_port: int = 9090
    grafana_port: int = 3000
    api_port: int = 8000
    
    # Logging settings
    log_level: str = "INFO"
    log_file: str = "app.log"
    
    # arXiv settings
    arxiv_max_results: int = 50
    arxiv_categories: str = "cs.AI,cs.CL,cs.LG"
    
    class Config:
        env_file = ".env"
        case_sensitive = False
    
    @property
    def arxiv_categories_list(self) -> List[str]:
        return self.arxiv_categories.split(",")
    
    @property
    def is_using_openai(self) -> bool:
        """Check if OpenAI API is being used"""
        return self.llm_type == "openai_api"
    
    @property
    def is_using_local_model(self) -> bool:
        """Check if local LLM is being used"""
        return self.llm_type == "local_model"

settings = Settings()
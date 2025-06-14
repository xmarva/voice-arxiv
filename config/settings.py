import os
from typing import List
from pydantic import BaseSettings

class Settings(BaseSettings):
    weaviate_url: str = "http://localhost:8080"
    weaviate_api_key: str = ""
    
    huggingface_api_key: str
    llm_model_name: str = "microsoft/DialoGPT-medium"
    embedding_model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    
    prometheus_port: int = 9090
    grafana_port: int = 3000
    api_port: int = 8000
    
    log_level: str = "INFO"
    log_file: str = "app.log"
    
    arxiv_max_results: int = 50
    arxiv_categories: str = "cs.AI,cs.CL,cs.LG"
    
    class Config:
        env_file = ".env"
        case_sensitive = False
    
    @property
    def arxiv_categories_list(self) -> List[str]:
        return self.arxiv_categories.split(",")

settings = Settings()
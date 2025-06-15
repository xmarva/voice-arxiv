import logging
import weaviate
from typing import List, Dict, Any, Optional
from src.config.settings import settings

logger = logging.getLogger(__name__)

class WeaviateManager:
    def __init__(self):
        self.client = None
        self.schema_name = "ResearchPaper"
        self._connect()
        self._setup_schema()
    
    def _connect(self):
        try:
            if settings.weaviate_api_key:
                auth_config = weaviate.AuthApiKey(api_key=settings.weaviate_api_key)
                self.client = weaviate.Client(
                    url=settings.weaviate_url,
                    auth_client_secret=auth_config
                )
            else:
                self.client = weaviate.Client(url=settings.weaviate_url)
            
            logger.info(f"Connected to Weaviate at {settings.weaviate_url}")
            logger.info(f"Weaviate is ready: {self.client.is_ready()}")
        except Exception as e:
            logger.error(f"Failed to connect to Weaviate: {e}")
            raise
    
    def _setup_schema(self):
        schema = {
            "class": self.schema_name,
            "description": "Research papers from arXiv",
            "vectorizer": "none",
            "properties": [
                {
                    "name": "title",
                    "dataType": ["text"],
                    "description": "Title of the paper"
                },
                {
                    "name": "abstract", 
                    "dataType": ["text"],
                    "description": "Abstract of the paper"
                },
                {
                    "name": "authors",
                    "dataType": ["text[]"],
                    "description": "Authors of the paper"
                },
                {
                    "name": "categories",
                    "dataType": ["text[]"],
                    "description": "arXiv categories"
                },
                {
                    "name": "arxiv_id",
                    "dataType": ["text"],
                    "description": "arXiv identifier"
                },
                {
                    "name": "published_date",
                    "dataType": ["date"],
                    "description": "Publication date"
                },
                {
                    "name": "pdf_url",
                    "dataType": ["text"],
                    "description": "URL to PDF"
                }
            ]
        }
        
        try:
            if not self.client.schema.exists(self.schema_name):
                self.client.schema.create_class(schema)
                logger.info(f"Created schema for class {self.schema_name}")
            else:
                logger.info(f"Schema {self.schema_name} already exists")
        except Exception as e:
            logger.error(f"Failed to setup schema: {e}")
            raise
    
    def add_papers(self, papers: List[Dict[str, Any]], embeddings: List[List[float]]):
        try:
            with self.client.batch as batch:
                batch.batch_size = 100
                for i, paper in enumerate(papers):
                    batch.add_data_object(
                        data_object=paper,
                        class_name=self.schema_name,
                        vector=embeddings[i] if i < len(embeddings) else None
                    )
            logger.info(f"Added {len(papers)} papers to Weaviate")
        except Exception as e:
            logger.error(f"Failed to add papers: {e}")
            raise
    
    @router.post("/search", response_model=SearchResponse)
    @track_rag_pipeline("basic_search")
    async def search_papers(request: SearchRequest):
        try:
            weaviate_manager = get_weaviate_manager()
            embeddings_model = get_embeddings()
            
            # Получаем вектор запроса
            query_vector = embeddings_model.embed_query(request.query)
            
            # Выполняем поиск
            papers = weaviate_manager.search_papers(query_vector, request.limit)
            
            # Возвращаем результат
            return {
                "papers": papers,
                "query": request.query,
                "pipeline_type": request.pipeline_type
            }
        
        except Exception as e:
            logger.error(f"Search error: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    def get_paper_count(self) -> int:
        try:
            result = (
                self.client.query
                .aggregate(self.schema_name)
                .with_meta_count()
                .do()
            )
            count = result["data"]["Aggregate"][self.schema_name][0]["meta"]["count"]
            return count
        except Exception as e:
            logger.error(f"Failed to get paper count: {e}")
            return 0

_weaviate_manager = None

def get_weaviate_manager() -> WeaviateManager:
    global _weaviate_manager
    if _weaviate_manager is None:
        _weaviate_manager = WeaviateManager()
    return _weaviate_manager
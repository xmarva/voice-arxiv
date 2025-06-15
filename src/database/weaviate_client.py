# src/database/weaviate_client.py

import logging
import weaviate
from typing import List, Dict, Any, Optional
from src.config.settings import settings
import time

logger = logging.getLogger(__name__)

class WeaviateManager:
    def __init__(self):
        self.client = None
        self.schema_name = "ResearchPaper"
        self._connect()
        self._setup_schema()
    
    def _connect(self):
        try:
            # Добавляем повторные попытки подключения
            max_retries = 5
            retry_count = 0
            connected = False

            while not connected and retry_count < max_retries:
                try:
                    if settings.weaviate_api_key:
                        auth_config = weaviate.AuthApiKey(api_key=settings.weaviate_api_key)
                        self.client = weaviate.Client(
                            url=settings.weaviate_url,
                            auth_client_secret=auth_config,
                            timeout_config=(5, 15)  # (connect_timeout, read_timeout)
                        )
                    else:
                        self.client = weaviate.Client(
                            url=settings.weaviate_url,
                            timeout_config=(5, 15)  # (connect_timeout, read_timeout)
                        )
                    
                    # Проверяем готовность Weaviate
                    is_ready = self.client.is_ready()
                    if is_ready:
                        connected = True
                        logger.info(f"Connected to Weaviate at {settings.weaviate_url}")
                        logger.info(f"Weaviate is ready: {is_ready}")
                    else:
                        raise Exception("Weaviate is not ready")
                except Exception as e:
                    retry_count += 1
                    logger.warning(f"Failed to connect to Weaviate (attempt {retry_count}/{max_retries}): {e}")
                    time.sleep(2)  # Ожидаем 2 секунды перед повторной попыткой
            
            if not connected:
                logger.error(f"Failed to connect to Weaviate after {max_retries} attempts")
                raise Exception(f"Failed to connect to Weaviate after {max_retries} attempts")
                
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
                },
                {
                    "name": "content",
                    "dataType": ["text"],
                    "description": "Full content of the paper, if available"
                }
            ]
        }
        
        try:
            # Добавляем повторы для проверки существования схемы
            max_retries = 3
            retry_count = 0
            schema_checked = False
            
            while not schema_checked and retry_count < max_retries:
                try:
                    exists = self.client.schema.exists(self.schema_name)
                    schema_checked = True
                    
                    if not exists:
                        self.client.schema.create_class(schema)
                        logger.info(f"Created schema for class {self.schema_name}")
                    else:
                        logger.info(f"Schema {self.schema_name} already exists")
                except Exception as e:
                    retry_count += 1
                    logger.warning(f"Error checking schema (attempt {retry_count}/{max_retries}): {e}")
                    time.sleep(2)  # Ожидаем 2 секунды перед повторной попыткой
            
            if not schema_checked:
                logger.error(f"Failed to check schema existence after {max_retries} attempts")
                raise Exception(f"Failed to check schema after {max_retries} attempts")
                
        except Exception as e:
            logger.error(f"Failed to setup schema: {e}")
            raise
    
    def add_papers(self, papers: List[Dict[str, Any]], embeddings: List[List[float]]):
        try:
            with self.client.batch as batch:
                batch.batch_size = 50
                batch.timeout_retries = 3
                
                for i, paper in enumerate(papers):
                    vector = None
                    # Убедимся, что у нас есть действительный вектор для этого документа
                    if i < len(embeddings) and embeddings[i] is not None:
                        # Проверим, что embeddings[i] - это действительно список чисел с плавающей точкой
                        if isinstance(embeddings[i], list) and all(isinstance(x, float) for x in embeddings[i]):
                            vector = embeddings[i]
                        else:
                            logger.warning(f"Invalid embedding vector for paper {i}, skipping vector")
                    
                    try:
                        batch.add_data_object(
                            data_object=paper,
                            class_name=self.schema_name,
                            vector=vector
                        )
                    except Exception as e:
                        logger.error(f"Error adding paper {i}: {e}")
                        # Продолжаем с следующей статьей
                        continue
            logger.info(f"Added {len(papers)} papers to Weaviate")
        except Exception as e:
            logger.error(f"Failed to add papers: {e}")
            raise
    
    def search_papers(self, query_vector: List[float], limit: int = 5) -> List[Dict[str, Any]]:
        try:
            # Validate the vector before sending to Weaviate
            if not isinstance(query_vector, list) or not all(isinstance(x, float) for x in query_vector):
                logger.error(f"Invalid query vector format: {type(query_vector)}")
                return self._get_fallback_papers(limit)
                
            # Ensure the vector is the right length (truncate or pad if necessary)
            # This assumes your vectors should be 384-dimensional for sentence-transformers/all-MiniLM-L6-v2
            expected_dim = 384
            if len(query_vector) > expected_dim:
                logger.warning(f"Query vector too long ({len(query_vector)}), truncating to {expected_dim}")
                query_vector = query_vector[:expected_dim]
            elif len(query_vector) < expected_dim:
                logger.warning(f"Query vector too short ({len(query_vector)}), padding to {expected_dim}")
                query_vector = query_vector + [0.0] * (expected_dim - len(query_vector))
                
            try:
                result = (
                    self.client.query
                    .get(self.schema_name, ["title", "abstract", "authors", "arxiv_id", "categories", "pdf_url"])
                    .with_near_vector({"vector": query_vector})
                    .with_limit(limit)
                    .with_additional(["distance"])
                    .do()
                )
                
                # Проверяем наличие результатов
                if result and "data" in result and "Get" in result["data"] and self.schema_name in result["data"]["Get"]:
                    papers = result["data"]["Get"][self.schema_name]
                    logger.info(f"Found {len(papers)} papers for query")
                    return papers
                else:
                    logger.warning("No papers found or unexpected response structure")
                    # Если не найдены релевантные статьи, возвращаем любые статьи из базы
                    return self._get_fallback_papers(limit)
            except Exception as search_error:
                logger.error(f"Vector search error: {search_error}")
                return self._get_fallback_papers(limit)
                
        except Exception as e:
            logger.error(f"Failed to search papers: {e}")
            # Если произошла ошибка, также возвращаем любые статьи
            return self._get_fallback_papers(limit)
    
    def _get_fallback_papers(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Получить любые статьи из базы, если не найдены релевантные"""
        try:
            logger.info("Getting fallback papers")
            result = (
                self.client.query
                .get(self.schema_name, ["title", "abstract", "authors", "arxiv_id", "categories", "pdf_url"])
                .with_limit(limit)
                .do()
            )
            
            if result and "data" in result and "Get" in result["data"] and self.schema_name in result["data"]["Get"]:
                papers = result["data"]["Get"][self.schema_name]
                logger.info(f"Found {len(papers)} fallback papers")
                return papers
            else:
                logger.warning("No fallback papers found")
                return []
        except Exception as e:
            logger.error(f"Failed to get fallback papers: {e}")
            return []
    
    def get_paper_count(self) -> int:
        try:
            max_retries = 3
            retry_count = 0
            
            while retry_count < max_retries:
                try:
                    result = (
                        self.client.query
                        .aggregate(self.schema_name)
                        .with_meta_count()
                        .do()
                    )
                    
                    # Проверяем структуру ответа
                    if result and "data" in result and "Aggregate" in result["data"] and self.schema_name in result["data"]["Aggregate"] and len(result["data"]["Aggregate"][self.schema_name]) > 0:
                        count = result["data"]["Aggregate"][self.schema_name][0]["meta"]["count"]
                        return count
                    else:
                        logger.warning("Unexpected response structure for paper count")
                        return 0
                        
                except Exception as e:
                    retry_count += 1
                    logger.warning(f"Error getting paper count (attempt {retry_count}/{max_retries}): {e}")
                    
                    if retry_count >= max_retries:
                        break
                    
                    time.sleep(2)  # Ожидаем 2 секунды перед повторной попыткой
            
            # Если все попытки не удались
            return 0
            
        except Exception as e:
            logger.error(f"Failed to get paper count: {e}")
            return 0
    
    def add_paper_from_file(self, title: str, content: str, authors: List[str] = None, categories: List[str] = None, 
                           paper_id: str = None, embeddings_model = None) -> bool:
        """Добавить статью из файла в базу данных"""
        try:
            paper = {
                "title": title,
                "abstract": content[:500] if content else "",  # Используем первые 500 символов как аннотацию
                "content": content,
                "authors": authors or [],
                "categories": categories or ["unknown"],
                "arxiv_id": paper_id or f"custom-{int(time.time())}",
                "published_date": None,
                "pdf_url": None
            }
            
            # Генерируем вектор для статьи, если есть модель для эмбеддингов
            if embeddings_model:
                try:
                    # Формируем текст для эмбеддинга (заголовок + первые 1000 символов контента)
                    embedding_text = f"{title} {content[:1000]}"
                    vector = embeddings_model.embed_query(embedding_text)
                    
                    # Проверяем, что вектор валидный
                    if vector and isinstance(vector, list) and all(isinstance(x, float) for x in vector):
                        self.add_papers([paper], [vector])
                    else:
                        logger.warning("Generated embedding vector is not valid, adding paper without vector")
                        self.add_papers([paper], [])
                except Exception as e:
                    logger.error(f"Error generating embeddings for uploaded paper: {e}")
                    # Если не удалось сгенерировать эмбеддинги, добавляем статью без вектора
                    self.add_papers([paper], [])
            else:
                self.add_papers([paper], [])
                
            return True
        except Exception as e:
            logger.error(f"Failed to add paper from file: {e}")
            return False
    
    def list_papers(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """Получить список всех статей в базе"""
        try:
            result = (
                self.client.query
                .get(self.schema_name, ["title", "abstract", "authors", "arxiv_id", "categories", "pdf_url"])
                .with_limit(limit)
                .with_offset(offset)
                .do()
            )
            
            if result and "data" in result and "Get" in result["data"] and self.schema_name in result["data"]["Get"]:
                papers = result["data"]["Get"][self.schema_name]
                return papers
            else:
                return []
                
        except Exception as e:
            logger.error(f"Failed to list papers: {e}")
            return []

    def get_paper_by_id(self, paper_id: str) -> Dict[str, Any]:
        """Получить статью по ID"""
        try:
            result = (
                self.client.query
                .get(self.schema_name, ["title", "abstract", "authors", "arxiv_id", "categories", "pdf_url", "content"])
                .with_where({
                    "path": ["arxiv_id"],
                    "operator": "Equal",
                    "valueString": paper_id
                })
                .with_limit(1)
                .do()
            )
            
            if result and "data" in result and "Get" in result["data"] and self.schema_name in result["data"]["Get"]:
                papers = result["data"]["Get"][self.schema_name]
                if papers:
                    logger.info(f"Found paper with ID {paper_id}")
                    return papers[0]
                else:
                    logger.warning(f"No paper found with ID {paper_id}")
                    return None
            else:
                logger.warning(f"Unexpected response structure when getting paper by ID {paper_id}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to get paper by ID {paper_id}: {e}")
            return None

_weaviate_manager = None

def get_weaviate_manager() -> WeaviateManager:
    global _weaviate_manager
    if _weaviate_manager is None:
        _weaviate_manager = WeaviateManager()
    return _weaviate_manager
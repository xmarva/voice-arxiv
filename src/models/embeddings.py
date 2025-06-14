import logging
from typing import List
from langchain.embeddings.base import Embeddings
from sentence_transformers import SentenceTransformer
from config.settings import settings

logger = logging.getLogger(__name__)

class CustomEmbeddings(Embeddings):
    def __init__(self, model_name: str = None):
        self.model_name = model_name or settings.embedding_model_name
        self.model = None
        self._load_model()
    
    def _load_model(self):
        logger.info(f"Loading embedding model: {self.model_name}")
        try:
            self.model = SentenceTransformer(self.model_name)
            logger.info("Embedding model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            raise
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        if not self.model:
            raise ValueError("Embedding model not loaded")
        
        try:
            embeddings = self.model.encode(texts, convert_to_tensor=False)
            return embeddings.tolist()
        except Exception as e:
            logger.error(f"Error embedding documents: {e}")
            raise
    
    def embed_query(self, text: str) -> List[float]:
        if not self.model:
            raise ValueError("Embedding model not loaded")
        
        try:
            embedding = self.model.encode([text], convert_to_tensor=False)
            return embedding[0].tolist()
        except Exception as e:
            logger.error(f"Error embedding query: {e}")
            raise

def get_embeddings() -> CustomEmbeddings:
    return CustomEmbeddings()
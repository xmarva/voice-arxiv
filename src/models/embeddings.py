import logging
from typing import List
from langchain.embeddings.base import Embeddings
from transformers import AutoTokenizer, AutoModel
import torch
import numpy as np
from src.config.settings import settings

logger = logging.getLogger(__name__)

class CustomEmbeddings(Embeddings):
    def __init__(self, model_name: str = None):
        self.model_name = model_name or settings.embedding_model_name
        self.model = None
        self.tokenizer = None
        self._load_model()
    
    def _load_model(self):
        logger.info(f"Loading embedding model: {self.model_name}")
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self.model = AutoModel.from_pretrained(self.model_name)
            logger.info("Embedding model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            raise
    
    def _mean_pooling(self, model_output, attention_mask):
        token_embeddings = model_output[0]
        input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
        return torch.sum(token_embeddings * input_mask_expanded, 0) / torch.clamp(input_mask_expanded.sum(0), min=1e-9)
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        if not self.model or not self.tokenizer:
            raise ValueError("Model not loaded")
        
        try:
            encoded_input = self.tokenizer(texts, padding=True, truncation=True, return_tensors='pt')
            with torch.no_grad():
                model_output = self.model(**encoded_input)
            embeddings = self._mean_pooling(model_output, encoded_input['attention_mask'])
            embeddings_list = embeddings.numpy().tolist()
            
            # Ensure we have a list of lists of floats
            result = []
            for emb in embeddings_list:
                if isinstance(emb, list):
                    result.append([float(x) for x in emb])
                else:
                    # If somehow we got a single value, wrap it
                    result.append([float(emb)])
            
            return result
        except Exception as e:
            logger.error(f"Error embedding documents: {e}")
            raise
    
    def embed_query(self, text: str) -> List[float]:
        if not self.model or not self.tokenizer:
            raise ValueError("Model not loaded")
        
        try:
            encoded_input = self.tokenizer([text], padding=True, truncation=True, return_tensors='pt')
            with torch.no_grad():
                model_output = self.model(**encoded_input)
            embeddings = self._mean_pooling(model_output, encoded_input['attention_mask'])
            
            # Convert to numpy, flatten, and then to list of floats
            numpy_array = embeddings.numpy()
            flattened = numpy_array.flatten()
            result = [float(x) for x in flattened]
            
            logger.info(f"Generated embedding vector with {len(result)} dimensions")
            return result
        except Exception as e:
            logger.error(f"Error embedding query: {e}")
            # Return a default embedding vector in case of error
            default_dim = 384  # Default dimension for all-MiniLM-L6-v2
            logger.warning(f"Returning default embedding vector with {default_dim} dimensions")
            return [0.0] * default_dim

def get_embeddings() -> CustomEmbeddings:
    return CustomEmbeddings()
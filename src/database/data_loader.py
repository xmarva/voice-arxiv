import logging
import os
import json
from typing import List, Dict, Any
from src.database.weaviate_client import get_weaviate_manager
from src.database.arxiv_scraper import ArxivScraper
from src.models.embeddings import get_embeddings
from src.config.settings import settings

logger = logging.getLogger(__name__)

class WeaviateDataLoader:
    def __init__(self):
        self.weaviate_manager = get_weaviate_manager()
        self.embedding_model = get_embeddings()
        self.scraper = ArxivScraper()
        self.data_dir = "data"
        self.embeddings_cache_file = os.path.join(self.data_dir, "embeddings_cache.json")
        
        # Create data directory if it doesn't exist
        os.makedirs(self.data_dir, exist_ok=True)
    
    def load_arxiv_data(self, max_results: int = 100) -> None:
        """Fetch arXiv papers and load them into Weaviate with embeddings."""
        try:
            # Fetch papers from arXiv or cache
            papers = self.scraper.fetch_papers(
                categories=settings.arxiv_categories_list,
                max_results=max_results
            )
            
            # Получаем ID существующих статей в Weaviate
            existing_papers = self.weaviate_manager.list_papers(limit=1000)
            existing_ids = {paper.get("arxiv_id") for paper in existing_papers}
            
            # Отфильтровываем только новые статьи
            new_papers = [paper for paper in papers if paper.get("arxiv_id") not in existing_ids]
            
            if not new_papers:
                logger.info("No new papers to add to Weaviate")
                return
                
            logger.info(f"Adding {len(new_papers)} new papers to Weaviate")
            
            # Generate embeddings for new papers
            embeddings = self._generate_embeddings_for_papers(new_papers)
            
            # Load papers with embeddings into Weaviate
            self.weaviate_manager.add_papers(new_papers, embeddings)
            
            logger.info(f"Successfully loaded {len(new_papers)} papers into Weaviate")
            
            # Verify the count of papers in Weaviate
            paper_count = self.weaviate_manager.get_paper_count()
            logger.info(f"Weaviate now contains {paper_count} papers")
            
        except Exception as e:
            logger.error(f"Error loading arXiv data into Weaviate: {e}")
            raise
    
    def _generate_embeddings_for_papers(self, papers: List[Dict[str, Any]]) -> List[List[float]]:
        """Generate embeddings for the given papers."""
        logger.info(f"Generating embeddings for {len(papers)} papers...")
        texts = [f"{p['title']} {p['abstract']}" for p in papers]
        return self.embedding_model.embed_documents(texts)
    
    def _get_or_generate_embeddings(self, papers: List[Dict[str, Any]]) -> List[List[float]]:
        """Get embeddings from cache or generate new ones."""
        # Этот метод оставлен для обратной совместимости
        return self._generate_embeddings_for_papers(papers)

def load_data(max_results: int = 100) -> None:
    """Utility function to load arXiv data into Weaviate."""
    loader = WeaviateDataLoader()
    loader.load_arxiv_data(max_results) 
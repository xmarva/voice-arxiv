import logging
import arxiv
import time
import os
import json
from datetime import datetime
from typing import List, Dict, Any
from src.config.settings import settings

logger = logging.getLogger(__name__)

class ArxivScraper:
    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        self.cache_file = os.path.join(data_dir, "arxiv_cache.json")
        
        # Create data directory if it doesn't exist
        os.makedirs(data_dir, exist_ok=True)
    
    def fetch_papers(self, categories: List[str] = None, max_results: int = 100) -> List[Dict[str, Any]]:
        """Fetch papers from arXiv API for specified categories."""
        if categories is None:
            categories = settings.arxiv_categories_list
            
        logger.info(f"Fetching up to {max_results} papers from categories: {categories}")
        
        # Проверяем кеш и загружаем новые статьи, если нужно
        cached_papers = []
        if os.path.exists(self.cache_file):
            logger.info(f"Found cached arXiv data at {self.cache_file}")
            with open(self.cache_file, 'r') as f:
                cached_papers = json.load(f)
            
            # Если в кеше достаточно статей, просто возвращаем нужное количество
            if len(cached_papers) >= max_results:
                logger.info(f"Using {max_results} papers from cache")
                return cached_papers[:max_results]
            
            # Если в кеше недостаточно статей, загрузим дополнительные
            logger.info(f"Cache has only {len(cached_papers)} papers, fetching {max_results - len(cached_papers)} more")
        
        # Формируем запрос к arXiv API
        category_query = " OR ".join([f"cat:{cat}" for cat in categories])
        
        client = arxiv.Client(
            page_size=100,
            delay_seconds=3.0,
            num_retries=5
        )
        
        # Определяем, сколько новых статей нужно загрузить
        papers_to_fetch = max_results - len(cached_papers)
        
        if papers_to_fetch <= 0:
            return cached_papers[:max_results]
        
        search = arxiv.Search(
            query=category_query,
            max_results=papers_to_fetch,
            sort_by=arxiv.SortCriterion.SubmittedDate
        )
        
        new_papers = []
        try:
            # Создаем множество существующих ID для проверки дубликатов
            existing_ids = {paper["arxiv_id"] for paper in cached_papers}
            
            for result in client.results(search):
                arxiv_id = result.entry_id.split('/')[-1]
                
                # Пропускаем дубликаты
                if arxiv_id in existing_ids:
                    logger.debug(f"Skipping duplicate paper with ID: {arxiv_id}")
                    continue
                
                paper = {
                    "title": result.title,
                    "abstract": result.summary,
                    "authors": [author.name for author in result.authors],
                    "categories": result.categories,
                    "arxiv_id": arxiv_id,
                    "published_date": result.published.isoformat() if result.published else None,
                    "pdf_url": result.pdf_url
                }
                new_papers.append(paper)
                existing_ids.add(arxiv_id)
                logger.debug(f"Fetched paper: {paper['title']}")
                
                # Add a small delay to be nice to the API
                time.sleep(0.1)
            
            # Объединяем новые и кешированные статьи
            all_papers = cached_papers + new_papers
            logger.info(f"Successfully fetched {len(new_papers)} new papers, total: {len(all_papers)}")
            
            # Cache the results
            self._save_to_cache(all_papers)
            
            return all_papers[:max_results]
        
        except Exception as e:
            logger.error(f"Error fetching papers from arXiv: {e}")
            # Если произошла ошибка, возвращаем то, что есть в кеше
            if cached_papers:
                logger.info(f"Returning {len(cached_papers)} papers from cache due to fetch error")
                return cached_papers[:max_results]
            raise
    
    def _save_to_cache(self, papers: List[Dict[str, Any]]) -> None:
        """Save fetched papers to cache file."""
        try:
            with open(self.cache_file, 'w') as f:
                json.dump(papers, f, indent=2)
            logger.info(f"Saved {len(papers)} papers to cache at {self.cache_file}")
        except Exception as e:
            logger.error(f"Error saving papers to cache: {e}") 
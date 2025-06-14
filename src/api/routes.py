import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from src.database.weaviate_client import get_weaviate_manager
from src.models.embeddings import get_embeddings
from src.monitoring.metrics import track_rag_pipeline

logger = logging.getLogger(__name__)
router = APIRouter()

class SearchRequest(BaseModel):
    query: str
    pipeline_type: str = "simple"
    limit: int = 5

class SearchResponse(BaseModel):
    papers: List[dict]
    query: str
    pipeline_type: str
    total_time: Optional[float] = None

class StatsResponse(BaseModel):
    paper_count: int
    system_status: str

@router.post("/search", response_model=SearchResponse)
@track_rag_pipeline("basic_search")
async def search_papers(request: SearchRequest):
    try:
        weaviate_manager = get_weaviate_manager()
        embeddings_model = get_embeddings()
        
        query_vector = embeddings_model.embed_query(request.query)
        papers = weaviate_manager.search_papers(query_vector, request.limit)
        
        return SearchResponse(
            papers=papers,
            query=request.query,
            pipeline_type=request.pipeline_type
        )
    
    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats", response_model=StatsResponse)
async def get_stats():
    try:
        weaviate_manager = get_weaviate_manager()
        paper_count = weaviate_manager.get_paper_count()
        
        return StatsResponse(
            paper_count=paper_count,
            system_status="online"
        )
    
    except Exception as e:
        logger.error(f"Stats error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/load-data")
async def load_sample_data():
    try:
        return {"message": "Data loading endpoint - to be implemented"}
    except Exception as e:
        logger.error(f"Data loading error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
import logging
import os
import io
import PyPDF2
from typing import List, Optional, Union
from fastapi import APIRouter, HTTPException, BackgroundTasks, UploadFile, File, Form, Query
from pydantic import BaseModel
from src.database.weaviate_client import get_weaviate_manager
from src.models.embeddings import get_embeddings
from src.monitoring.metrics import track_rag_pipeline
from src.database.data_loader import load_data
from src.rag.pipeline import get_rag_pipeline
from src.config.settings import settings
import asyncio
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)
router = APIRouter()
# Create a thread pool for handling synchronous operations
thread_executor = ThreadPoolExecutor(max_workers=4)

class SearchRequest(BaseModel):
    query: str
    limit: int = 5

class SearchResponse(BaseModel):
    papers: List[dict] = []
    query: str
    result: Optional[str] = None
    total_time: Optional[float] = None

class PaperQueryRequest(BaseModel):
    paper_id: str
    query: str

class PaperQueryResponse(BaseModel):
    paper: Optional[dict] = None
    query: str
    result: Optional[str] = None

class StatsResponse(BaseModel):
    paper_count: int
    system_status: str
    llm_model: str
    embedding_model: str

class LoadDataRequest(BaseModel):
    count: int = 100
    categories: Optional[str] = None

class PaperUploadResponse(BaseModel):
    success: bool
    message: str
    paper_id: Optional[str] = None

class PaperListResponse(BaseModel):
    papers: List[dict]
    total: int

@router.post("/search", response_model=SearchResponse)
@track_rag_pipeline("search")
async def search_papers(request: SearchRequest):
    """Search and analyze papers based on user query"""
    try:
        rag_pipeline = get_rag_pipeline()
        
        # Run the synchronous process_query in a thread pool to avoid blocking
        result = await asyncio.get_event_loop().run_in_executor(
            thread_executor,
            lambda: rag_pipeline.process_query(request.query, request.limit)
        )
        
        return SearchResponse(
            papers=result["papers"],
            query=result["query"],
            result=result["result"]
        )
    
    except Exception as e:
        logger.error(f"Search error: {e}")
        return SearchResponse(
            papers=[],
            query=request.query,
            result="Unfortunately, we couldn't process your request. Please try again later."
        )

@router.post("/paper-query", response_model=PaperQueryResponse)
@track_rag_pipeline("paper_query")
async def query_paper(request: PaperQueryRequest):
    """Query a specific paper"""
    try:
        rag_pipeline = get_rag_pipeline()
        
        # Run the synchronous process_single_paper in a thread pool
        result = await asyncio.get_event_loop().run_in_executor(
            thread_executor,
            lambda: rag_pipeline.process_single_paper(request.paper_id, request.query)
        )
        
        return PaperQueryResponse(
            paper=result["paper"],
            query=result["query"],
            result=result["result"]
        )
    
    except Exception as e:
        logger.error(f"Paper query error: {e}")
        return PaperQueryResponse(
            paper=None,
            query=request.query,
            result=f"An error occurred while processing the query: {str(e)}"
        )

@router.get("/stats", response_model=StatsResponse)
def get_stats():
    """Get system statistics"""
    try:
        weaviate_manager = get_weaviate_manager()
        paper_count = weaviate_manager.get_paper_count()
        
        return StatsResponse(
            paper_count=paper_count,
            system_status="online",
            llm_model=settings.llm_model_name,
            embedding_model=settings.embedding_model_name
        )
    
    except Exception as e:
        logger.error(f"Stats error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def _load_data_background(count: int, categories: Optional[str] = None):
    """Background task to load arXiv data"""
    from src.config.settings import settings
    if categories:
        settings.arxiv_categories = categories
    load_data(max_results=count)

@router.post("/load-data")
def load_sample_data(request: LoadDataRequest, background_tasks: BackgroundTasks):
    """Load data from arXiv"""
    try:
        # Add the data loading task to background tasks
        background_tasks.add_task(_load_data_background, request.count, request.categories)
        return {"message": f"Data loading started in the background. Loading {request.count} papers."}
    except Exception as e:
        logger.error(f"Data loading error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/papers", response_model=PaperListResponse)
def list_papers(limit: int = Query(100, ge=1, le=1000), 
                     offset: int = Query(0, ge=0)):
    """Get a list of all papers in the database"""
    try:
        weaviate_manager = get_weaviate_manager()
        papers = weaviate_manager.list_papers(limit=limit, offset=offset)
        count = weaviate_manager.get_paper_count()
        
        return PaperListResponse(
            papers=papers,
            total=count
        )
    except Exception as e:
        logger.error(f"Error listing papers: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/upload-paper", response_model=PaperUploadResponse)
async def upload_paper(
    file: UploadFile = File(...),
    title: str = Form(...),
    authors: Optional[str] = Form(None),
    categories: Optional[str] = Form(None)
):
    """Upload a PDF paper to the database"""
    try:
        weaviate_manager = get_weaviate_manager()
        embeddings_model = get_embeddings()
        
        # Convert author and category strings to lists
        authors_list = authors.split(',') if authors else []
        categories_list = categories.split(',') if categories else []
        
        # Get file contents
        content = ""
        if file.filename.endswith('.pdf'):
            try:
                contents = await file.read()
                pdf_file = io.BytesIO(contents)
                
                # Extract text from PDF
                pdf_reader = PyPDF2.PdfReader(pdf_file)
                for page_num in range(len(pdf_reader.pages)):
                    page = pdf_reader.pages[page_num]
                    content += page.extract_text() + "\n"
            except Exception as e:
                logger.error(f"Error extracting text from PDF: {e}")
                raise HTTPException(status_code=400, detail=f"Could not process PDF: {e}")
        else:
            # For text files, just read the content
            content = (await file.read()).decode('utf-8')
        
        # Add paper to database
        success = weaviate_manager.add_paper_from_file(
            title=title,
            content=content,
            authors=authors_list,
            categories=categories_list,
            embeddings_model=embeddings_model
        )
        
        if success:
            return PaperUploadResponse(
                success=True,
                message="Paper uploaded successfully",
                paper_id=f"custom-{title}"
            )
        else:
            return PaperUploadResponse(
                success=False,
                message="Failed to upload paper"
            )
    except Exception as e:
        logger.error(f"Error uploading paper: {e}")
        return PaperUploadResponse(
            success=False,
            message=f"Error: {str(e)}"
        )
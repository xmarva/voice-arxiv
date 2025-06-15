import logging
from typing import List, Dict, Any, Optional
from langchain.schema import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

from src.models.embeddings import get_embeddings
from src.models.llm_manager import get_llm
from src.database.weaviate_client import get_weaviate_manager
from src.monitoring.metrics import metrics_collector

logger = logging.getLogger(__name__)

class RAGPipeline:
    def __init__(self):
        self.weaviate_manager = get_weaviate_manager()
        self.embeddings = get_embeddings()
        self.llm = get_llm()
        self.output_parser = StrOutputParser()
        logger.info("RAG Pipeline initialized")
    
    def _retrieve(self, query: str, limit: int = 5) -> List[Document]:
        """Получить релевантные документы из базы данных"""
        start_time = metrics_collector.start_timer("rag_retrieval")
        
        try:
            query_vector = self.embeddings.embed_query(query)
            results = self.weaviate_manager.search_papers(query_vector, limit)
            
            documents = []
            for result in results:
                content = f"Title: {result.get('title', '')}\n"
                content += f"Abstract: {result.get('abstract', '')}\n"
                content += f"Authors: {', '.join(result.get('authors', []))}\n"
                content += f"Categories: {', '.join(result.get('categories', []))}\n"
                content += f"arXiv ID: {result.get('arxiv_id', '')}"
                
                metadata = {
                    "arxiv_id": result.get("arxiv_id", ""),
                    "title": result.get("title", ""),
                    "categories": result.get("categories", []),
                    "similarity": 1 - result.get("_additional", {}).get("distance", 0) if "_additional" in result else 0
                }
                
                documents.append(Document(page_content=content, metadata=metadata))
            
            return documents
        
        finally:
            metrics_collector.stop_timer("rag_retrieval", start_time)
    
    def _format_documents(self, documents: List[Document]) -> str:
        """Форматировать документы для использования в промпте"""
        document_strings = []
        for i, doc in enumerate(documents):
            doc_string = f"[Document {i+1}]\n{doc.page_content}\n"
            document_strings.append(doc_string)
        
        return "\n\n".join(document_strings)
    
    def simple_search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Простой поиск статей по запросу"""
        start_time = metrics_collector.start_timer("rag_simple_search")
        
        try:
            query_vector = self.embeddings.embed_query(query)
            papers = self.weaviate_manager.search_papers(query_vector, limit)
            return papers
        
        finally:
            metrics_collector.stop_timer("rag_simple_search", start_time)
    
    def process_query(self, query: str, limit: int = 5) -> Dict[str, Any]:
        """Единый метод для обработки запроса пользователя"""
        start_time = metrics_collector.start_timer("rag_process_query")
        
        try:
            # Поиск релевантных статей
            papers = self.simple_search(query, limit)
            
            # Получение документов для RAG
            documents = self._retrieve(query, limit)
            
            if not documents:
                result = "Не удалось найти релевантные статьи по вашему запросу. Попробуйте изменить запрос или загрузить больше статей."
                return {
                    "papers": papers,
                    "query": query,
                    "result": result
                }
            
            # Форматирование документов для промпта
            formatted_docs = self._format_documents(documents)
            
            # Создание промпта для LLM
            prompt_template = """
            Ты - исследовательский ассистент, помогающий с научными статьями.
            Ответь на следующий запрос, основываясь ТОЛЬКО на предоставленных исследовательских статьях.
            Если статьи не содержат информацию для прямого ответа на запрос, синтезируй то, что доступно,
            и четко укажи, когда ты делаешь выводы за пределами того, что есть в статьях.
            
            Запрос: {query}
            
            Исследовательские статьи:
            {documents}
            
            Предоставь подробный и хорошо структурированный ответ, который напрямую отвечает на запрос.
            Включи конкретные ссылки на статьи, когда это уместно.
            """
            
            # Создание и запуск цепочки обработки
            chain_input = {"query": query, "documents": formatted_docs}
            prompt = prompt_template.format(**chain_input)
            
            # Генерация ответа с помощью LLM
            result = self.llm._call(prompt)
            
            return {
                "papers": papers,
                "query": query,
                "result": result
            }
            
        except Exception as e:
            logger.error(f"Error in RAG process_query: {e}")
            return {
                "papers": [],
                "query": query,
                "result": f"Произошла ошибка при обработке запроса: {str(e)}"
            }
            
        finally:
            metrics_collector.stop_timer("rag_process_query", start_time)
    
    def process_single_paper(self, paper_id: str, query: str) -> Dict[str, Any]:
        """Обработка запроса по конкретной статье"""
        start_time = metrics_collector.start_timer("rag_process_single_paper")
        
        try:
            # Получение статьи по ID
            paper = self.weaviate_manager.get_paper_by_id(paper_id)
            
            if not paper:
                return {
                    "paper": None,
                    "query": query,
                    "result": f"Статья с ID {paper_id} не найдена."
                }
            
            # Создание документа для RAG
            content = f"Title: {paper.get('title', '')}\n"
            content += f"Abstract: {paper.get('abstract', '')}\n"
            content += f"Authors: {', '.join(paper.get('authors', []))}\n"
            content += f"Categories: {', '.join(paper.get('categories', []))}\n"
            content += f"arXiv ID: {paper.get('arxiv_id', '')}"
            
            if paper.get('content'):
                content += f"\n\nContent: {paper.get('content')}"
            
            # Создание промпта для LLM
            prompt_template = """
            Ты - исследовательский ассистент, помогающий с научными статьями.
            Ответь на следующий запрос, основываясь ТОЛЬКО на предоставленной статье.
            Если статья не содержит информацию для прямого ответа на запрос, укажи это.
            
            Запрос: {query}
            
            Статья:
            {content}
            
            Предоставь подробный и хорошо структурированный ответ, который напрямую отвечает на запрос.
            """
            
            # Создание и запуск цепочки обработки
            chain_input = {"query": query, "content": content}
            prompt = prompt_template.format(**chain_input)
            
            # Генерация ответа с помощью LLM
            result = self.llm._call(prompt)
            
            return {
                "paper": paper,
                "query": query,
                "result": result
            }
            
        except Exception as e:
            logger.error(f"Error in RAG process_single_paper: {e}")
            return {
                "paper": None,
                "query": query,
                "result": f"Произошла ошибка при обработке запроса: {str(e)}"
            }
            
        finally:
            metrics_collector.stop_timer("rag_process_single_paper", start_time)

def get_rag_pipeline() -> RAGPipeline:
    return RAGPipeline() 
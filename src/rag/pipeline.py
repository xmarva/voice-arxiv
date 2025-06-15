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
        """Retrieve relevant documents from the database"""
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
        """Format documents for use in prompt"""
        document_strings = []
        for i, doc in enumerate(documents):
            doc_string = f"[Document {i+1}]\n{doc.page_content}\n"
            document_strings.append(doc_string)
        
        return "\n\n".join(document_strings)
    
    def simple_search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Simple search for papers based on query"""
        start_time = metrics_collector.start_timer("rag_simple_search")
        
        try:
            query_vector = self.embeddings.embed_query(query)
            papers = self.weaviate_manager.search_papers(query_vector, limit)
            return papers
        
        finally:
            metrics_collector.stop_timer("rag_simple_search", start_time)
    
    def process_query(self, query: str, limit: int = 5) -> Dict[str, Any]:
        """Unified method for processing user queries"""
        start_time = metrics_collector.start_timer("rag_process_query")
        
        try:
            # Search for relevant papers
            papers = self.simple_search(query, limit)
            
            # Retrieve documents for RAG
            documents = self._retrieve(query, limit)
            
            # Handle case when no relevant documents are found
            if not documents:
                # Create fallback response that's helpful even without specific documents
                fallback_prompt = """
                You are a research assistant helping with scientific papers.
                The user asked this question: {query}
                
                Unfortunately, no relevant research papers were found in the database for this query.
                
                Please provide:
                1. A helpful response acknowledging the lack of specific papers
                2. General information about the topic if possible
                3. Suggestions for how the user might reformulate their query
                4. Alternative research directions they might consider
                
                Make your response well-structured and informative even without specific papers to reference.
                """
                
                formatted_prompt = fallback_prompt.format(query=query)
                result = self.llm._call(formatted_prompt)
                
                return {
                    "papers": papers,
                    "query": query,
                    "result": result
                }
            
            # Format documents for prompt
            formatted_docs = self._format_documents(documents)
            
            # Create prompt for LLM
            prompt_template = """
            You are a research assistant helping with scientific papers.
            Answer the following query based ONLY on the provided research papers.
            If the papers don't contain information for a direct answer to the query, synthesize what is available,
            and clearly indicate when you are making inferences beyond what's in the papers.
            
            Query: {query}
            
            Research Papers:
            {documents}
            
            Provide a detailed and well-structured response that directly addresses the query.
            Include specific references to papers when appropriate.
            Your response should:
            1. Summarize key findings relevant to the query
            2. Present information in a logical, organized way with clear sections
            3. Highlight areas of consensus and disagreement across papers if relevant
            4. If the papers don't fully address the query, acknowledge this and provide insights based on what is available
            """
            
            # Create and run processing chain
            chain_input = {"query": query, "documents": formatted_docs}
            prompt = prompt_template.format(**chain_input)
            
            # Generate response using LLM
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
                "result": f"An error occurred while processing the query: {str(e)}"
            }
            
        finally:
            metrics_collector.stop_timer("rag_process_query", start_time)
    
    def process_single_paper(self, paper_id: str, query: str) -> Dict[str, Any]:
        """Process query for a specific paper"""
        start_time = metrics_collector.start_timer("rag_process_single_paper")
        
        try:
            # Get paper by ID
            paper = self.weaviate_manager.get_paper_by_id(paper_id)
            
            if not paper:
                # Create structured response for when paper is not found
                not_found_prompt = f"""
                You are a research assistant helping with scientific papers.
                The user asked about paper with ID {paper_id} with this query: {query}
                
                Unfortunately, the requested paper could not be found in the database.
                
                Please provide a helpful response that:
                1. Acknowledges the paper was not found
                2. Suggests alternatives for finding this paper (like searching on arXiv directly)
                3. Offers guidance on how to use the system more effectively
                """
                
                result = self.llm._call(not_found_prompt)
                
                return {
                    "paper": None,
                    "query": query,
                    "result": result
                }
            
            # Create document for RAG
            content = f"Title: {paper.get('title', '')}\n"
            content += f"Abstract: {paper.get('abstract', '')}\n"
            content += f"Authors: {', '.join(paper.get('authors', []))}\n"
            content += f"Categories: {', '.join(paper.get('categories', []))}\n"
            content += f"arXiv ID: {paper.get('arxiv_id', '')}"
            
            if paper.get('content'):
                content += f"\n\nContent: {paper.get('content')}"
            
            # Create prompt for LLM
            prompt_template = """
            You are a research assistant helping with scientific papers.
            Answer the following query based ONLY on the provided paper.
            If the paper doesn't contain information for a direct answer to the query, clearly indicate this.
            
            Query: {query}
            
            Paper:
            {content}
            
            Provide a detailed and well-structured response that directly addresses the query.
            Your response should:
            1. Focus specifically on information from this paper relevant to the query
            2. Be organized with clear sections and logical flow
            3. Include specific references to sections or findings from the paper
            4. If the paper doesn't address the query, provide a helpful explanation of what the paper does cover
            """
            
            # Create and run processing chain
            chain_input = {"query": query, "content": content}
            prompt = prompt_template.format(**chain_input)
            
            # Generate response using LLM
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
                "result": f"An error occurred while processing the query: {str(e)}"
            }
            
        finally:
            metrics_collector.stop_timer("rag_process_single_paper", start_time)

def get_rag_pipeline() -> RAGPipeline:
    return RAGPipeline() 
import logging
import os
import re
from typing import Optional, List, Dict, Any
from langchain.llms.base import LLM
from langchain.callbacks.manager import CallbackManagerForLLMRun
from src.config.settings import settings
from src.monitoring.metrics import metrics_collector

logger = logging.getLogger(__name__)

class SimpleLLM(LLM):
    """A simple rule-based LLM that doesn't require API keys or GPU"""
    model_name: str = "simple-local-llm"
    
    def __init__(self):
        super().__init__()
        logger.info("Initialized Simple Local LLM")
    
    @property
    def _llm_type(self) -> str:
        return "simple_local_llm"
    
    def _call(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs
    ) -> str:
        """Generate a response based on simple rules and pattern matching"""
        start_time = metrics_collector.start_timer("llm_inference_time")
        
        try:
            # Extract the query from the prompt
            query_match = re.search(r"Запрос: (.*?)(?:\n\n|$)", prompt, re.DOTALL)
            query = query_match.group(1).strip() if query_match else "Unknown query"
            
            # Extract paper information from the prompt
            papers_info = []
            paper_sections = re.findall(r"\[Document \d+\](.*?)(?=\[Document \d+\]|\Z)", prompt, re.DOTALL)
            
            for section in paper_sections:
                title_match = re.search(r"Title: (.*?)(?:\n|$)", section)
                title = title_match.group(1) if title_match else "Unknown title"
                
                abstract_match = re.search(r"Abstract: (.*?)(?:\n[A-Z]|$)", section, re.DOTALL)
                abstract = abstract_match.group(1).strip() if abstract_match else "No abstract available"
                
                authors_match = re.search(r"Authors: (.*?)(?:\n|$)", section)
                authors = authors_match.group(1) if authors_match else "Unknown authors"
                
                papers_info.append({
                    "title": title,
                    "abstract": abstract[:100] + "..." if len(abstract) > 100 else abstract,
                    "authors": authors
                })
            
            # Generate a response based on the query and papers
            if "summarize" in query.lower() or "summary" in query.lower():
                response = self._generate_summary_response(papers_info, query)
            elif "explain" in query.lower() or "what is" in query.lower() or "how" in query.lower():
                response = self._generate_explanation_response(papers_info, query)
            elif "compare" in query.lower() or "difference" in query.lower():
                response = self._generate_comparison_response(papers_info, query)
            elif "find" in query.lower() or "search" in query.lower():
                response = self._generate_search_response(papers_info, query)
            else:
                response = self._generate_general_response(papers_info, query)
            
            metrics_collector.stop_timer("llm_inference_time", start_time)
            return response
            
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            metrics_collector.stop_timer("llm_inference_time", start_time)
            return "Извините, я не смог сгенерировать ответ на ваш запрос. Пожалуйста, попробуйте переформулировать вопрос."
    
    def _generate_summary_response(self, papers_info: List[Dict], query: str) -> str:
        """Generate a summary response based on the papers"""
        if not papers_info:
            return "Я не нашел статей, соответствующих вашему запросу."
        
        response = f"На основе найденных статей, вот краткое резюме по вашему запросу '{query}':\n\n"
        
        for i, paper in enumerate(papers_info[:3]):  # Limit to first 3 papers
            response += f"**Статья {i+1}: {paper['title']}**\n"
            response += f"{paper['abstract']}\n\n"
        
        if len(papers_info) > 3:
            response += f"Также найдено еще {len(papers_info) - 3} статей по этой теме.\n"
        
        return response
    
    def _generate_explanation_response(self, papers_info: List[Dict], query: str) -> str:
        """Generate an explanation response based on the papers"""
        if not papers_info:
            return "Я не нашел статей, которые могли бы помочь с объяснением по вашему запросу."
        
        response = f"Вот объяснение по вашему запросу '{query}', основанное на научных статьях:\n\n"
        
        # Extract relevant sentences from abstracts that might contain explanations
        explanations = []
        for paper in papers_info:
            abstract = paper["abstract"]
            sentences = re.split(r'(?<=[.!?])\s+', abstract)
            relevant_sentences = [s for s in sentences if self._is_relevant_to_query(s, query)]
            if relevant_sentences:
                explanations.extend(relevant_sentences)
        
        if explanations:
            response += "\n".join(explanations[:5])  # Limit to first 5 relevant sentences
            response += f"\n\nЭто объяснение основано на статье \"{papers_info[0]['title']}\" авторов {papers_info[0]['authors']}."
        else:
            # If no relevant sentences found, use the first paper's abstract
            response += f"{papers_info[0]['abstract']}\n\n"
            response += f"Это информация из статьи \"{papers_info[0]['title']}\" авторов {papers_info[0]['authors']}."
        
        return response
    
    def _generate_comparison_response(self, papers_info: List[Dict], query: str) -> str:
        """Generate a comparison response based on the papers"""
        if len(papers_info) < 2:
            return "Для сравнения необходимо как минимум две статьи. Пожалуйста, уточните запрос."
        
        response = f"Сравнение по вашему запросу '{query}':\n\n"
        
        response += f"**Статья 1: {papers_info[0]['title']}**\n"
        response += f"Авторы: {papers_info[0]['authors']}\n"
        response += f"Основные идеи: {papers_info[0]['abstract']}\n\n"
        
        response += f"**Статья 2: {papers_info[1]['title']}**\n"
        response += f"Авторы: {papers_info[1]['authors']}\n"
        response += f"Основные идеи: {papers_info[1]['abstract']}\n\n"
        
        response += "**Сравнение:**\n"
        response += "Обе статьи относятся к области исследований искусственного интеллекта, но имеют разные подходы и фокус. "
        response += "Первая статья больше сосредоточена на теоретических аспектах, в то время как вторая предлагает практическое применение технологий."
        
        return response
    
    def _generate_search_response(self, papers_info: List[Dict], query: str) -> str:
        """Generate a search response based on the papers"""
        if not papers_info:
            return "Я не нашел статей, соответствующих вашему запросу."
        
        response = f"Результаты поиска по запросу '{query}':\n\n"
        
        for i, paper in enumerate(papers_info):
            response += f"{i+1}. **{paper['title']}**\n"
            response += f"   Авторы: {paper['authors']}\n"
            response += f"   Краткое описание: {paper['abstract']}\n\n"
        
        return response
    
    def _generate_general_response(self, papers_info: List[Dict], query: str) -> str:
        """Generate a general response based on the papers"""
        if not papers_info:
            return "Я не нашел статей, соответствующих вашему запросу."
        
        response = f"По вашему запросу '{query}' я нашел следующую информацию:\n\n"
        
        most_relevant_paper = papers_info[0]
        response += f"Согласно статье \"{most_relevant_paper['title']}\" авторов {most_relevant_paper['authors']}, "
        response += f"{most_relevant_paper['abstract']}\n\n"
        
        if len(papers_info) > 1:
            response += f"Также по этой теме найдено еще {len(papers_info) - 1} статей. "
            response += "Вы можете уточнить запрос, чтобы получить более конкретную информацию."
        
        return response
    
    def _is_relevant_to_query(self, sentence: str, query: str) -> bool:
        """Check if a sentence is relevant to the query"""
        query_words = set(re.findall(r'\w+', query.lower()))
        sentence_words = set(re.findall(r'\w+', sentence.lower()))
        
        # Remove common stop words
        stop_words = {'the', 'a', 'an', 'in', 'on', 'at', 'to', 'for', 'with', 'by', 'about', 'как', 'что', 'и', 'в', 'на'}
        query_words = query_words - stop_words
        
        # Check if there's significant overlap between query words and sentence words
        overlap = query_words.intersection(sentence_words)
        return len(overlap) >= 1  # At least one significant word should match

def get_llm() -> LLM:
    """Factory function to get the LLM"""
    return SimpleLLM()
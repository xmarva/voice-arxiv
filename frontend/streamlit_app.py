import streamlit as st
import requests
import json
import time
import os
from typing import Dict, Any, List
import pandas as pd

# Configure the app
st.set_page_config(
    page_title="PaperAI",
    page_icon="📚",
    layout="wide"
)

# Get API URL from environment or use default
API_URL = os.environ.get("API_URL", "http://api:8000")
SEARCH_ENDPOINT = f"{API_URL}/api/v1/search"
PAPER_QUERY_ENDPOINT = f"{API_URL}/api/v1/paper-query"
STATS_ENDPOINT = f"{API_URL}/api/v1/stats"
HEALTH_ENDPOINT = f"{API_URL}/health"
LOAD_DATA_ENDPOINT = f"{API_URL}/api/v1/load-data"
PAPERS_ENDPOINT = f"{API_URL}/api/v1/papers"
UPLOAD_ENDPOINT = f"{API_URL}/api/v1/upload-paper"

# Функция для проверки доступности API
def check_system_status() -> bool:
    """Check if the API is available"""
    try:
        response = requests.get(HEALTH_ENDPOINT, timeout=2)
        return response.status_code == 200
    except:
        return False

# Функция для получения статистики системы
def get_system_stats() -> Dict[str, Any]:
    """Get system statistics"""
    try:
        response = requests.get(STATS_ENDPOINT, timeout=2)
        if response.status_code == 200:
            return response.json()
        return {"paper_count": "N/A", "system_status": "Error", "llm_model": "Unknown", "embedding_model": "Unknown"}
    except:
        return {"paper_count": "N/A", "system_status": "Offline", "llm_model": "Unknown", "embedding_model": "Unknown"}

# Функция для поиска статей
def search_papers(query: str, limit: int) -> Dict[str, Any]:
    """Search for papers using the API"""
    try:
        payload = {
            "query": query,
            "limit": limit
        }
        response = requests.post(SEARCH_ENDPOINT, json=payload)
        if response.status_code == 200:
            return response.json()
        return {"papers": [], "result": None, "query": query}
    except Exception as e:
        st.error(f"Error searching papers: {e}")
        return {"papers": [], "result": None, "query": query}

# Функция для запроса к конкретной статье
def query_paper(paper_id: str, query: str) -> Dict[str, Any]:
    """Query a specific paper"""
    try:
        payload = {
            "paper_id": paper_id,
            "query": query
        }
        response = requests.post(PAPER_QUERY_ENDPOINT, json=payload)
        if response.status_code == 200:
            return response.json()
        return {"paper": None, "result": None, "query": query}
    except Exception as e:
        st.error(f"Error querying paper: {e}")
        return {"paper": None, "result": None, "query": query}

# Функция для загрузки данных из arXiv
def load_arxiv_data(count: int, categories: str = None) -> str:
    """Trigger data loading from arXiv"""
    try:
        payload = {"count": count}
        if categories:
            payload["categories"] = categories
        response = requests.post(LOAD_DATA_ENDPOINT, json=payload)
        if response.status_code == 200:
            return response.json()["message"]
        return f"Error: {response.status_code}"
    except Exception as e:
        return f"Error: {str(e)}"

# Функция для получения списка статей
def list_papers(limit: int = 100, offset: int = 0) -> Dict[str, Any]:
    """Get list of papers from the API"""
    try:
        params = {
            "limit": limit,
            "offset": offset
        }
        response = requests.get(PAPERS_ENDPOINT, params=params)
        if response.status_code == 200:
            return response.json()
        return {"papers": [], "total": 0}
    except Exception as e:
        st.error(f"Error listing papers: {e}")
        return {"papers": [], "total": 0}

# Функция для загрузки статьи
def upload_paper(file, title: str, authors: str = None, categories: str = None) -> Dict[str, Any]:
    """Upload a paper file to the API"""
    try:
        files = {"file": file}
        data = {
            "title": title,
            "authors": authors or "",
            "categories": categories or ""
        }
        
        response = requests.post(UPLOAD_ENDPOINT, files=files, data=data)
        if response.status_code == 200:
            return response.json()
        return {"success": False, "message": f"Error: {response.status_code}"}
    except Exception as e:
        return {"success": False, "message": f"Error: {str(e)}"}

# Функция для отображения статьи
def display_paper(paper: Dict[str, Any], expanded: bool = False):
    """Display a paper in the UI"""
    if not paper:
        return
    
    with st.expander(f"📄 {paper['title']}", expanded=expanded):
        col1, col2 = st.columns([3, 1])
        
        with col1:
            st.markdown(f"**Abstract**")
            st.markdown(paper.get("abstract", "No abstract available"))
        
        with col2:
            st.markdown(f"**ID**: {paper.get('arxiv_id', 'N/A')}")
            
            authors = paper.get('authors', [])
            if authors:
                st.markdown(f"**Authors**: {', '.join(authors[:3])}" + 
                        (f" and {len(authors)-3} more" if len(authors) > 3 else ""))
            
            categories = paper.get('categories', [])
            if categories:
                st.markdown(f"**Categories**: {', '.join(categories[:3])}" + 
                        (f" and {len(categories)-3} more" if len(categories) > 3 else ""))
            
            if "_additional" in paper and "distance" in paper["_additional"]:
                similarity = 1 - paper["_additional"]["distance"]
                st.metric("Similarity", f"{similarity:.3f}")
            
            if paper.get("pdf_url"):
                st.markdown(f"[Download PDF]({paper['pdf_url']})")
            
            # Добавляем кнопку для запроса к этой статье
            if st.button("Ask about this paper", key=f"ask_{paper.get('arxiv_id', 'custom')}"):
                st.session_state.selected_paper = paper
                st.session_state.active_tab = "ask_paper"
                st.rerun()

# Инициализация состояния сессии
if 'active_tab' not in st.session_state:
    st.session_state.active_tab = "search"

if 'selected_paper' not in st.session_state:
    st.session_state.selected_paper = None

if 'loading_data' not in st.session_state:
    st.session_state.loading_data = False

if 'loading_progress' not in st.session_state:
    st.session_state.loading_progress = 0

if 'loading_message' not in st.session_state:
    st.session_state.loading_message = ""

# Заголовок приложения
st.title("PaperAI")

# Получаем статистику системы
system_stats = get_system_stats()

# Создаем вкладки
tabs = ["Search", "Ask about Paper", "Upload Paper", "Browse Papers", "Settings"]
tab_icons = ["🔍", "📝", "📤", "📚", "⚙️"]

# Если идет загрузка данных, блокируем переход на другие вкладки
if st.session_state.loading_data:
    st.warning(st.session_state.loading_message)
    progress_bar = st.progress(st.session_state.loading_progress)
    
    if st.button("Cancel Loading"):
        st.session_state.loading_data = False
        st.session_state.loading_progress = 0
        st.session_state.loading_message = ""
        st.rerun()
else:
    # Отображаем вкладки как кнопки
    col1, col2, col3, col4, col5 = st.columns(5)
    cols = [col1, col2, col3, col4, col5]

    for i, (tab, icon) in enumerate(zip(tabs, tab_icons)):
        with cols[i]:
            if st.button(f"{icon} {tab}", key=f"tab_{tab}", use_container_width=True, 
                        type="primary" if st.session_state.active_tab == tab.lower().replace(" ", "_") else "secondary"):
                st.session_state.active_tab = tab.lower().replace(" ", "_")
                st.rerun()

st.divider()

# Вкладка поиска
if st.session_state.active_tab == "search":
    st.header("🔍 Search Research Papers")
    
    with st.form("search_form"):
        query = st.text_area("Ask about research papers...", 
                            placeholder="Example: Explain the key innovations in transformer models for NLP",
                            height=100)
        
        col1, col2 = st.columns([4, 1])
        with col1:
            st.caption("The AI will search for relevant papers and provide an answer based on them.")
        with col2:
            limit = st.number_input("Max papers", min_value=1, max_value=20, value=5)
        
        submit_button = st.form_submit_button("Search", type="primary", use_container_width=True)
    
    if submit_button:
        if not query:
            st.warning("Please enter a search query")
        else:
            with st.spinner("Searching and analyzing papers..."):
                result = search_papers(query, limit)
            
            papers = result.get("papers", [])
            rag_result = result.get("result")
            
            # Display RAG result
            if rag_result:
                st.header("AI Research Assistant Response")
                st.info(rag_result)
                st.divider()
            
            # Display paper results
            if papers:
                st.header("Relevant Research Papers")
                for paper in papers:
                    display_paper(paper)
            else:
                st.warning("No papers found for your query")

# Вкладка запроса к конкретной статье
elif st.session_state.active_tab == "ask_paper":
    st.header("📝 Ask about a Specific Paper")
    
    # Если статья уже выбрана
    if st.session_state.selected_paper:
        paper = st.session_state.selected_paper
        
        st.subheader(f"Selected Paper: {paper.get('title', 'Unknown')}")
        st.caption(f"ID: {paper.get('arxiv_id', 'N/A')} | Authors: {', '.join(paper.get('authors', ['Unknown']))}")
        
        with st.expander("Paper Abstract", expanded=True):
            st.markdown(paper.get("abstract", "No abstract available"))
        
        with st.form("paper_query_form"):
            query = st.text_area("Ask a question about this paper", 
                                placeholder="Example: Summarize the main findings of this paper",
                                height=100)
            
            submit_button = st.form_submit_button("Ask", type="primary", use_container_width=True)
        
        if submit_button:
            if not query:
                st.warning("Please enter a question")
            else:
                with st.spinner("Analyzing paper..."):
                    result = query_paper(paper.get('arxiv_id'), query)
                
                if result.get("result"):
                    st.header("AI Response")
                    st.info(result.get("result"))
                else:
                    st.error("Failed to get response")
        
        if st.button("Select a different paper"):
            st.session_state.selected_paper = None
            st.rerun()
    
    # Если статья не выбрана
    else:
        st.info("Select a paper to ask questions about it.")
        
        # Получаем список статей
        papers_data = list_papers(limit=10)
        papers = papers_data.get("papers", [])
        
        # Добавляем поле для ввода запроса
        query = st.text_area("Enter your question about papers", 
                            placeholder="Your question will be applied to the paper you select below",
                            height=100)
        
        if papers:
            st.subheader("Available Papers")
            for paper in papers:
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.markdown(f"**{paper.get('title')}**")
                with col2:
                    if st.button("Select", key=f"select_{paper.get('arxiv_id')}"):
                        st.session_state.selected_paper = paper
                        st.rerun()
                st.divider()
        else:
            st.warning("No papers available. Please upload or load some papers first.")

# Вкладка загрузки статьи
elif st.session_state.active_tab == "upload_paper":
    st.header("📤 Upload Research Paper")
    
    with st.form("upload_form"):
        uploaded_file = st.file_uploader("Choose a PDF or text file", type=["pdf", "txt"])
        paper_title = st.text_input("Paper Title", placeholder="Enter paper title")
        paper_authors = st.text_input("Authors (comma-separated)", placeholder="Author1, Author2")
        paper_categories = st.text_input("Categories (comma-separated)", placeholder="cs.AI, cs.CL")
        
        submit_button = st.form_submit_button("Upload Paper", type="primary", use_container_width=True)
    
    if submit_button:
        if not uploaded_file:
            st.error("Please select a file to upload")
        elif not paper_title:
            st.error("Please enter a paper title")
        else:
            with st.spinner("Uploading paper..."):
                response = upload_paper(
                    file=uploaded_file,
                    title=paper_title,
                    authors=paper_authors,
                    categories=paper_categories
                )
                
                if response.get("success", False):
                    st.success(f"Paper uploaded successfully: {response.get('message')}")
                    
                    # Обновляем статистику
                    system_stats = get_system_stats()
                else:
                    st.error(f"Failed to upload paper: {response.get('message')}")

# Вкладка просмотра статей
elif st.session_state.active_tab == "browse_papers":
    st.header("📚 Browse Research Papers")
    
    # Получаем список статей
    papers_data = list_papers(limit=50)
    papers = papers_data.get("papers", [])
    total_papers = papers_data.get("total", 0)
    
    # Отображаем информацию о количестве статей
    st.caption(f"Total papers in database: {total_papers}")
    
    # Показываем статьи
    if papers:
        # Добавляем поиск по статьям
        search_term = st.text_input("Filter papers by title or author", placeholder="Enter search term")
        
        # Фильтруем статьи по поисковому запросу
        if search_term:
            filtered_papers = [
                p for p in papers 
                if search_term.lower() in p.get('title', '').lower() or 
                any(search_term.lower() in author.lower() for author in p.get('authors', []))
            ]
        else:
            filtered_papers = papers
        
        st.caption(f"Showing {len(filtered_papers)} papers")
        
        # Отображаем статьи
        for paper in filtered_papers:
            display_paper(paper)
    else:
        st.info("No papers available in the database. Use the 'Settings' tab to load papers.")

# Вкладка настроек
elif st.session_state.active_tab == "settings":
    st.header("⚙️ Settings")
    
    # Отображаем информацию о системе
    st.subheader("System Information")
    
    system_online = system_stats.get("system_status") == "online"
    status_color = "green" if system_online else "red"
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**Status**: :{status_color}[{system_stats.get('system_status', 'Unknown')}]")
        st.markdown(f"**Papers in DB**: {system_stats.get('paper_count', 'N/A')}")
    with col2:
        st.markdown(f"**LLM Model**: {system_stats.get('llm_model', 'Unknown')}")
        st.markdown(f"**Embedding Model**: {system_stats.get('embedding_model', 'Unknown')}")
    
    # Загрузка данных из arXiv
    st.subheader("Load Data from arXiv")
    with st.form("load_data_form"):
        col1, col2 = st.columns(2)
        with col1:
            count = st.number_input("Number of papers", min_value=1, max_value=1000, value=100)
        with col2:
            categories = st.text_input("Categories (comma-separated)", placeholder="cs.AI,cs.CL,cs.LG", value="cs.AI,cs.CL,cs.LG")
        
        submit_button = st.form_submit_button("Load arXiv Data", type="primary", use_container_width=True)
        
    if submit_button:
        # Устанавливаем флаг загрузки данных
        st.session_state.loading_data = True
        st.session_state.loading_message = f"Loading {count} papers from arXiv categories: {categories}..."
        st.session_state.loading_progress = 0.1
        
        with st.spinner("Loading data..."):
            result = load_arxiv_data(count, categories)
            
            # Имитируем прогресс загрузки
            for i in range(1, 10):
                time.sleep(0.2)
                st.session_state.loading_progress = i / 10
                st.rerun()
            
            # Завершаем загрузку
            st.session_state.loading_data = False
            st.session_state.loading_progress = 1.0
            st.success(result)
            
            # Обновляем статистику
            system_stats = get_system_stats()

# Footer
st.divider()
st.caption("PaperAI - Powered by LangChain & Weaviate") 
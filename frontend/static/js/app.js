class ResearchApp {
    constructor() {
        this.searchInput = document.getElementById('searchInput');
        this.searchBtn = document.getElementById('searchBtn');
        this.pipelineSelect = document.getElementById('pipelineSelect');
        this.resultsDiv = document.getElementById('results');
        this.paperCountSpan = document.getElementById('paperCount');
        this.systemStatusSpan = document.getElementById('systemStatus');
        
        this.initEventListeners();
        this.checkSystemStatus();
        this.updatePaperCount();
    }
    
    initEventListeners() {
        this.searchBtn.addEventListener('click', () => this.performSearch());
        this.searchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.performSearch();
            }
        });
    }
    
    async performSearch() {
        const query = this.searchInput.value.trim();
        const pipeline = this.pipelineSelect.value;
        
        if (!query) {
            this.showError('Please enter a search query');
            return;
        }
        
        this.showLoading();
        
        try {
            const response = await fetch('/api/v1/search', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    query: query,
                    pipeline_type: pipeline,
                    limit: 5
                })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const results = await response.json();
            this.displayResults(results);
            
        } catch (error) {
            console.error('Search error:', error);
            this.showError('Search failed. Please try again.');
        }
    }
    
    showLoading() {
        this.resultsDiv.innerHTML = '<div class="loading">Searching...</div>';
    }
    
    showError(message) {
        this.resultsDiv.innerHTML = `<div class="error result-item">${message}</div>`;
    }
    
    displayResults(results) {
        if (!results.papers || results.papers.length === 0) {
            this.resultsDiv.innerHTML = '<div class="result-item">No papers found for your query.</div>';
            return;
        }
        
        const html = results.papers.map(paper => `
            <div class="result-item">
                <div class="result-title">${paper.title}</div>
                <div class="result-authors">Authors: ${paper.authors ? paper.authors.join(', ') : 'Unknown'}</div>
                <div class="result-abstract">${paper.abstract || 'No abstract available'}</div>
                <div class="result-meta">
                    <span>arXiv ID: ${paper.arxiv_id || 'N/A'}</span>
                    <span>Categories: ${paper.categories ? paper.categories.join(', ') : 'N/A'}</span>
                    ${paper._additional ? `<span>Similarity: ${(1 - paper._additional.distance).toFixed(3)}</span>` : ''}
                </div>
            </div>
        `).join('');
        
        this.resultsDiv.innerHTML = html;
    }
    
    async checkSystemStatus() {
        try {
            const response = await fetch('/health');
            if (response.ok) {
                this.systemStatusSpan.textContent = 'Online';
                this.systemStatusSpan.style.color = '#27ae60';
            } else {
                throw new Error('Health check failed');
            }
        } catch (error) {
            this.systemStatusSpan.textContent = 'Offline';
            this.systemStatusSpan.style.color = '#e74c3c';
        }
    }
    
    async updatePaperCount() {
        try {
            const response = await fetch('/api/v1/stats');
            if (response.ok) {
                const stats = await response.json();
                this.paperCountSpan.textContent = stats.paper_count || 0;
            } else {
                throw new Error('Stats fetch failed');
            }
        } catch (error) {
            this.paperCountSpan.textContent = 'Error';
        }
    }
}

document.addEventListener('DOMContentLoaded', () => {
    new ResearchApp();
});
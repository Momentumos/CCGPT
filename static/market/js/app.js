// Market Analysis Application
class MarketAnalysisApp {
    constructor() {
        this.apiKey = null;
        this.currentRootNode = null;
        this.markets = [];
        this.jobs = [];
        this.baseURL = window.location.origin;
        this.refreshInterval = null;
        
        this.init();
    }

    init() {
        // Check if already logged in
        const savedApiKey = localStorage.getItem('market_analysis_api_key');
        if (savedApiKey) {
            this.apiKey = savedApiKey;
            this.showMainScreen();
        }

        this.attachEventListeners();
    }

    attachEventListeners() {
        // Login form
        document.getElementById('login-form').addEventListener('submit', (e) => {
            e.preventDefault();
            this.handleLogin();
        });

        // Logout button
        document.getElementById('logout-btn').addEventListener('click', () => {
            this.handleLogout();
        });

        // New analysis buttons
        document.getElementById('new-analysis-btn').addEventListener('click', () => {
            this.showNewAnalysisModal();
        });
        
        document.getElementById('start-btn').addEventListener('click', () => {
            this.showNewAnalysisModal();
        });

        // Modal controls
        document.querySelectorAll('.modal-close, .modal-cancel').forEach(btn => {
            btn.addEventListener('click', () => {
                this.hideModal();
            });
        });

        // New analysis form
        document.getElementById('new-analysis-form').addEventListener('submit', (e) => {
            e.preventDefault();
            this.handleNewAnalysis();
        });

        // Refresh button
        document.getElementById('refresh-btn').addEventListener('click', () => {
            if (this.currentRootNode) {
                this.loadTreeData(this.currentRootNode.id);
            }
        });

        // Export button
        document.getElementById('export-btn').addEventListener('click', () => {
            this.exportData();
        });
    }

    async handleLogin() {
        const apiKeyInput = document.getElementById('api-key');
        const apiKey = apiKeyInput.value.trim();
        const errorDiv = document.getElementById('login-error');
        const submitBtn = document.querySelector('#login-form button');

        if (!apiKey) {
            this.showError(errorDiv, 'Please enter an API key');
            return;
        }

        submitBtn.disabled = true;
        submitBtn.textContent = 'Connecting...';
        errorDiv.style.display = 'none';

        try {
            // Test the API key
            const response = await fetch(`${this.baseURL}/api/market/nodes/roots/`, {
                headers: {
                    'X-API-Key': apiKey,
                }
            });

            if (response.ok) {
                this.apiKey = apiKey;
                localStorage.setItem('market_analysis_api_key', apiKey);
                this.showMainScreen();
            } else if (response.status === 401) {
                this.showError(errorDiv, 'Invalid API key. Please check and try again.');
            } else {
                this.showError(errorDiv, 'Connection failed. Please try again.');
            }
        } catch (error) {
            console.error('Login error:', error);
            this.showError(errorDiv, 'Connection error. Please check if the server is running.');
        } finally {
            submitBtn.disabled = false;
            submitBtn.textContent = 'Connect';
        }
    }

    handleLogout() {
        if (confirm('Are you sure you want to logout?')) {
            localStorage.removeItem('market_analysis_api_key');
            this.apiKey = null;
            this.currentRootNode = null;
            this.markets = [];
            
            if (this.refreshInterval) {
                clearInterval(this.refreshInterval);
            }
            
            this.showLoginScreen();
        }
    }

    showLoginScreen() {
        document.getElementById('login-screen').classList.add('active');
        document.getElementById('main-screen').classList.remove('active');
        document.getElementById('api-key').value = '';
    }

    async showMainScreen() {
        document.getElementById('login-screen').classList.remove('active');
        document.getElementById('main-screen').classList.add('active');
        
        await this.loadMarkets();
        
        // Start auto-refresh for running jobs
        this.startAutoRefresh();
    }

    showError(element, message) {
        element.textContent = message;
        element.style.display = 'block';
    }

    showNewAnalysisModal() {
        document.getElementById('new-analysis-modal').classList.add('active');
    }

    hideModal() {
        document.getElementById('new-analysis-modal').classList.remove('active');
    }

    async handleNewAnalysis() {
        const titlesInput = document.getElementById('market-titles');
        const maxDepthSelect = document.getElementById('max-depth');
        const submitBtn = document.querySelector('#new-analysis-form button[type="submit"]');

        const titles = titlesInput.value
            .split('\n')
            .map(t => t.trim())
            .filter(t => t.length > 0);

        if (titles.length === 0) {
            alert('Please enter at least one market name');
            return;
        }

        submitBtn.disabled = true;
        submitBtn.textContent = 'Starting Analysis...';

        try {
            const response = await fetch(`${this.baseURL}/api/market/analyze/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-API-Key': this.apiKey,
                },
                body: JSON.stringify({
                    market_titles: titles,
                    max_depth: parseInt(maxDepthSelect.value)
                }),
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const jobs = await response.json();
            
            this.hideModal();
            titlesInput.value = '';
            
            // Reload markets
            await this.loadMarkets();
            
            alert(`Analysis started for ${jobs.length} market(s)!`);

        } catch (error) {
            console.error('Start analysis error:', error);
            alert('Failed to start analysis. Please try again.');
        } finally {
            submitBtn.disabled = false;
            submitBtn.textContent = 'Start Analysis';
        }
    }

    async loadMarkets() {
        try {
            const response = await fetch(`${this.baseURL}/api/market/nodes/roots/`, {
                headers: {
                    'X-API-Key': this.apiKey,
                }
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            this.markets = await response.json();
            this.renderMarketsList();

        } catch (error) {
            console.error('Load markets error:', error);
        }
    }

    renderMarketsList() {
        const container = document.getElementById('markets-list');
        
        if (this.markets.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <p>No markets analyzed yet.</p>
                    <p>Click "New Analysis" to start.</p>
                </div>
            `;
            return;
        }

        container.innerHTML = this.markets.map(market => `
            <div class="market-item ${this.currentRootNode?.id === market.id ? 'active' : ''}" 
                 data-id="${market.id}">
                <div class="market-title">${market.title}</div>
                <div class="market-status status-${market.status}">${market.status}</div>
            </div>
        `).join('');

        // Add click handlers
        container.querySelectorAll('.market-item').forEach(item => {
            item.addEventListener('click', () => {
                const marketId = item.dataset.id;
                this.selectMarket(marketId);
            });
        });
    }

    async selectMarket(marketId) {
        const market = this.markets.find(m => m.id === marketId);
        if (!market) return;

        this.currentRootNode = market;
        this.renderMarketsList();
        
        // Show visualization view
        document.getElementById('welcome-view').classList.remove('active');
        document.getElementById('visualization-view').classList.add('active');
        
        // Load tree data
        await this.loadTreeData(marketId);
    }

    async loadTreeData(rootNodeId) {
        try {
            const response = await fetch(`${this.baseURL}/api/market/tree/${rootNodeId}/`, {
                headers: {
                    'X-API-Key': this.apiKey,
                }
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const treeData = await response.json();
            
            // Update UI
            document.getElementById('viz-title').textContent = treeData.name;
            document.getElementById('total-value').textContent = this.formatCurrency(treeData.value);
            document.getElementById('total-employment').textContent = this.formatNumber(treeData.employment);
            document.getElementById('analysis-status').textContent = treeData.status;
            
            // Count sub-markets
            const countSubmarkets = (node) => {
                let count = node.children.length;
                node.children.forEach(child => {
                    count += countSubmarkets(child);
                });
                return count;
            };
            document.getElementById('total-submarkets').textContent = countSubmarkets(treeData);
            
            // Render visualization
            if (window.MarketVisualization) {
                window.MarketVisualization.render(treeData);
            }

        } catch (error) {
            console.error('Load tree data error:', error);
        }
    }

    startAutoRefresh() {
        // Refresh every 5 seconds if there are running jobs
        this.refreshInterval = setInterval(async () => {
            if (this.markets.some(m => m.status === 'analyzing' || m.status === 'pending')) {
                await this.loadMarkets();
                
                if (this.currentRootNode) {
                    await this.loadTreeData(this.currentRootNode.id);
                }
            }
        }, 5000);
    }

    exportData() {
        if (!this.currentRootNode) return;

        // Export as JSON
        fetch(`${this.baseURL}/api/market/tree/${this.currentRootNode.id}/`, {
            headers: {
                'X-API-Key': this.apiKey,
            }
        })
        .then(response => response.json())
        .then(data => {
            const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `${this.currentRootNode.title.replace(/\s+/g, '_')}_analysis.json`;
            a.click();
            URL.revokeObjectURL(url);
        })
        .catch(error => {
            console.error('Export error:', error);
            alert('Failed to export data');
        });
    }

    formatCurrency(value) {
        if (!value) return '$0';
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'USD',
            minimumFractionDigits: 0,
            maximumFractionDigits: 0,
        }).format(value);
    }

    formatNumber(value) {
        if (!value) return '0';
        return new Intl.NumberFormat('en-US').format(value);
    }
}

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.app = new MarketAnalysisApp();
});

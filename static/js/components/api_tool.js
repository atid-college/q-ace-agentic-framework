document.addEventListener('alpine:init', () => {
    Alpine.data('apiTool', () => ({
        // Server Selection
        selectedServer: 'jsonplaceholder',
        customServerUrl: '',
        activeServer: '',

        // Prompt & State
        prompt: '',
        loading: false,
        error: '',
        successMsg: '',
        result: null,
        llmIntent: null,
        aiAnalysis: null,
        isVerified: null,
        activeTab: 'agent', // 'agent' or 'results'

        // History & Stats
        promptHistory: [],
        historyStats: null,
        selectedHistoryItem: null,

        // Preset servers
        presetServers: [
            { id: 'jsonplaceholder', label: 'JSONPlaceholder', url: 'https://jsonplaceholder.typicode.com' },
            { id: 'local', label: 'Local Dev       (http://localhost:3000)', url: 'http://localhost:3000' },
            { id: 'staging', label: 'Staging         (https://staging.example.com)', url: 'https://staging.example.com' },
            { id: 'prod', label: 'Production      (https://api.example.com)', url: 'https://api.example.com' },
            { id: 'custom', label: '-- Custom URL --', url: '' },
        ],

        init() {
            this.loadHistory();
            this.loadStats();
        },

        // ── Resolved URL ───────────────────────────────────────────────
        get resolvedServerUrl() {
            if (this.selectedServer === 'custom') return this.customServerUrl.trim();
            const preset = this.presetServers.find(s => s.id === this.selectedServer);
            return preset ? preset.url : '';
        },

        // ── Backend History Helpers ─────────────────────────────────────
        async loadHistory() {
            try {
                const response = await Auth.fetch('/api/api-agent/history');
                if (response.ok) {
                    this.promptHistory = await response.json();
                }
            } catch (e) {
                console.error('Failed to load API history from DB:', e);
            }
        },

        async loadStats() {
            try {
                const response = await Auth.fetch('/api/api-agent/stats');
                if (response.ok) {
                    this.historyStats = await response.json();
                    this.$nextTick(() => this.renderChart());
                }
            } catch (e) {
                console.error('Failed to load API stats:', e);
            }
        },

        renderChart() {
            const ctx = document.getElementById('apiHistoryChart');
            if (!ctx || !this.historyStats) return;

            if (window.apiChartInstance) window.apiChartInstance.destroy();

            window.apiChartInstance = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: this.historyStats.daily.map(d => d.date.split('-').slice(1).join('/')),
                    datasets: [{
                        label: 'Runs',
                        data: this.historyStats.daily.map(d => d.count),
                        borderColor: '#10b981',
                        backgroundColor: 'rgba(16, 185, 129, 0.1)',
                        borderWidth: 3,
                        fill: true,
                        tension: 0.4,
                        pointRadius: 4,
                        pointBackgroundColor: '#fff',
                        pointBorderColor: '#10b981'
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: {
                        y: { beginAtZero: true, grid: { display: false }, ticks: { stepSize: 1 } },
                        x: { grid: { display: false } }
                    }
                }
            });
        },

        async addToHistory(prompt, result, llmIntent, aiAnalysis, isVerified, serverUrl) {
            try {
                await Auth.fetch('/api/api-agent/history', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        prompt: prompt.trim(),
                        result: result,
                        llmIntent: llmIntent,
                        aiAnalysis: aiAnalysis,
                        isVerified: isVerified,
                        serverUrl: serverUrl,
                        selectedServer: this.selectedServer
                    })
                });
                await this.loadHistory();
                await this.loadStats();
            } catch (e) {
                console.error('Failed to save API history to DB:', e);
            }
        },

        async removeHistoryItem(id) {
            if (!confirm('Delete this history item?')) return;
            try {
                const res = await Auth.fetch(`/api/api-agent/history/${id}`, {
                    method: 'DELETE'
                });
                if (res.ok) {
                    await this.loadHistory();
                    await this.loadStats();
                }
            } catch (e) {}
        },

        async clearHistory() {
            if (!confirm('Clear all API execution history?')) return;
            try {
                const res = await Auth.fetch('/api/api-agent/history/clear', {
                    method: 'DELETE'
                });
                if (res.ok) {
                    this.promptHistory = [];
                    await this.loadStats();
                }
            } catch (e) {}
        },

        selectHistoryItem(item) {
            this.selectedHistoryItem = item;
            this.$nextTick(() => { if (window.lucide) window.lucide.createIcons(); });
        },

        // ── Execute Action ──────────────────────────────────────────────
        async executeAction() {
            if (!this.prompt.trim()) {
                this.error = 'Please provide an instruction.';
                return;
            }

            const serverUrl = this.resolvedServerUrl;

            this.loading = true;
            this.error = '';
            this.successMsg = '';
            this.result = null;
            this.llmIntent = null;
            this.aiAnalysis = null;
            this.isVerified = null;

            try {
                const response = await Auth.fetch('/api/tool/action', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        tool_id: 'api',
                        action: 'llm_execute',
                        data: {
                            prompt: this.prompt,
                            server_url: serverUrl
                        }
                    })
                });

                const data = await response.json();

                let intent = data.llm_intent || null;
                let analysis = data.ai_analysis || null;
                let verified = data.is_verified !== undefined ? data.is_verified : null;

                if (data.status === 'error') {
                    this.error = data.message;
                    // Even on error, we might want to save to history if there was an attempt
                    this.addToHistory(this.prompt, data, intent, analysis, false, serverUrl);
                } else {
                    if (data.message) this.successMsg = data.message;
                    this.result = data.data !== undefined ? data.data : data;
                    this.llmIntent = intent;
                    this.aiAnalysis = analysis;
                    this.isVerified = verified;
                    this.activeServer = serverUrl;
                    
                    this.addToHistory(
                        this.prompt, this.result,
                        this.llmIntent, this.aiAnalysis, this.isVerified,
                        serverUrl
                    );
                }
            } catch (err) {
                this.error = `Connection failed: ${err.message}`;
            } finally {
                this.loading = false;
                this.$nextTick(() => { if (window.lucide) window.lucide.createIcons(); });
            }
        }
    }));
});

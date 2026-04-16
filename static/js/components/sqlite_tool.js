document.addEventListener('alpine:init', () => {
    Alpine.data('sqliteTool', () => ({
        selectedSample: 'custom',
        customDbPath: '',
        prompt: '',
        loading: false,
        error: '',
        successMsg: '',
        result: null,
        activeDb: '',
        promptHistory: [],
        historyStats: null,
        selectedHistoryItem: null,
        aiAnalysis: null,
        isVerified: null,
        activeTab: 'agent', // 'agent' or 'results'

        // Schema Modal
        showSchemaModal: false,
        schemaLoading: false,
        schemaData: [],

        init() {
            this.loadHistory();
            this.loadStats();
        },

        async loadStats() {
            try {
                const response = await Auth.fetch('/api/sqlite/stats');
                if (response.ok) {
                    this.historyStats = await response.json();
                    this.$nextTick(() => this.renderChart());
                }
            } catch (e) {
                console.error('Failed to load sqlite stats:', e);
            }
        },

        renderChart() {
            const ctx = document.getElementById('sqliteHistoryChart');
            if (!ctx || !this.historyStats) return;

            if (window.sqliteChartInstance) window.sqliteChartInstance.destroy();

            window.sqliteChartInstance = new Chart(ctx, {
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

        async loadHistory() {
            try {
                const response = await Auth.fetch('/api/sqlite/history');
                if (response.ok) {
                    this.promptHistory = await response.json();
                }
            } catch (e) {
                console.error('Failed to load sqlite history from DB:', e);
            }
        },

        async addToHistory(prompt, result, activeDb) {
            try {
                await Auth.fetch('/api/sqlite/history', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        prompt: prompt.trim(),
                        result: result,
                        activeDb: activeDb,
                        sampleDb: this.selectedSample,
                        aiAnalysis: this.aiAnalysis,
                        isVerified: this.isVerified
                    })
                });
                await this.loadHistory(); // Refresh from DB
                await this.loadStats();   // Update stats
            } catch (e) {
                console.error('Failed to save sqlite history to DB:', e);
            }
        },

        async removeHistoryItem(id) {
            if (!confirm('Delete this history item?')) return;
            try {
                const res = await Auth.fetch(`/api/sqlite/history/${id}`, {
                    method: 'DELETE'
                });
                if (res.ok) {
                    await this.loadHistory();
                    await this.loadStats();
                }
            } catch (e) {}
        },

        async clearHistory() {
            if (!confirm('Clear all database execution history?')) return;
            try {
                const res = await Auth.fetch('/api/sqlite/history/clear', {
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
            this.prompt = item.prompt;
            this.result = JSON.parse(JSON.stringify(item.result)); // Restore results
            this.activeDb = item.activeDb;
            this.aiAnalysis = item.aiAnalysis || null;
            this.isVerified = item.isVerified !== undefined ? item.isVerified : null;
            this.error = '';
            this.successMsg = '';
            this.$nextTick(() => { if (window.lucide) window.lucide.createIcons(); });
        },

        async execute() {
            const dbPath = this.selectedSample === 'custom' ? this.customDbPath : '';
            if (!this.prompt || (this.selectedSample === 'custom' && !dbPath)) {
                this.error = 'Please provide the database path and your query.';
                return;
            }

            this.loading = true;
            this.error = '';
            this.successMsg = '';
            this.result = null;
            this.aiAnalysis = null;
            this.isVerified = null;

            try {
                const response = await Auth.fetch('/api/tool/action', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        tool_id: 'sqlite',
                        action: 'text_to_sql',
                        data: {
                            sample_db: this.selectedSample,
                            db_path: dbPath,
                            prompt: this.prompt
                        }
                    })
                });

                const data = await response.json();
                if (data.status === 'error' || data.status === 'warning') {
                    this.error = data.message;
                    if (data.query) this.result = { query: data.query, data: [] };
                } else {
                    this.result = data;
                    this.activeDb = data.active_db;
                    this.aiAnalysis = data.ai_analysis;
                    this.isVerified = data.is_verified;
                    // Add to history on success with FULL data
                    this.addToHistory(this.prompt, data, data.active_db);
                }
            } catch (err) {
                this.error = `Connection failed: ${err.message}`;
            } finally {
                this.loading = false;
                this.$nextTick(() => { if (window.lucide) window.lucide.createIcons(); });
            }
        },

        async resetDb() {
            if (this.selectedSample === 'custom') return;

            this.loading = true;
            this.error = '';
            this.successMsg = '';

            try {
                const response = await Auth.fetch('/api/tool/action', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        tool_id: 'sqlite',
                        action: 'reset_db',
                        data: { sample_db: this.selectedSample }
                    })
                });

                const data = await response.json();
                if (data.status === 'success') {
                    this.successMsg = data.message;
                } else {
                    this.error = data.message;
                }
            } catch (err) {
                this.error = `Reset failed: ${err.message}`;
            } finally {
                this.loading = false;
                this.$nextTick(() => { if (window.lucide) window.lucide.createIcons(); });
            }
        },

        copySql() {
            if (this.result?.query) {
                navigator.clipboard.writeText(this.result.query);
                this.successMsg = "SQL copied to clipboard!";
                setTimeout(() => this.successMsg = '', 3000);
            }
        },

        get columns() {
            if (this.result?.data?.length > 0) {
                return Object.keys(this.result.data[0]);
            }
            return [];
        },

        get filteredHistory() {
            return this.promptHistory.filter(h => {
                if (this.selectedSample === 'custom') {
                    // Match by custom path
                    return h.sampleDb === 'custom' && h.activeDb === this.customDbPath;
                } else {
                    // Match by sample name
                    return h.sampleDb === this.selectedSample;
                }
            });
        }
        ,
        async showSchema() {
            this.showSchemaModal = true;
            this.schemaLoading = true;
            this.schemaData = [];

            const dbPath = this.selectedSample === 'custom' ? this.customDbPath : '';

            try {
                const response = await Auth.fetch('/api/tool/action', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        tool_id: 'sqlite',
                        action: 'get_schema',
                        data: {
                            sample_db: this.selectedSample,
                            db_path: dbPath
                        }
                    })
                });
                const data = await response.json();
                if (data.status === 'success') {
                    this.schemaData = data.schema;
                } else {
                    this.error = data.message;
                    this.showSchemaModal = false;
                }
            } catch (err) {
                this.error = `Failed to load schema: ${err.message}`;
                this.showSchemaModal = false;
            } finally {
                this.schemaLoading = false;
                this.$nextTick(() => { if (window.lucide) window.lucide.createIcons(); });
            }
        },

    }));
});

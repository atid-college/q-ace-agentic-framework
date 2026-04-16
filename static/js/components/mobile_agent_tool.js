function mobileAgentTool() {
    return {
        activeTab: 'task',
        
        get task() { return window.Alpine.store('mobileAgent').task },
        set task(v) { window.Alpine.store('mobileAgent').setTask(v) },
        get logs() { return window.Alpine.store('mobileAgent').logs },
        set logs(v) { window.Alpine.store('mobileAgent').setLogs(v) },
        get status() { return window.Alpine.store('mobileAgent').status },
        set status(v) { window.Alpine.store('mobileAgent').setStatus(v) },
        get finalResult() { return window.Alpine.store('mobileAgent').finalResult },
        set finalResult(v) { window.Alpine.store('mobileAgent').setFinalResult(v) },
        get errorMessage() { return window.Alpine.store('mobileAgent').errorMsg },
        set errorMessage(v) { window.Alpine.store('mobileAgent').setError(v) },
        
        showErrorModal: false,
        
        promptHistory: [],
        selectedHistoryItem: null,
        historyStats: { total: 0, success: 0, failed: 0, rate: 0, daily: [] },
        chartInstance: null,

        // Suite
        suiteFile: null,
        suiteName: '',
        suiteTasks: [],
        suiteTaskNames: [],

        appiumConfig: {
            serverUrl: 'http://localhost:4723',
            platformName: 'Android',
            udid: '',
            appPackage: '',
            appActivity: ''
        },

        savingConfig: false,
        successMsg: '',
        _abortController: null,

        async init() {
            // Restore saved settings from DB
            try {
                const response = await Auth.fetch('/api/mobile-agent/config');
                if (response.ok) {
                    const data = await response.json();
                    if (data.appium_config) {
                        this.appiumConfig = { ...this.appiumConfig, ...data.appium_config };
                    }
                }
            } catch (e) {
                console.error('[MobileAgent] Failed to load config from DB:', e);
            }
            
            await this.loadHistoryFromDB();
            await this.loadStats();
        },

        async saveConfig() {
            this.savingConfig = true;
            try {
                const response = await Auth.fetch('/api/mobile-agent/config', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ appium_config: this.appiumConfig })
                });
                if (response.ok) {
                    this.successMsg = 'Appium configuration saved successfully!';
                    setTimeout(() => { this.successMsg = ''; }, 3000);
                    console.log('[MobileAgent] Config saved successfully');
                }
            } catch (e) {
                console.error('[MobileAgent] Failed to save config to DB:', e);
            } finally {
                this.savingConfig = false;
            }
        },

        async loadStats() {
            try {
                const response = await Auth.fetch('/api/mobile-agent/stats');
                if (response.ok) {
                    this.historyStats = await response.json();
                    this.$nextTick(() => this.initChart());
                }
            } catch (e) {}
        },

        initChart() {
            // Use 350ms timeout so Alpine's x-show transition finishes before
            // Chart.js touches the canvas (prevents 'null save' error)
            setTimeout(() => {
                if (this.activeTab !== 'results') return;
                const canvas = document.getElementById('mobileHistoryChart');
                if (!canvas || !canvas.isConnected) return;
                if (!this.historyStats || !this.historyStats.daily || !this.historyStats.daily.length) return;
                // Ensure the canvas and all its ancestors are visible
                if (canvas.offsetWidth === 0 || canvas.offsetHeight === 0) return;
                if (!canvas.offsetParent && canvas.style.display === 'none') return;

                const ctx = canvas.getContext('2d');
                if (!ctx) return;

                if (this.chartInstance) {
                    this.chartInstance.destroy();
                    this.chartInstance = null;
                }
                try {
                    this.chartInstance = new Chart(canvas, {
                        type: 'line',
                        data: {
                            labels: this.historyStats.daily.map(d => d.day),
                            datasets: [{
                                label: 'Runs per Day',
                                data: this.historyStats.daily.map(d => d.count),
                                borderColor: '#10b981',
                                backgroundColor: 'rgba(16,185,129,0.1)',
                                fill: true, tension: 0.4, borderWidth: 3,
                                pointBackgroundColor: '#fff',
                                pointBorderColor: '#10b981',
                                pointBorderWidth: 2, pointRadius: 4
                            }]
                        },
                        options: {
                            responsive: true, maintainAspectRatio: false,
                            animation: { duration: 600 },
                            plugins: { legend: { display: false } },
                            scales: {
                                y: { beginAtZero: true, grid: { display: false }, ticks: { font: { size: 10, weight: '600' }, color: '#94a3b8' } },
                                x: { grid: { display: false }, ticks: { font: { size: 10, weight: '600' }, color: '#94a3b8' } }
                            }
                        }
                    });
                } catch (e) { console.error('Chart.js init failed:', e); }
            }, 350);
        },

        async loadHistoryFromDB() {
            try {
                const response = await Auth.fetch('/api/mobile-agent/history');
                if (response.ok) {
                    this.promptHistory = await response.json();
                }
            } catch (e) {}
        },

        async saveHistoryToDB(prompt, logs, result, history_json = {}) {
            try {
                await Auth.fetch('/api/mobile-agent/history', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ prompt, logs, result, history_json })
                });
                await this.loadHistoryFromDB();
            } catch (e) {}
        },

        async clearHistory() {
            if (!confirm('Are you sure you want to clear all mobile execution history?')) return;
            try {
                const res = await Auth.fetch('/api/mobile-agent/history/clear', {
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
            this.$nextTick(() => {
                if (window.lucide) lucide.createIcons();
            });
        },

        async switchTab(tab) {
            this.activeTab = tab;
            if (tab === 'results') {
                await this.loadStats();
                this.$nextTick(() => {
                    this.initChart();
                    if (window.lucide) lucide.createIcons();
                });
            }
        },

        async startAgent() {
            if (!this.task.trim()) return;
            this.status = 'running';
            this.logs = [];
            this.finalResult = '';
            
            this._abortController = new AbortController();
            const token = typeof Auth !== 'undefined' ? Auth.getToken() : '';
            
            try {
                const response = await Auth.fetch('/api/mobile-agent/run', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        task: this.task,
                        appium_config: this.appiumConfig
                    }),
                    signal: this._abortController.signal
                });

                if (!response.ok) {
                    const text = await response.text();
                    this.errorMessage = text || "Failed to start mobile agent. Is the server running?";
                    this.showErrorModal = true;
                    this.status = 'idle';
                    return;
                }

                const reader = response.body.getReader();
                const decoder = new TextDecoder();
                let buffer = '';

                while (true) {
                    const { done, value } = await reader.read();
                    if (done) break;

                    buffer += decoder.decode(value, { stream: true });
                    const parts = buffer.split('\n\n');
                    buffer = parts.pop();

                    for (const part of parts) {
                        const line = part.trim();
                        if (!line.startsWith('data: ')) continue;
                        const jsonStr = line.slice(6).trim();
                        if (!jsonStr) continue;
                        
                        try {
                            const data = JSON.parse(jsonStr);
                            
                            if (data.type === 'step') {
                                this.logs.push(data);
                            } else if (data.type === 'error') {
                                this.logs.push(data);
                                this.errorMessage = data.text;
                                this.showErrorModal = true;
                                this.status = 'idle';
                                await this.saveHistoryToDB(this.task, this.logs, "Failed: " + data.text);
                            } else if (data.type === 'done') {
                                this.logs.push(data);
                                this.finalResult = data.result || 'Task completed successfully.';
                                this.status = 'idle';
                                await this.saveHistoryToDB(this.task, this.logs, this.finalResult);
                            }
                            this.scrollToBottom();
                        } catch (err) {}
                    }
                }
                
                if (buffer.trim().startsWith('data: ')) {
                    try {
                        const data = JSON.parse(buffer.trim().slice(6).trim());
                        if (data.type === 'done') {
                            this.finalResult = data.result || 'Task completed successfully.';
                            this.status = 'idle';
                            await this.saveHistoryToDB(this.task, this.logs, this.finalResult);
                        }
                    } catch (_) {}
                }
                
            } catch (err) {
                if (err.name === 'AbortError') {
                    // Aborted gracefully
                } else {
                    this.logs.push({ type: 'error', text: err.message });
                    this.errorMessage = "Failed to initiate request: " + err.message;
                    this.showErrorModal = true;
                    this.status = 'idle';
                    await this.saveHistoryToDB(this.task, this.logs, "Exception: " + err.message);
                }
            }
        },

        async stopAgent() {
            if (this.status !== 'running') return;
            
            if (this._abortController) {
                this._abortController.abort();
                this._abortController = null;
            }
            
            this.logs.push({ type: 'error', text: 'Task cancelled by user.' });
            this.status = 'idle';
            this.finalResult = 'Cancelled.';
            await this.saveHistoryToDB(this.task, this.logs, 'Task cancelled by user.');
            
            try {
                await Auth.fetch('/api/mobile-agent/stop', {
                    method: 'POST'
                });
            } catch (e) {}
        },

        clearLogs() {
            this.logs = [];
            this.finalResult = '';
        },

        loadSuiteFile(event) {
            const file = event.target.files[0];
            if (!file) return;
            this.suiteName = file.name;
            const reader = new FileReader();
            reader.onload = (e) => {
                const content = e.target.result.trim();

                // --- 1. Try YAML list: - name: "..." \n  prompt: '...' ---
                // Split on entries starting with '- name:'
                const yamlItems = content.split(/^(?=- name:)/m).map(s => s.trim()).filter(Boolean);
                if (yamlItems.length > 0 && yamlItems[0].startsWith('- name:')) {
                    this.suiteTaskNames = [];
                    this.suiteTasks = [];
                    for (const item of yamlItems) {
                        const nameMatch = item.match(/^- name:\s*["']?(.+?)["']?\s*$/m);
                        const promptMatch = item.match(/^\s*prompt:\s*['"]([\s\S]*?)['"]\s*$/m);
                        if (nameMatch && promptMatch) {
                            this.suiteTaskNames.push(nameMatch[1].trim());
                            // Collapse internal whitespace from block-style YAML formatting
                            this.suiteTasks.push(promptMatch[1].replace(/[ \t]+/g, ' ').trim());
                        }
                    }
                    if (this.suiteTasks.length > 0) {
                        this.suiteFile = file;
                        if (this.suiteTasks.length > 0) this.task = this.suiteTasks[0];
                        this.$nextTick(() => { if (window.lucide) lucide.createIcons(); });
                        return;
                    }
                }

                // --- 2. Try JSON ---
                try {
                    const parsed = JSON.parse(content);
                    if (Array.isArray(parsed)) {
                        this.suiteTaskNames = parsed.map(t => (typeof t === 'string' ? '' : (t.name || '')));
                        this.suiteTasks = parsed.map(t => (typeof t === 'string' ? t : (t.prompt || t.task || JSON.stringify(t)))).filter(Boolean);
                    } else if (parsed.tasks && Array.isArray(parsed.tasks)) {
                        this.suiteTaskNames = parsed.tasks.map(t => (typeof t === 'string' ? '' : (t.name || '')));
                        this.suiteTasks = parsed.tasks.map(t => (typeof t === 'string' ? t : (t.prompt || t.task || ''))).filter(Boolean);
                        if (parsed.name) this.suiteName = parsed.name;
                    } else {
                        this.suiteTasks = [];
                        this.suiteTaskNames = [];
                    }
                } catch (_) {
                    // --- 3. Plain text: one task per non-empty line (skip # comments) ---
                    const lines = content.split('\n').map(l => l.trim()).filter(l => l && !l.startsWith('#'));
                    this.suiteTasks = lines;
                    this.suiteTaskNames = lines.map(() => '');
                }
                this.suiteFile = file;
                if (this.suiteTasks.length > 0) this.task = this.suiteTasks[0];
                this.$nextTick(() => { if (window.lucide) lucide.createIcons(); });
            };
            reader.readAsText(file);
            // Reset input so same file can be re-loaded
            event.target.value = '';
        },

        clearSuite() {
            this.suiteFile = null;
            this.suiteName = '';
            this.suiteTasks = [];
            this.suiteTaskNames = [];
        },

        async runSuiteSequential() {
            if (this.status === 'running' || !this.suiteTasks.length) return;
            this.logs = [];
            this.finalResult = '';
            const tasks = [...this.suiteTasks];
            for (let i = 0; i < tasks.length; i++) {
                this.task = tasks[i];
                this.logs.push({ type: 'step', text: `▶ [Suite ${i+1}/${tasks.length}] Starting task: ${tasks[i]}` });
                // Wait for the current run to complete by calling startAgent and waiting for status to return to idle
                await this.startAgent();
                // Let Alpine settle and wait until status goes back to idle  
                await new Promise(resolve => {
                    const check = setInterval(() => {
                        if (this.status !== 'running') {
                            clearInterval(check);
                            resolve();
                        }
                    }, 500);
                });
                this.logs.push({ type: 'step', text: `✓ [Suite ${i+1}/${tasks.length}] Task complete.` });
                if (i < tasks.length - 1) await new Promise(r => setTimeout(r, 800));
            }
            this.logs.push({ type: 'done', text: `✅ Suite complete — ${tasks.length} task(s) executed.` });
            this.scrollToBottom();
        },

        scrollToBottom() {
            this.$nextTick(() => {
                const consoleDiv = document.getElementById('mobile-agent-console');
                if (consoleDiv) {
                    consoleDiv.scrollTop = consoleDiv.scrollHeight;
                }
            });
        }
    }
}

function browserAgentTool() {
    return {
        activeTab: 'task',
        task: '',
        status: 'idle',
        resultStatus: 'idle',
        logs: [],
        finalResult: '',
        headless: false,
        promptHistory: [],
        selectedHistoryId: null,
        isQuotaError: false,
        showResultDetail: true,
        toast: { show: false, message: '', type: 'success' },
        metrics: null,
        _abortController: null,

        // Docs State
        docs: [],
        loadingDocs: false,
        selectedDoc: null,
        helpModal: { show: false, title: '', content: '' },
        helpMap: {},

        // Configuration State
        configTab: 'agent',
        agentConfig: {
            use_vision: 'auto',
            max_actions_per_step: 4,
            max_failures: 3,
            use_thinking: true,
            flash_mode: false,
            llm_timeout: 90,
            generate_gif: false,
            // Performance & Limits
            max_history_items: 20,
            step_timeout: 120,
            directly_open_url: true,
            // Timeouts
            timeouts: {
                navigate: 15.0,
                click: 15.0,
                type: 60.0,
                screenshot: 15.0
            }
        },
        browserConfig: {
            headless: false,
            window_width: 1280,
            window_height: 1100,
            viewport_width: 1280,
            viewport_height: 1100,
            keep_alive: false,
            enable_default_extensions: true,
            user_data_dir: '',
            record_video_dir: '',
            // Domains
            allowed_domains: '',
            prohibited_domains: '',
            // Recording & Debugging
            record_video_width: 1280,
            record_video_height: 720,
            record_video_framerate: 30,
            record_har_path: '',
            traces_dir: '',
            record_har_content: 'embed',
            record_har_mode: 'full'
        },

        // Suite / Batch Processing
        suiteFile: null,
        suiteName: '',
        suiteTasks: [],
        suiteTaskNames: [],

        // Modal State
        showConfirmModal: false,
        confirmTitle: '',
        confirmMessage: '',
        confirmAction: null,

        async init() {
            this.loadHistory();
            await this.loadConfig();
            this.fetchDocs(); // Pre-load docs for help tooltips
            this.$nextTick(() => {
                if (window.lucide) lucide.createIcons();
                this.renderStatsChart();
            });
        },

        async loadConfig() {
            try {
                const response = await Auth.fetch('/api/browser-agent/config');
                if (response.ok) {
                    const data = await response.json();
                    // Handle both snake_case (legacy/internal) and camelCase (newly saved)
                    const agent_cfg = data.agent_config || data.agentConfig;
                    const browser_cfg = data.browser_config || data.browserConfig;

                    if (agent_cfg) {
                        // Ensure nested objects like timeouts don't get wiped out by a shallow merge
                        this.agentConfig = { 
                            ...this.agentConfig, 
                            ...agent_cfg,
                            timeouts: { 
                                ...this.agentConfig.timeouts, 
                                ...(agent_cfg.timeouts || {}) 
                            }
                        };
                    }
                    if (browser_cfg) {
                        this.browserConfig = { ...this.browserConfig, ...browser_cfg };
                        this.headless = this.browserConfig.headless;
                    }
                }
            } catch (e) { console.error('[BrowserAgent] Failed to load config:', e); }
        },

        async saveConfig() {
            try {
                // Keep headless in sync
                this.browserConfig.headless = this.headless;
                
                const res = await Auth.fetch('/api/browser-agent/config', {
                    method: 'POST',
                    headers: { 
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        agent_config: this.agentConfig, // Using snake_case for consistency with backend GET
                        browser_config: this.browserConfig
                    })
                });
                if (res.ok) {
                    this.showToast('Settings saved successfully', 'success');
                } else {
                    this.showToast('Failed to save settings', 'error');
                }
            } catch (e) { 
                console.error('[BrowserAgent] Failed to save config:', e); 
                this.showToast('Error saving settings', 'error');
            }
        },

        showToast(message, type = 'success') {
            this.toast.message = message;
            this.toast.type = type;
            this.toast.show = true;
            this.$nextTick(() => { if (window.lucide) lucide.createIcons(); });
            setTimeout(() => { this.toast.show = false; }, 3000);
        },

        copyConsoleOutput() {
            const text = this.logs.map(l => l.text).join('\n');
            navigator.clipboard.writeText(text).then(() => {
                this.showToast('Console output copied to clipboard', 'success');
            }).catch(err => {
                console.error('Failed to copy text: ', err);
                this.showToast('Failed to copy to clipboard', 'error');
            });
        },

        async loadHistory() {
            try {
                const response = await Auth.fetch('/api/browser-agent/history');
                if (response.ok) {
                    this.promptHistory = await response.json();
                } else {
                    this.promptHistory = [];
                }
            } catch(e) { 
                console.error('[BrowserAgent] Failed to load history:', e);
                this.promptHistory = []; 
            }
        },

        async saveHistory(prompt, logs, result, status, metrics) {
            try {
                await Auth.fetch('/api/browser-agent/history', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ prompt, logs, result, status, metrics })
                });
            } catch (e) {
                console.error('[BrowserAgent] Failed to save history to DB:', e);
            }
        },

        async addToHistory(prompt, logs, result, status = 'success', metrics = null) {
            await this.saveHistory(prompt, logs, result, status, metrics);
            await this.loadHistory(); // Refresh from DB
            this.renderStatsChart();
        },

        removeHistoryItem(id) {
            this.triggerConfirm(
                'Delete Record',
                'Are you sure you want to delete this execution record? This action cannot be undone.',
                async () => {
                    try {
                        const res = await Auth.fetch(`/api/browser-agent/history/${id}`, {
                            method: 'DELETE'
                        });
                        if (res.ok) {
                            await this.loadHistory();
                            if (this.selectedHistoryId === id) this.selectedHistoryId = null;
                            this.renderStatsChart();
                            this.showToast('Record deleted', 'success');
                        }
                    } catch (e) {
                        this.showToast('Failed to delete record', 'error');
                    }
                }
            );
        },

        clearHistory() {
            this.triggerConfirm(
                'Clear History',
                'Are you sure you want to clear all execution history? This will permanently delete all records.',
                async () => {
                    try {
                        const res = await Auth.fetch('/api/browser-agent/history/clear', {
                            method: 'DELETE'
                        });
                        if (res.ok) {
                            this.promptHistory = [];
                            this.selectedHistoryId = null;
                            this.renderStatsChart();
                            this.showToast('History cleared', 'success');
                        }
                    } catch (e) {
                        this.showToast('Failed to clear history', 'error');
                    }
                }
            );
        },

        triggerConfirm(title, message, action) {
            this.confirmTitle = title;
            this.confirmMessage = message;
            this.confirmAction = action;
            this.showConfirmModal = true;
        },

        executeConfirm() {
            if (this.confirmAction) this.confirmAction();
            this.showConfirmModal = false;
            this.confirmAction = null;
        },

        selectHistoryItem(item) {
            this.selectedHistoryId = item.id;
            this.task = item.prompt;
            this.logs = [...item.logs];
            this.finalResult = item.result;
            this.status = 'idle';
            this.metrics = item.metrics || null;
            this.isQuotaError = item.status === 'failed' && (item.result.includes('429') || item.result.toLowerCase().includes('quota exceeded'));
            this.$nextTick(() => {
                this.scrollToBottom();
                if (window.lucide) lucide.createIcons();
            });
        },

        switchTab(tab) {
            this.activeTab = tab;
            this.$nextTick(() => {
                if (window.lucide) lucide.createIcons();
            });
        },

        clearLogs() {
            this.logs = [];
            this.finalResult = '';
            this.selectedHistoryId = null;
            this.isQuotaError = false;
            this.showResultDetail = true;
            this.metrics = null;
        },

        async startAgent() {
            if (!this.task.trim()) return;
            
            // Save current config before running
            await this.saveConfig();

            const taskPrompt = this.task;
            this.status = 'running';
            this.resultStatus = 'idle';
            this.isQuotaError = false;
            this.finalResult = '';
            this.showResultDetail = true;
            this.metrics = null;
            this._abortController = new AbortController();
            
            this.logs.push({ type: 'step', text: `🚀 Initializing Browser Agent for task: "${taskPrompt}"` });
            this.$nextTick(() => { if (window.lucide) lucide.createIcons(); });

            try {
                const response = await Auth.fetch('/api/browser-agent/run', {
                    method: 'POST',
                    headers: { 
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        task: taskPrompt,
                        agent_config: this.agentConfig,
                        browser_config: this.browserConfig
                    }),
                    signal: this._abortController.signal
                });

                if (!response.ok) {
                    throw new Error(`Server returned ${response.status}: ${await response.text()}`);
                }

                const reader = response.body.getReader();
                const decoder = new TextDecoder();
                let buffer = '';

                while (true) {
                    const { value, done } = await reader.read();
                    if (done) break;

                    buffer += decoder.decode(value, { stream: true });
                    const lines = buffer.split('\n\n');
                    buffer = lines.pop();

                    for (const line of lines) {
                        if (line.startsWith('data: ')) {
                            try {
                                const data = JSON.parse(line.substring(6));
                                if (data.type === 'step') {
                                    this.logs.push({ type: 'step', text: data.text });
                                } else if (data.type === 'done' || data.type === 'error') {
                                    this.resultStatus = data.status || 'success';
                                    if (data.type === 'error') {
                                        this.resultStatus = 'failed';
                                        this.isQuotaError = true;
                                    }
                                    this.finalResult = data.text;
                                    this.metrics = data.metrics || null;
                                    
                                    // Robust Fallback: Check result text for failure keywords if status is success
                                    const lowerText = (this.finalResult || "").toLowerCase();
                                    if (this.resultStatus === 'success') {
                                        const failureKeywords = ['failed', 'unable to', 'could not', 'incorrect', 'mismatch', 'error:'];
                                        if (failureKeywords.some(key => lowerText.includes(key))) {
                                            this.resultStatus = 'failed';
                                        }
                                    }

                                    // Sync IsQuotaError based on text if not already set
                                    if (!this.isQuotaError && (lowerText.includes('429') || lowerText.includes('quota') || lowerText.includes('resource_exhausted'))) {
                                        this.isQuotaError = true;
                                        this.resultStatus = 'failed';
                                    }

                                    if (this.resultStatus === 'failed' || this.isQuotaError) {
                                        this.logs.push({ type: 'error', text: `❌ ${this.finalResult}` });
                                    } else {
                                        this.logs.push({ type: 'done', text: `✅ ${this.finalResult}` });
                                    }
                                    
                                    const finalStatus = this.resultStatus;
                                    this.status = 'idle';
                                    this.addToHistory(taskPrompt, this.logs, this.finalResult, finalStatus, this.metrics);
                                    this.scrollToBottom();
                                    
                                    // Refresh Lucide icons after banner appears
                                    this.$nextTick(() => {
                                        if (window.lucide) {
                                            window.lucide.createIcons();
                                            // Debug log
                                            console.log('Banner displayed with status:', finalStatus, 'isQuotaError:', this.isQuotaError);
                                        }
                                    });
                                }
                                this.scrollToBottom();
                            } catch (e) {
                                console.warn('[BrowserAgent] Failed to parse SSE line:', line);
                            }
                        }
                    }
                }
            } catch (error) {
                if (error.name === 'AbortError') {
                    // Aborted gracefully
                } else {
                    this.logs.push({ type: 'error', text: `📡 Connection Error: ${error.message}` });
                    this.status = 'idle';
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
            this.resultStatus = 'failed';
            await this.addToHistory(this.task, this.logs, 'Task cancelled by user.', 'failed', null);
            
            try {
                await Auth.fetch('/api/browser-agent/stop', {
                    method: 'POST'
                });
            } catch (e) {
                console.error('[BrowserAgent] Failed to stop agent:', e);
            }
        },

        loadSuiteFile(event) {
            const file = event.target.files[0];
            if (!file) return;
            this.suiteName = file.name;
            const ext = file.name.split('.').pop().toLowerCase();
            const reader = new FileReader();
            reader.onload = (e) => {
                const content = e.target.result.trim();
                let tasks = [];
                let names = [];

                try {
                    if (ext === 'json') {
                        const parsed = JSON.parse(content);
                        const list = Array.isArray(parsed) ? parsed : (parsed.tasks || []);
                        tasks = list.map(t => (typeof t === 'string' ? t : (t.prompt || t.task || ''))).filter(Boolean);
                        names = list.map(t => (typeof t === 'string' ? '' : (t.name || '')));
                    } else if (ext === 'yaml' || ext === 'yml') {
                        const parsed = this.parseYAML(content);
                        tasks = parsed.map(t => t.prompt);
                        names = parsed.map(t => t.name);
                    } else if (ext === 'csv') {
                        tasks = this.parseCSV(content);
                        names = tasks.map(() => '');
                    } else {
                        // Plain text: line by line
                        tasks = content.split('\n').map(l => l.trim()).filter(l => l && !l.startsWith('#'));
                        names = tasks.map(() => '');
                    }
                } catch (err) {
                    console.error('[BrowserAgent] Suite parse error:', err);
                    alert('Failed to parse suite file. Please check the format.');
                }

                this.suiteTasks = tasks;
                this.suiteTaskNames = names;
                this.suiteFile = file;
                if (this.suiteTasks.length > 0) this.task = this.suiteTasks[0];
                this.$nextTick(() => { if (window.lucide) lucide.createIcons(); });
            };
            reader.readAsText(file);
            event.target.value = '';
        },

        parseYAML(text) {
            const lines = text.split('\n');
            const items = [];
            let currentItem = null;
            let capturingPrompt = false;
            let promptLines = [];

            lines.forEach(line => {
                const trimmed = line.trim();
                if (!trimmed || trimmed.startsWith('#')) return;

                // Check for new block: "- name:"
                if (trimmed.startsWith('- name:')) {
                    if (currentItem) {
                        currentItem.prompt = promptLines.join('\n').trim();
                        items.push(currentItem);
                    }
                    const name = trimmed.replace(/^- name:\s*/, '').replace(/^["']|["']$/g, '').trim();
                    currentItem = { name: name, prompt: '' };
                    promptLines = [];
                    capturingPrompt = false;
                } else if (trimmed.startsWith('name:')) {
                    // Fallback if '-' is missing but it's a new entry
                    if (currentItem && !capturingPrompt) {
                         currentItem.prompt = promptLines.join('\n').trim();
                         items.push(currentItem);
                         currentItem = null; 
                    }
                    const name = trimmed.replace(/^name:\s*/, '').replace(/^["']|["']$/g, '').trim();
                    currentItem = { name: name, prompt: '' };
                    promptLines = [];
                    capturingPrompt = false;
                } else if (trimmed.startsWith('prompt:')) {
                    capturingPrompt = true;
                    let p = trimmed.split('prompt:')[1].trim();
                    if (p.startsWith("'") || p.startsWith('"')) p = p.substring(1);
                    if (p) promptLines.push(p);
                } else if (capturingPrompt) {
                    // If it doesn't look like a new key, it's a prompt line
                    if (!trimmed.includes(': ')) {
                        let p = trimmed;
                        if (p.endsWith("'") || p.endsWith('"')) p = p.substring(0, p.length - 1);
                        if (p) promptLines.push(p);
                    } else {
                        capturingPrompt = false;
                    }
                }
            });

            if (currentItem) {
                currentItem.prompt = promptLines.join('\n').trim();
                items.push(currentItem);
            }
            return items;
        },
 stories: [
                { title: 'Standard Execution', desc: 'Standard browser agent workflow with real-time feedback' },
                { title: 'Batch Suite', desc: 'Running multiple tests in sequence with statistics' },
                { title: 'Rich Config', desc: 'Deep-dive into performance and behavior settings' }
            ],

        parseCSV(text) {
            const lines = text.split('\n');
            const tasks = [];
            lines.forEach((line, idx) => {
                if (idx === 0 && line.toLowerCase().includes('task')) return; // Skip header
                const cells = line.split(',').map(c => c.trim().replace(/^["']|["']$/g, ''));
                if (cells[0]) tasks.push(cells[0]);
            });
            return tasks;
        },

        getStats() {
            const total = this.promptHistory.length;
            const success = this.promptHistory.filter(h => h.status === 'success').length;
            const failed = this.promptHistory.filter(h => h.status === 'failed').length;
            return { total, success, failed };
        },

        renderStatsChart() {
            const ctx = document.getElementById('runsChart');
            if (!ctx) return;
            
            // Cleanup existing chart if any
            if (window.browserStatsChart) window.browserStatsChart.destroy();

            const history = [...this.promptHistory].reverse().slice(-15); // Last 15 runs
            const labels = history.map((h, i) => `Run ${i + 1}`);
            const data = history.map(h => h.status === 'success' ? 1 : 0);
            
            window.browserStatsChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: labels,
                    datasets: [{
                        label: 'Success (1) / Failure (0)',
                        data: data,
                        borderColor: '#8b5cf6',
                        backgroundColor: 'rgba(139, 92, 246, 0.1)',
                        borderWidth: 3,
                        tension: 0.4,
                        fill: true,
                        pointBackgroundColor: history.map(h => h.status === 'success' ? '#22c55e' : '#ef4444'),
                        pointRadius: 6
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: {
                        y: { min: -0.2, max: 1.2, ticks: { stepSize: 1, callback: v => v === 1 ? 'SUCCESS' : (v === 0 ? 'FAIL' : '') } },
                        x: { grid: { display: false } }
                    }
                }
            });
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
                await this.startAgent();
                // Wait for idle status
                await new Promise(resolve => {
                    const check = setInterval(() => {
                        if (this.status !== 'running') {
                            clearInterval(check);
                            resolve();
                        }
                    }, 500);
                });
                if (i < tasks.length - 1) await new Promise(r => setTimeout(r, 1000));
            }
            this.logs.push({ type: 'done', text: `✅ Suite complete — ${tasks.length} tasks executed.` });
        },

        scrollToBottom() {
            this.$nextTick(() => {
                const consoleEl = document.getElementById('browser-agent-console-body');
                if (consoleEl) consoleEl.scrollTop = consoleEl.scrollHeight;
            });
        },

        showHistory() {
            this.activeTab = 'results';
            this.$nextTick(() => {
                this.renderStatsChart();
                if (window.lucide) lucide.createIcons();
            });
        },

        async fetchDocs() {
            if (this.docs.length > 0) return;
            this.loadingDocs = true;
            try {
                const response = await Auth.fetch('/api/browser-agent/docs');
                if (response.ok) {
                    const data = await response.json();
                    this.docs = data.docs || [];
                    if (this.docs.length > 0) {
                        this.selectedDoc = this.docs[0];
                        this.parseDocsForHelp();
                    }
                }
            } catch (e) {
                console.error("Error fetching docs:", e);
            } finally {
                this.loadingDocs = false;
                this.$nextTick(() => { if (window.lucide) lucide.createIcons(); });
            }
        },

        parseDocsForHelp() {
            this.helpMap = {};
            this.docs.forEach(doc => {
                const lines = doc.content.split('\n');
                lines.forEach(line => {
                    // Match bullet points with code backticks: * `name`: description
                    let match = line.match(/^\s*[\*\-]\s*`([^`]+)`\s*(?:\([^)]*\))?\s*:\s*(.*)/);
                    if (match) {
                        this.helpMap[match[1]] = match[2].trim();
                    }
                    // Match table rows: | `NAME` | default | description |
                    match = line.match(/^\s*\|\s*`([^`]+)`\s*\|\s*[^|]*\|\s*([^|]+)\s*\|/);
                    if (match) {
                        this.helpMap[match[1]] = match[2].trim();
                    }
                });
            });
            // Fallback mappings for UI labels
            const fallbacks = {
                'use_vision': 'use_vision',
                'max_actions': 'max_actions_per_step',
                'max_failures': 'max_failures',
                'use_thinking': 'use_thinking',
                'flash_mode': 'flash_mode',
                'llm_timeout': 'llm_timeout',
                'step_timeout': 'step_timeout',
                'directly_open_url': 'directly_open_url',
                'headless': 'headless',
                'keep_alive': 'keep_alive'
            };
            Object.keys(fallbacks).forEach(uiKey => {
                if (!this.helpMap[uiKey] && this.helpMap[fallbacks[uiKey]]) {
                    this.helpMap[uiKey] = this.helpMap[fallbacks[uiKey]];
                }
            });
        },

        showHelp(field, title = null) {
            const content = this.helpMap[field] || "No detailed documentation found for this parameter.";
            this.helpModal = {
                show: true,
                title: title || field.replace(/_/g, ' ').toUpperCase(),
                content: content
            };
        }
    };
}

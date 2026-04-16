document.addEventListener('alpine:init', () => {
    Alpine.data('app', () => ({
        currentToolId: 'chat',
        viewTitle: 'Agent Chat',
        availableTools: [],
        globalConfig: {
            provider: 'gemini',
            gemini_model: 'gemini-2.5-flash',
            ollama_model: 'gemma3:1b',
            model: 'gemini-2.5-flash',
            api_key: '',
            base_url: 'http://localhost:11434',
            json_config: {
                openai: { apiKey: '', model: 'o3' },
                anthropic: { apiKey: '', model: 'claude-3-5-sonnet-20240620-v1:0' },
                azure: { endpoint: '', apiKey: '', model: 'gpt-4o', apiVersion: '2024-05-01-preview' },
                deepseek: { apiKey: '', model: 'deepseek-chat' },
                bedrock: { accessKey: '', secretKey: '', region: 'us-east-1', model: 'anthropic.claude-3-5-sonnet-20240620-v1:0' }
            }
        },
        showConfig: false,
        configForm: { 
            provider: 'gemini', gemini_model: '', ollama_model: '', api_key: '', base_url: '',
            showSecrets: false,
            json_config: {
                openai: { apiKey: '', model: '' },
                anthropic: { apiKey: '', model: '' },
                azure: { endpoint: '', apiKey: '', model: '', apiVersion: '' },
                deepseek: { apiKey: '', model: '' },
                bedrock: { accessKey: '', secretKey: '', region: '', model: '' }
            }
        },
        ollamaRunning: false,
        ollamaLoading: false,
        sidebarWidth: 260,
        isResizing: false,
        chatPrompt: '',
        chatHistory: [],
        chatSessions: [],
        currentSessionId: null,
        user: null,
        toolData: { prompt: '' },
        componentHtml: '',
        executionSteps: [],
        selectedArtifact: null,
        _boundStopResize: null,

        // Modal State
        showConfirmModal: false,
        confirmTitle: '',
        confirmMessage: '',
        confirmAction: null,

        async init() {
            // Initialize Global Store for Browser Agent persistence
            Alpine.store('browserAgent', {
                logs: [],
                status: 'idle',
                finalResult: '',
                task: '',
                errorMsg: '',
                setLogs(logs) { this.logs = logs },
                setStatus(status) { this.status = status },
                setFinalResult(result) { this.finalResult = result },
                setTask(task) { this.task = task },
                setError(msg) { this.errorMsg = msg }
            });

            // Initialize Global Store for Mobile Agent persistence
            Alpine.store('mobileAgent', {
                logs: [],
                status: 'idle',
                finalResult: '',
                task: '',
                errorMsg: '',
                setLogs(logs) { this.logs = logs },
                setStatus(status) { this.status = status },
                setFinalResult(result) { this.finalResult = result },
                setTask(task) { this.task = task },
                setError(msg) { this.errorMsg = msg }
            });

            this.user = await Auth.checkAuth();
            if (!this.user) return; // Unauthenticated users will be redirected
            this.loadSettings();
            await this.fetchTools();
            await this.loadChatSessions();

            // Show the landing page by default instead of auto-loading a chat
            if (this.currentToolId === 'chat') {
                this.initializeChatHistory();
            }
            await this.loadComponent(this.currentToolId);

            lucide.createIcons();

            // Sync with backend on start
            await this.syncConfigWithBackend();

            // Poll Ollama status
            this.checkOllamaStatus();
            setInterval(() => this.checkOllamaStatus(), 5000);
        },

        loadSettings() {
            // Load non-sensitive UI preferences from localStorage
            const saved = localStorage.getItem('q_ace_settings');
            if (saved) {
                try {
                    const settings = JSON.parse(saved);
                    // Only restore UI prefs like sidebar width from localStorage
                    if (settings.sidebarWidth) this.sidebarWidth = settings.sidebarWidth;
                } catch (e) {}
            }
            // LLM settings will be loaded from DB via syncConfigWithBackend()
        },

        async syncConfigWithBackend() {
            try {
                const response = await Auth.fetch('/api/config', {
                    method: 'GET'
                });
                if (response.ok) {
                    const data = await response.json();
                    if (data && data.provider) {
                        this.globalConfig = { 
                            ...this.globalConfig,
                            ...data,
                            json_config: { ...this.globalConfig.json_config, ...(data.json_config || {}) }
                        };
                    }
                }
            } catch (error) {
                console.error('Failed to sync config with backend:', error);
            }
        },

        async fetchTools() {
            try {
                const response = await Auth.fetch('/api/tools');
                if (response.ok) {
                    this.availableTools = await response.json();
                } else if (response.status === 401) {
                    this.logout();
                } else {
                    console.error('Failed to fetch tools:', await response.text());
                }
            } catch (error) {
                console.error('Failed to fetch tools:', error);
            }
        },

        async switchTool(toolId) {
            this.currentToolId = toolId;
            if (toolId === 'chat') {
                this.viewTitle = 'Agent Chat';
                await this.loadChatSessions(); // Refresh list
                if (this.chatSessions.length > 0 && !this.currentSessionId) {
                    await this.switchChatSession(this.chatSessions[0].id);
                }
            } else if (toolId === 'browser_agent') {
                this.viewTitle = 'Browser Agent';
            } else {
                const tool = this.availableTools.find(t => t.id === toolId);
                this.viewTitle = tool ? tool.name : 'Tool';
            }

            await this.loadComponent(toolId);
            this.$nextTick(() => { if (window.lucide) window.lucide.createIcons(); });
        },

        async loadComponent(toolId) {
            if (toolId === 'browser_agent') {
                try {
                    const response = await Auth.fetch('/components/browser_agent_tool.html');
                    if (!response.ok) throw new Error('Failed to load browser_agent_tool.html');
                    this.componentHtml = await response.text();
                    this.$nextTick(() => { if (window.lucide) window.lucide.createIcons(); });
                } catch (error) {
                    this.componentHtml = `<div class="p-8 text-red-500 font-bold">Error loading component: ${error.message}</div>`;
                }
                return;
            }

            if (toolId === 'admin_dashboard' || toolId === 'admin_management') {
                const fileName = `${toolId}.html`;
                try {
                    const response = await Auth.fetch(`/components/${fileName}`);
                    if (!response.ok) throw new Error(`Failed to load ${fileName}`);
                    this.componentHtml = await response.text();
                    this.$nextTick(() => { if (window.lucide) window.lucide.createIcons(); });
                } catch (error) {
                    this.componentHtml = `<div class="p-8 text-red-500 font-bold">Error loading component: ${error.message}</div>`;
                }
                return;
            }

            if (toolId === 'chat') {
                try {
                    const response = await Auth.fetch('/components/chat_view.html');
                    if (!response.ok) throw new Error('Failed to load chat_view.html');
                    this.componentHtml = await response.text();
                } catch (error) {
                    this.componentHtml = `<div class="p-8 text-red-500 font-bold">Error loading component: ${error.message}</div>`;
                }
                return;
            }

            const tool = this.availableTools.find(t => t.id === toolId);
            const isPlaceholder = tool?.ui?.is_placeholder;
            const fileName = isPlaceholder ? 'placeholder_tool.html' : `${toolId}_tool.html`;

            try {
                const response = await Auth.fetch(`/components/${fileName}`);
                if (!response.ok) throw new Error(`Failed to load ${fileName}`);
                this.componentHtml = await response.text();
                this.toolData = { prompt: '' }; // Reset tool data on switch
            } catch (error) {
                this.componentHtml = `<div class="p-8 text-red-500 font-bold">Error loading component: ${error.message}</div>`;
            }
        },

        logout() {
            Auth.logout();
        },

        async executePlaceholderAction() {
            this.triggerConfirm(
                'Integration Coming Soon',
                'This tool integration is currently in development and will be available in a future update. Check back later!',
                null
            );
        },

        toggleConfig() {
            this.showConfig = !this.showConfig;
            if (this.showConfig) {
                this.configForm = JSON.parse(JSON.stringify(this.globalConfig));
            }
            this.$nextTick(() => { if (window.lucide) window.lucide.createIcons(); });
        },

        async saveConfig() {
            try {
                const response = await Auth.fetch('/api/config', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(this.configForm)
                });
                if (response.ok) {
                    const data = await response.json();
                    this.globalConfig = { 
                        ...this.globalConfig,
                        ...data,
                        json_config: { ...this.globalConfig.json_config, ...(data.json_config || {}) }
                    };
                    // Only save non-sensitive UI layout prefs to localStorage
                    localStorage.setItem('q_ace_settings', JSON.stringify({ sidebarWidth: this.sidebarWidth }));
                    this.showConfig = false;
                }
            } catch (error) {
                alert('Failed to save configuration');
            }
        },

        async checkOllamaStatus() {
            try {
                const response = await Auth.fetch('/api/ollama/status');
                const data = await response.json();
                this.ollamaRunning = data.running;
            } catch (error) {
                this.ollamaRunning = false;
            }
        },

        async toggleOllama() {
            this.ollamaLoading = true;
            const action = this.ollamaRunning ? 'stop' : 'start';
            try {
                await Auth.fetch('/api/ollama/manage', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ action })
                });
                // Wait a bit for status to reflect
                setTimeout(() => {
                    this.checkOllamaStatus();
                    this.ollamaLoading = false;
                }, 2000);
            } catch (error) {
                alert('Ollama management failed');
                this.ollamaLoading = false;
            }
        },

        async loadChatSessions() {
            try {
                const response = await Auth.fetch('/api/chats');
                if (response.ok) {
                    this.chatSessions = await response.json();
                } else if (response.status === 401) {
                    this.logout();
                }
            } catch (error) {
                console.error('Failed to fetch chat sessions:', error);
            }
        },

        async createChatSession() {
            try {
                const response = await Auth.fetch('/api/chats', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ title: 'New Chat' })
                });
                if (response.ok) {
                    const session = await response.json();
                    this.chatSessions.unshift(session);
                    await this.switchChatSession(session.id);
                }
            } catch (error) {
                console.error('Failed to create chat session:', error);
            }
        },

        async switchChatSession(sessionId) {
            this.currentSessionId = sessionId;
            this.chatHistory = [];

            if (this.currentToolId !== 'chat') {
                await this.switchTool('chat');
            }

            try {
                const response = await Auth.fetch(`/api/chats/${sessionId}`);
                if (response.ok) {
                    const messages = await response.json();
                    console.log(`[DEBUG] Fetched ${messages.length} messages for session ${sessionId}`);
                    if (messages.length > 0) {
                        this.chatHistory = messages.map(m => {
                            let content = m.content;
                            let type = m.type;
                            if (m.type === 'workflow') {
                                try {
                                    content = JSON.parse(m.content);
                                    console.log(`[DEBUG] Parsed workflow message content:`, content);
                                } catch (e) {
                                    console.error('[DEBUG] Failed to parse workflow JSON:', e, m.content);
                                }
                            }
                            return { role: m.role, content: content, type: type };
                        });
                    } else {
                        this.initializeChatHistory();
                    }

                    const chat = this.chatSessions.find(c => c.id === sessionId);
                    if (chat) this.viewTitle = `Agent Chat - ${chat.title}`;
                } else if (response.status === 401) {
                    this.logout();
                } else {
                    this.initializeChatHistory();
                }
            } catch (error) {
                console.error('Failed to load chat history:', error);
                this.initializeChatHistory();
            }

            this.scrollToBottom();
            this.$nextTick(() => { if (window.lucide) window.lucide.createIcons(); });
        },

        async deleteChatSession(sessionId) {
            this.triggerConfirm(
                'Delete Chat Session',
                'Are you sure you want to delete this chat? This will permanently remove all messages.',
                async () => {
                    try {
                        const response = await Auth.fetch(`/api/chats/${sessionId}`, {
                            method: 'DELETE'
                        });
                        if (response.ok) {
                            this.chatSessions = this.chatSessions.filter(c => c.id !== sessionId);
                            if (this.currentSessionId === sessionId) {
                                this.currentSessionId = null;
                                this.chatHistory = [];
                                this.initializeChatHistory();
                                this.viewTitle = 'Agent Chat';
                            }
                        }
                    } catch (error) {
                        console.error('Failed to delete chat session:', error);
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

        async sendChat() {
            if (!sessionStorage.getItem('qace_chat_dev_warning_v2')) {
                this.triggerConfirm(
                    'Feature in Development',
                    'Welcome to the Agent Chat. Please note that this feature is an early development preview and has not been fully implemented yet. Workflows and AI orchestrations may be unstable or produce unexpected results.',
                    () => {
                        sessionStorage.setItem('qace_chat_dev_warning_v2', 'true');
                        this.sendChat();
                    }
                );
                return;
            }

            const prompt = this.chatPrompt.trim();
            if (!prompt) return;

            // Clear welcome flow if it was just started
            if (this.chatHistory.length === 2 && this.chatHistory[0].content.includes('Welcome')) {
                // Keep it if you want, but user likely wants a fresh chat
            }

            // Optimistic update
            this.chatHistory.push({ role: 'user', content: prompt, type: 'text' });
            this.chatPrompt = '';
            this.scrollToBottom();

            try {
                const response = await Auth.fetch('/api/chat', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ prompt: prompt, session_id: this.currentSessionId })
                });

                const reader = response.body.getReader();
                const decoder = new TextDecoder('utf-8');
                let currentAssistantMessage = null;
                let buffer = '';

                while (true) {
                    const { value, done } = await reader.read();
                    if (done) break;
                    
                    buffer += decoder.decode(value, { stream: true });
                    const chunks = buffer.split('\n\n');
                    buffer = chunks.pop(); // Keep the last incomplete piece
                    
                    for (const chunk of chunks) {
                        const lines = chunk.split('\n');
                        for (const line of lines) {
                            if (line.startsWith('data: ')) {
                                try {
                                    const rawData = line.substring(6);
                                    const dataObj = JSON.parse(rawData);
                                    console.log(`[SSE] Received event type: ${dataObj.type}`, dataObj);
                                    
                                    if (dataObj.type === 'session_init') {
                                        console.log(`[SSE] Session Init: ${dataObj.session_id}`);
                                        if (!this.currentSessionId) {
                                            this.currentSessionId = dataObj.session_id;
                                            await this.loadChatSessions(); 
                                        }
                                    } else if (dataObj.type === 'workflow') {
                                        console.log(`[SSE] Workflow update. Steps: ${dataObj.steps?.length || 0}`);
                                        if (!currentAssistantMessage) {
                                            currentAssistantMessage = { role: 'assistant', content: dataObj, type: 'workflow' };
                                            this.chatHistory.push(currentAssistantMessage);
                                        } else {
                                            const idx = this.chatHistory.indexOf(currentAssistantMessage);
                                            if (idx !== -1) {
                                                this.chatHistory.splice(idx, 1, { ...currentAssistantMessage, content: dataObj });
                                                currentAssistantMessage = this.chatHistory[idx];
                                            }
                                        }
                                        this.scrollToBottom();
                                    } else if (dataObj.type === 'tool_progress') {
                                        console.log(`[SSE] Tool Progress for step ${dataObj.step_id}: ${dataObj.text}`);
                                        if (currentAssistantMessage && currentAssistantMessage.content.steps) {
                                            const step = currentAssistantMessage.content.steps.find(s => s.id === dataObj.step_id);
                                            if (step) {
                                                step.result = dataObj.text;
                                                if (!step.logs) step.logs = [];
                                                const logEntry = `[${new Date().toLocaleTimeString()}] ${dataObj.text}`;
                                                step.logs.push(logEntry);
                                                console.log(`[DEBUG] Log added to step ${dataObj.step_id}:`, logEntry);
                                                
                                                const idx = this.chatHistory.indexOf(currentAssistantMessage);
                                                if (idx !== -1) {
                                                    this.chatHistory.splice(idx, 1, { ...currentAssistantMessage });
                                                }

                                                if (this.selectedArtifact && this.selectedArtifact.id === step.id) {
                                                    this.selectedArtifact.logs = [...step.logs];
                                                    this.selectedArtifact.result = step.result;
                                                }
                                            } else {
                                                console.warn(`[SSE] Progress received for unknown step ID: ${dataObj.step_id}`);
                                            }
                                        }
                                    } else if (dataObj.type === 'error') {
                                        console.error(`[SSE] Server Error:`, dataObj.text);
                                        this.chatHistory.push({ role: 'assistant', content: `Error: ${dataObj.text}`, type: 'text' });
                                        this.scrollToBottom();
                                    }
                                } catch (e) {
                                    console.error('[SSE] Failed to parse JSON chunk:', e, line);
                                }
                            }
                        }
                    }
                }
            } catch (error) {
                this.chatHistory.push({ role: 'assistant', content: `Error: ${error.message}`, type: 'text' });
            } finally {
                this.scrollToBottom();
                this.$nextTick(() => { if (window.lucide) window.lucide.createIcons(); });
            }
        },

        scrollToBottom() {
            this.$nextTick(() => {
                const hist = document.getElementById('chat-history');
                if (hist) hist.scrollTop = hist.scrollHeight;
            });
        },

        initializeChatHistory() {
            // Replaced the text-based welcome message with the new visual Landing Page in chat_view.html.
            // Leaving the array empty triggers the x-show="chatHistory.length === 0" empty state.
            this.chatHistory = [];
        },

        getStepResult(step) {
            if (step.result) return step.result;

            // Mock data for example flows
            if (step.tool === 'api') return 'GET /users\n\nHTTP/1.1 200 OK\nContent-Type: application/json\n\n[\n  {"id": 1, "username": "admin", "role": "admin"},\n  {"id": 2, "username": "qa_user", "role": "user"}\n]';
            if (step.tool === 'sqlite') return '-- Executing Query:\nSELECT id, username, role FROM users;\n\n-- Results (2 rows):\n1 | admin | admin\n2 | qa_user | user\n\nQuery executed successfully in 4ms.';
            if (step.tool === 'ai' && step.label.includes('Verification')) return 'AI Analysis Complete:\n\nThe API response data matches the local SQLite database records perfectly.\n- User "admin" (ID 1) exists in both sources.\n- User "qa_user" (ID 2) exists in both sources.\n\nVerification: PASSED';
            if (step.tool === 'ai') return 'AI Agent Output:\n\nTask executed successfully. Generated scripts and payloads match the required spec.\n\nTokens used: 142';
            if (step.tool === 'spec_analyzer') return 'Extracted Requirements from login-spec.pdf:\n\nREQ-001: User must be able to log in with valid credentials.\nREQ-002: System must lock account after 3 failed attempts.\nREQ-003: Password must be masked during input.\n\nIdentified 3 test scenarios.';
            if (step.tool === 'jenkins') return 'Triggering Jenkins Pipeline: "auth-automation-suite"\n\n[INFO] Starting build #42\n[INFO] Running tests on node: linux-agent-01\n[INFO] Test Scenario 1: Valid Login - PASS\n[INFO] Test Scenario 2: Account Lockout - PASS\n[INFO] Test Scenario 3: Password Masking - PASS\n\n[SUCCESS] Pipeline completed successfully.';
            if (step.tool === 'slack') return 'Sending Slack Message to #qa-alerts...\n\nPayload:\n{\n  "text": "All tests passed successfully for auth-automation-suite build #42."\n}\n\nStatus: 200 OK (Message Delivered)';
            if (step.tool === 'jira') return 'Creating Jira Issues...\n\n[SUCCESS] Created Bug: QACE-104 - "Login timeout on slow network"\n[SUCCESS] Created Task: QACE-105 - "Update login UI elements"';
            if (step.tool === 'github') return 'Executing Git Operations...\n\n$ git checkout -b automation-update\n$ git add tests/auth.spec.js\n$ git commit -m "chore: updated auth test suite"\n$ git push origin automation-update\n\n[SUCCESS] PR #12 ready for review.';
            if (step.tool === 'browser_agent') return 'Running Browser-Use Agent Tests...\n\nok 1 - should allow valid login\nok 2 - should show error on invalid credentials\n\n2 passed (3.4s)';

            return `Processing result from [ ${step.tool} ] will be displayed here as it is generated by the agent. \n\nYou can review, edit, and approve these outputs before they are passed to the next tool in the chain.`;
        },

        startResize(e) {
            this.isResizing = true;
            this._boundResize = this.resize.bind(this);
            this._boundStopResize = this.stopResize.bind(this);
            document.addEventListener('mousemove', this._boundResize);
            document.addEventListener('mouseup', this._boundStopResize);
            document.body.style.cursor = 'col-resize';
            document.body.style.userSelect = 'none';
        },

        resize(e) {
            if (!this.isResizing) return;
            const newWidth = e.clientX;
            if (newWidth > 200 && newWidth < 600) {
                this.sidebarWidth = newWidth;
            }
        },

        stopResize() {
            this.isResizing = false;
            document.removeEventListener('mousemove', this._boundResize);
            document.removeEventListener('mouseup', this._boundStopResize);
            document.body.style.cursor = 'default';
            document.body.style.userSelect = 'auto';

            this.globalConfig.sidebarWidth = this.sidebarWidth;
            localStorage.setItem('q_ace_settings', JSON.stringify(this.globalConfig));
        }
    }));
});

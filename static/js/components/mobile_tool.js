function mobileAgentTool() {
    return {
        activeTab: 'task',
        task: '',
        status: 'idle', // idle, running
        logs: [],
        finalResult: '',
        
        showErrorModal: false,
        errorMessage: '',

        appiumConfig: {
            serverUrl: 'http://localhost:4723',
            platformName: 'Android',
            udid: '',
            appPackage: '',
            appActivity: ''
        },

        eventSource: null,

        async init() {
            // Restore saved settings from backend
            try {
                const response = await Auth.fetch('/api/mobile-agent/config');
                if (response.ok) {
                    const data = await response.json();
                    this.appiumConfig = { ...this.appiumConfig, ...data };
                }
            } catch (e) {
                console.error("Failed to load mobile config:", e);
            }
        },

        async saveConfig() {
            try {
                const response = await Auth.fetch('/api/mobile-agent/config', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(this.appiumConfig)
                });

                if (response.ok) {
                    // Show success feedback if needed
                    const originalTab = this.activeTab;
                    this.activeTab = 'task';
                    setTimeout(() => {
                        alert("Mobile Configuration Saved Successfully!");
                        this.activeTab = originalTab;
                    }, 100);
                } else {
                    alert("Failed to save configuration.");
                }
            } catch (err) {
                alert("Error saving configuration: " + err.message);
            }
        },

        switchTab(tab) {
            this.activeTab = tab;
        },

        async startAgent() {
            if (!this.task.trim()) return;
            this.status = 'running';
            this.logs = [];
            this.finalResult = '';
            
            try {
                const response = await Auth.fetch('/api/mobile-agent/run', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        task: this.task,
                        appium_config: this.appiumConfig
                    })
                });

                if (!response.ok) {
                    const text = await response.text();
                    this.errorMessage = text || "Failed to start mobile agent. Is the server running?";
                    this.showErrorModal = true;
                    this.status = 'idle';
                    return;
                }

                // Connect to SSE stream
                this.connectToStream();
                
            } catch (err) {
                this.errorMessage = "Failed to initiate request: " + err.message;
                this.showErrorModal = true;
                this.status = 'idle';
            }
        },

        async connectToStream() {
            this.eventSource = new EventSource(`/api/mobile-agent/run`);
            
            this.eventSource.onmessage = (e) => {
                try {
                    const data = JSON.parse(e.data);
                    
                    if (data.type === 'step') {
                        this.logs.push(data);
                    } else if (data.type === 'error') {
                        this.logs.push(data);
                        this.errorMessage = data.text;
                        this.showErrorModal = true;
                        this.status = 'idle';
                        this.cleanup();
                    } else if (data.type === 'done') {
                        this.logs.push(data);
                        this.finalResult = data.result || 'Task completed successfully.';
                        this.status = 'idle';
                        this.cleanup();
                    }
                    this.scrollToBottom();
                } catch (err) {}
            };

            this.eventSource.onerror = (e) => {
                // If it fails immediately, the component may have been dismounted or connection dropped
                this.logs.push({ type: 'error', text: 'Lost connection to execution stream.' });
                this.status = 'idle';
                this.cleanup();
            };
        },

        async stopAgent() {
            if (this.status !== 'running') return;
            
            this.logs.push({ type: 'error', text: 'Task cancelled by user.' });
            this.status = 'idle';
            
            try {
                await Auth.fetch('/api/mobile-agent/stop', {
                    method: 'POST'
                });
            } catch (e) {}
            
            this.cleanup();
        },

        cleanup() {
            if (this.eventSource) {
                this.eventSource.close();
                this.eventSource = null;
            }
        },

        clearLogs() {
            this.logs = [];
            this.finalResult = '';
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

document.addEventListener('alpine:init', () => {
    Alpine.data('specAnalyzerTool', () => ({
        loading: false,
        saving: false,
        selectedSpec: 'custom',
        customPath: '',
        category: 'functionality',
        selectedTechniques: [],
        specOptions: [],
        testCases: '',
        resultFilename: '',
        savedTests: [],
        showHistory: false,
        showDeleteConfirm: false,
        fileToDelete: null,
        error: '',
        successMsg: '',

        techniquesOptions: [
            { label: 'Edge Cases', value: 'edge_cases' },
            { label: 'Boundary Value', value: 'bva' },
            { label: 'Equivalence Partitioning', value: 'ep' },
            { label: 'Decision Table', value: 'decision_table' },
            { label: 'State Transition', value: 'state_transition' },
            { label: 'Smoke', value: 'smoke' },
            { label: 'Positive/Negative', value: 'positive_negative' },
            { label: 'Pair-wise', value: 'pairwise' },
            { label: 'All', value: 'all' }
        ],

        async init() {
            await this.loadSpecFiles();
            await this.loadSavedTests();
            // Lucide icons need to be re-rendered as this is a dynamic component
            if (window.lucide) {
                window.lucide.createIcons();
            }
        },

        async loadSpecFiles() {
            try {
                const response = await Auth.fetch('/api/tool/action', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        tool_id: 'spec_analyzer',
                        action: 'get_spec_files',
                        data: {}
                    })
                });
                const result = await response.json();
                if (result.status === 'success') {
                    this.specOptions = result.options;
                }
            } catch (err) {
                console.error('Failed to load spec files:', err);
            }
        },

        toggleTechnique(val) {
            if (this.selectedTechniques.includes(val)) {
                this.selectedTechniques = this.selectedTechniques.filter(t => t !== val);
            } else {
                this.selectedTechniques.push(val);
            }
        },

        async generateTests() {
            this.loading = true;
            this.error = '';
            this.successMsg = '';
            this.testCases = '';

            try {
                const response = await Auth.fetch('/api/tool/action', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        tool_id: 'spec_analyzer',
                        action: 'analyze_spec',
                        data: {
                            spec_file: this.selectedSpec,
                            custom_path: this.customPath,
                            category: this.category,
                            techniques: this.selectedTechniques.includes('all') ? ['all'] : this.selectedTechniques
                        }
                    })
                });

                const result = await response.json();
                if (result.status === 'success') {
                    this.testCases = result.test_cases;
                    this.resultFilename = result.filename;
                    this.successMsg = 'Test cases generated successfully!';

                    // Re-render icons if any were added in the results
                    setTimeout(() => { if (window.lucide) window.lucide.createIcons(); }, 100);
                } else {
                    this.error = result.message || 'Failed to generate test cases.';
                }
            } catch (err) {
                this.error = 'Connection error: ' + err.message;
            } finally {
                this.loading = false;
            }
        },

        async saveToApp() {
            this.saving = true;
            try {
                const response = await Auth.fetch('/api/tool/action', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        tool_id: 'spec_analyzer',
                        action: 'save_to_local',
                        data: {
                            filename: this.resultFilename,
                            content: this.testCases,
                            source_name: this.selectedSpec !== 'custom' ? this.selectedSpec : (this.customPath || 'custom'),
                            category: this.category
                        }
                    })
                });
                const result = await response.json();
                if (result.status === 'success') {
                    this.successMsg = result.message;
                    if (result.filename) this.resultFilename = result.filename;
                    await this.loadSavedTests();
                } else {
                    this.error = result.message;
                }
            } catch (err) {
                this.error = 'Failed to save: ' + err.message;
            } finally {
                this.saving = false;
            }
        },

        async loadSavedTests() {
            try {
                const response = await Auth.fetch('/api/tool/action', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        tool_id: 'spec_analyzer',
                        action: 'get_saved_tests',
                        data: {}
                    })
                });
                const result = await response.json();
                if (result.status === 'success') {
                    this.savedTests = result.tests;
                    this.$nextTick(() => { if (window.lucide) window.lucide.createIcons(); });
                }
            } catch (err) {
                console.error('Failed to load saved tests:', err);
            }
        },

        async viewSavedTest(filename) {
            try {
                const response = await Auth.fetch('/api/tool/action', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        tool_id: 'spec_analyzer',
                        action: 'get_test_content',
                        data: { filename }
                    })
                });
                const result = await response.json();
                if (result.status === 'success') {
                    this.testCases = result.content;
                    this.resultFilename = filename;
                    this.error = '';
                    this.successMsg = '';
                    // Re-render icons
                    this.$nextTick(() => { if (window.lucide) window.lucide.createIcons(); });
                }
            } catch (err) {
                this.error = 'Failed to load test: ' + err.message;
            }
        },

        async deleteSavedTest(filename) {
            if (!filename) {
                filename = this.fileToDelete;
            } else {
                this.fileToDelete = filename;
                this.showDeleteConfirm = true;
                return;
            }

            try {
                const response = await Auth.fetch('/api/tool/action', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        tool_id: 'spec_analyzer',
                        action: 'delete_test',
                        data: { filename }
                    })
                });
                const result = await response.json();
                if (result.status === 'success') {
                    if (this.resultFilename === filename) {
                        this.testCases = '';
                        this.resultFilename = '';
                    }
                    await this.loadSavedTests();
                } else {
                    this.error = result.message;
                }
            } catch (err) {
                this.error = 'Failed to delete: ' + err.message;
            } finally {
                this.showDeleteConfirm = false;
                this.fileToDelete = null;
            }
        },

        downloadTests() {
            const blob = new Blob([this.testCases], { type: 'text/markdown' });
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = this.resultFilename || 'generated_tests.md';
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
        },

        renderMarkdown(content) {
            if (!content) return '';

            // 1. Basic block replacements (Headers)
            let processed = content
                .replace(/^### (.*$)/gim, '<h3 class="text-xl font-bold mt-8 mb-4 text-slate-800">$1</h3>')
                .replace(/^## (.*$)/gim, '<h2 class="text-2xl font-bold mt-10 mb-6 border-b border-slate-100 pb-3 text-slate-900">$1</h2>')
                .replace(/^# (.*$)/gim, '<h1 class="text-3xl font-black mt-12 mb-8 text-slate-900">$1</h1>')
                .replace(/\*\*(.*)\*\*/gim, '<strong>$1</strong>')
                .replace(/\*(.*)\*/gim, '<em>$1</em>');

            // 2. Table handling - process line by line
            const lines = processed.split('\n');
            const resultLines = [];
            let inTable = false;
            let currentTable = [];

            const renderTable = (rows) => {
                if (rows.length === 0) return '';
                let html = '<div class="overflow-x-auto my-8 shadow-sm border border-slate-200 rounded-2xl bg-white"><table class="min-w-full divide-y divide-slate-200 text-sm">';

                rows.forEach((row, i) => {
                    // Skip separator row
                    if (row.includes('---')) return;

                    const cells = row.split('|').filter((c, idx, arr) => {
                        // Keep internal cells, remove edges if they are empty
                        if (idx === 0 && c.trim() === '') return false;
                        if (idx === arr.length - 1 && c.trim() === '') return false;
                        return true;
                    });

                    const isHeader = i === 0 || (i > 1 && rows[i - 1].includes('---'));
                    html += `<tr class="${isHeader ? 'bg-slate-50/80 font-bold text-slate-700' : 'hover:bg-slate-50/50 transition-colors'}">`;

                    cells.forEach(cell => {
                        const tag = isHeader ? 'th' : 'td';
                        const classes = isHeader
                            ? 'px-6 py-4 text-left text-[10px] uppercase tracking-wider font-extrabold border-b border-slate-200'
                            : 'px-6 py-4 text-slate-600 border-b border-slate-50 leading-relaxed';
                        html += `<${tag} class="${classes}">${cell.trim()}</${tag}>`;
                    });
                    html += '</tr>';
                });

                html += '</table></div>';
                return html;
            };

            for (let i = 0; i < lines.length; i++) {
                const line = lines[i].trim();
                if (line.startsWith('|')) {
                    inTable = true;
                    currentTable.push(line);
                } else {
                    if (inTable) {
                        resultLines.push(renderTable(currentTable));
                        currentTable = [];
                        inTable = false;
                    }
                    resultLines.push(line);
                }
            }

            // Handle table at very end of content
            if (inTable) {
                resultLines.push(renderTable(currentTable));
            }

            return resultLines.join('\n').replace(/\n/g, '<br>');
        }
    }));
});

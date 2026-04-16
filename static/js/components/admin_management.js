document.addEventListener('alpine:init', () => {
    Alpine.data('adminManagement', () => ({
        showAddUser: false,
        showAddGroup: false,
        showEditGroup: false,
        showEditUser: false,

        // Modal Notification System
        modalNotice: { show: false, title: '', message: '', type: 'success' },
        confirmNotice: { show: false, title: '', message: '', onConfirm: null },

        users: [],
        groups: [],
        availableTools: [
            { id: 'sqlite', name: 'Text-to-SQL' },
            { id: 'api', name: 'REST API' },
            { id: 'spec_analyzer', name: 'Spec Analyzer' },
            { id: 'jenkins', name: 'Jenkins' },
            { id: 'github_actions', name: 'GitHub Actions' },
            { id: 'selenium', name: 'Selenium' },
            { id: 'playwright', name: 'Playwright' },
            { id: 'cypress', name: 'Cypress' },
            { id: 'postman', name: 'Postman' },
            { id: 'github', name: 'GitHub' },
            { id: 'jira', name: 'Jira' },
            { id: 'qase', name: 'Qase' },
            { id: 'slack', name: 'Slack' }
        ],
        newUser: { username: '', password: '', role: 'user', group_id: '' },
        newGroup: { name: '', description: '', tools: [] },
        editGroup: { id: '', name: '', description: '', tools: [] },
        editUser: { id: '', username: '', password: '', role: '', group_id: '' },

        async init() {
            await this.fetchGroups();
            await this.fetchUsers();
        },

        showModal(title, message, type = 'success') {
            this.modalNotice = { show: true, title, message, type };
        },

        async askConfirm(title, message) {
            return new Promise((resolve) => {
                this.confirmNotice = {
                    show: true,
                    title,
                    message,
                    onConfirm: () => {
                        this.confirmNotice.show = false;
                        resolve(true);
                    }
                };
            });
        },

        async fetchGroups() {
            try {
                const response = await Auth.fetch('/api/tool/action', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ tool_id: 'auth', action: 'get_groups', data: {} })
                });
                const data = await response.json();
                if (data.status === 'success') {
                    this.groups = data.groups;
                    if (this.groups.length > 0 && !this.newUser.group_id) {
                        this.newUser.group_id = this.groups[0].id;
                    }
                }
            } catch (e) { console.error('Failed to fetch groups', e); }
            finally {
                this.$nextTick(() => { if (window.lucide) window.lucide.createIcons(); });
            }
        },

        async fetchUsers() {
            try {
                const response = await Auth.fetch('/api/tool/action', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ tool_id: 'auth', action: 'get_users', data: {} })
                });
                const data = await response.json();
                if (data.status === 'success') this.users = data.users;
            } catch (e) { console.error('Failed to fetch users', e); }
            finally {
                this.$nextTick(() => { if (window.lucide) window.lucide.createIcons(); });
            }
        },

        async addUser() {
            try {
                const response = await Auth.fetch('/api/tool/action', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ tool_id: 'auth', action: 'create_user', data: this.newUser })
                });
                const data = await response.json();
                if (data.status === 'success') {
                    this.showModal('Success', 'User created successfully');
                    this.showAddUser = false;
                    this.newUser = { username: '', password: '', role: 'user', group_id: this.groups[0]?.id || '' };
                    await this.fetchUsers();
                } else this.showModal('Error', data.message, 'error');
            } catch (e) { this.showModal('Connection Error', 'Failed to connect to server', 'error'); }
        },

        async updateUser() {
            try {
                const response = await Auth.fetch('/api/tool/action', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ tool_id: 'auth', action: 'update_user', data: this.editUser })
                });
                const data = await response.json();
                if (data.status === 'success') {
                    this.showModal('Success', 'User updated successfully');
                    this.showEditUser = false;
                    await this.fetchUsers();
                } else this.showModal('Error', data.message, 'error');
            } catch (e) { this.showModal('Connection Error', 'Failed to connect to server', 'error'); }
        },

        openEditUser(user) {
            this.editUser = {
                id: user.id,
                username: user.username,
                password: '',
                role: user.role,
                group_id: user.group_id
            };
            this.showEditUser = true;
        },

        async deleteUser(id) {
            if (!(await this.askConfirm('Delete User', 'Are you sure you want to delete this user?'))) return;
            try {
                const response = await Auth.fetch('/api/tool/action', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ tool_id: 'auth', action: 'delete_user', data: { id } })
                });
                const data = await response.json();
                if (data.status === 'success') {
                    this.showModal('Success', 'User deleted');
                    await this.fetchUsers();
                } else this.showModal('Error', data.message, 'error');
            } catch (e) { this.showModal('Connection Error', 'Failed to connect to server', 'error'); }
        },

        async addGroup() {
            try {
                const response = await Auth.fetch('/api/tool/action', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ tool_id: 'auth', action: 'create_group', data: this.newGroup })
                });
                const data = await response.json();
                if (data.status === 'success') {
                    this.showModal('Success', 'Group created successfully');
                    this.showAddGroup = false;
                    this.newGroup = { name: '', description: '', tools: [] };
                    await this.fetchGroups();
                } else this.showModal('Error', data.message, 'error');
            } catch (e) { this.showModal('Connection Error', 'Failed to connect to server', 'error'); }
        },

        async updateGroup() {
            try {
                const response = await Auth.fetch('/api/tool/action', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ tool_id: 'auth', action: 'update_group', data: this.editGroup })
                });
                const data = await response.json();
                if (data.status === 'success') {
                    this.showModal('Success', 'Group updated successfully');
                    this.showEditGroup = false;
                    await this.fetchGroups();
                } else this.showModal('Error', data.message, 'error');
            } catch (e) { this.showModal('Connection Error', 'Failed to connect to server', 'error'); }
        },

        openEditGroup(group) {
            this.editGroup = JSON.parse(JSON.stringify(group));
            this.showEditGroup = true;
        },

        async deleteGroup(id) {
            if (!(await this.askConfirm('Delete Group', 'Are you sure? This will fail if users are in the group.'))) return;
            try {
                const response = await Auth.fetch('/api/tool/action', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ tool_id: 'auth', action: 'delete_group', data: { id } })
                });
                const data = await response.json();
                if (data.status === 'success') {
                    this.showModal('Success', 'Group deleted');
                    await this.fetchGroups();
                } else this.showModal('Error', data.message, 'error');
            } catch (e) { this.showModal('Connection Error', 'Failed to connect to server', 'error'); }
        },

        toggleTool(toolId, isEdit = false) {
            const list = isEdit ? this.editGroup.tools : this.newGroup.tools;
            const index = list.indexOf(toolId);
            if (index > -1) list.splice(index, 1);
            else list.push(toolId);
        }
    }));
});

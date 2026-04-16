const Auth = {
    currentUser: null,

    getToken() {
        return ''; // Legacy compat for app.js fetch headers
    },

    getUser() {
        return this.currentUser;
    },

    isAuthenticated() {
        return !!this.currentUser;
    },

    async fetch(url, options = {}) {
        options.credentials = 'same-origin';
        const response = await fetch(url, options);
        if (response.status === 401 && !url.includes('/api/auth/me')) {
            this.logout();
        }
        return response;
    },

    async logout() {
        try {
            await fetch('/api/auth/logout', { method: 'POST', credentials: 'same-origin' });
        } catch (e) { }
        this.currentUser = null;
        window.location.href = '/login.html';
    },

    async checkAuth() {
        const isLogin = window.location.pathname.endsWith('login.html');
        try {
            const res = await this.fetch('/api/auth/me');
            if (!res.ok) {
                throw new Error(`HTTP ${res.status}`);
            }
            const data = await res.json();
            this.currentUser = data.user;
            if (isLogin) {
                window.location.href = '/';
            }
            return this.currentUser;
        } catch(e) {
            this.currentUser = null;
            if (!isLogin) {
                window.location.href = '/login.html';
            }
            return null;
        }
    }

};

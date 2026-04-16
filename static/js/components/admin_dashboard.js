document.addEventListener('alpine:init', () => {
    Alpine.data('adminDashboard', () => ({
        stats: {
            total_users: 0,
            active_today: 0,
            top_tools: [],
            usage_by_group: []
        },
        async fetchAnalytics() {
            try {
                const response = await Auth.fetch('/api/admin/analytics');
                const data = await response.json();
                if (data.status === 'success') {
                    this.stats = data.analytics;
                }
            } catch (error) {
                console.error('Failed to fetch analytics:', error);
            } finally {
                this.$nextTick(() => {
                    if (window.lucide) window.lucide.createIcons();
                });
            }
        }
    }));
});

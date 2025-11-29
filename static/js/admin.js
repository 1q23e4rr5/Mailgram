// Admin panel functionality for Mailgram

class AdminPanel {
    constructor() {
        this.init();
    }

    init() {
        this.bindEvents();
        this.loadStats();
        this.initializeDataTables();
    }

    bindEvents() {
        // Tab navigation
        const tabs = document.querySelectorAll('[data-tab]');
        tabs.forEach(tab => {
            tab.addEventListener('click', (e) => {
                e.preventDefault();
                this.switchTab(tab.getAttribute('data-tab'));
            });
        });

        // Search functionality
        const searchInputs = document.querySelectorAll('[data-admin-search]');
        searchInputs.forEach(input => {
            input.addEventListener('input', this.debounce((e) => {
                this.handleSearch(e.target);
            }, 300));
        });

        // Bulk actions
        const bulkAction = document.querySelector('[data-bulk-action]');
        if (bulkAction) {
            bulkAction.addEventListener('change', (e) => {
                this.handleBulkAction(e.target.value);
            });
        }

        // Export buttons
        const exportButtons = document.querySelectorAll('[data-export]');
        exportButtons.forEach(button => {
            button.addEventListener('click', (e) => {
                this.exportData(e.target.getAttribute('data-export'));
            });
        });
    }

    switchTab(tabName) {
        // Hide all tab contents
        const tabContents = document.querySelectorAll('.tab-content');
        tabContents.forEach(content => {
            content.classList.remove('active');
        });

        // Remove active class from all tabs
        const tabs = document.querySelectorAll('[data-tab]');
        tabs.forEach(tab => {
            tab.classList.remove('active');
        });

        // Show selected tab content
        const activeContent = document.querySelector(`#${tabName}`);
        if (activeContent) {
            activeContent.classList.add('active');
        }

        // Activate selected tab
        const activeTab = document.querySelector(`[data-tab="${tabName}"]`);
        if (activeTab) {
            activeTab.classList.add('active');
        }

        // Load tab data if needed
        this.loadTabData(tabName);
    }

    async loadStats() {
        try {
            const response = await fetch('/admin/api/stats');
            const stats = await response.json();
            
            this.updateStatsDisplay(stats);
        } catch (error) {
            console.error('Error loading stats:', error);
        }
    }

    updateStatsDisplay(stats) {
        Object.keys(stats).forEach(statKey => {
            const element = document.querySelector(`[data-stat="${statKey}"]`);
            if (element) {
                element.textContent = stats[statKey];
            }
        });
    }

    initializeDataTables() {
        // Simple client-side sorting and filtering for admin tables
        const tables = document.querySelectorAll('.admin-table[data-sortable]');
        
        tables.forEach(table => {
            const headers = table.querySelectorAll('th[data-sort]');
            
            headers.forEach(header => {
                header.style.cursor = 'pointer';
                header.addEventListener('click', () => {
                    this.sortTable(table, header.getAttribute('data-sort'));
                });
            });
        });
    }

    sortTable(table, column) {
        const tbody = table.querySelector('tbody');
        const rows = Array.from(tbody.querySelectorAll('tr'));
        const currentOrder = table.getAttribute('data-sort-order') || 'asc';
        const newOrder = currentOrder === 'asc' ? 'desc' : 'asc';

        rows.sort((a, b) => {
            const aValue = a.querySelector(`td:nth-child(${this.getColumnIndex(table, column) + 1})`).textContent;
            const bValue = b.querySelector(`td:nth-child(${this.getColumnIndex(table, column) + 1})`).textContent;
            
            if (newOrder === 'asc') {
                return aValue.localeCompare(bValue);
            } else {
                return bValue.localeCompare(aValue);
            }
        });

        // Clear and re-add sorted rows
        rows.forEach(row => tbody.appendChild(row));
        table.setAttribute('data-sort-order', newOrder);

        // Update sort indicators
        this.updateSortIndicators(table, column, newOrder);
    }

    getColumnIndex(table, columnName) {
        const headers = table.querySelectorAll('th');
        for (let i = 0; i < headers.length; i++) {
            if (headers[i].getAttribute('data-sort') === columnName) {
                return i;
            }
        }
        return 0;
    }

    updateSortIndicators(table, column, order) {
        const headers = table.querySelectorAll('th');
        headers.forEach(header => {
            header.classList.remove('sort-asc', 'sort-desc');
        });

        const activeHeader = table.querySelector(`th[data-sort="${column}"]`);
        if (activeHeader) {
            activeHeader.classList.add(`sort-${order}`);
        }
    }

    handleSearch(input) {
        const searchTerm = input.value.toLowerCase();
        const table = input.closest('.admin-card').querySelector('table');
        
        if (!table) return;

        const rows = table.querySelectorAll('tbody tr');
        
        rows.forEach(row => {
            const text = row.textContent.toLowerCase();
            if (text.includes(searchTerm)) {
                row.style.display = '';
            } else {
                row.style.display = 'none';
            }
        });
    }

    handleBulkAction(action) {
        const selectedItems = this.getSelectedItems();
        
        if (selectedItems.length === 0) {
            alert('لطفاً حداقل یک آیتم را انتخاب کنید');
            return;
        }

        if (confirm(`آیا از انجام عملیات "${action}" روی ${selectedItems.length} آیتم مطمئن هستید؟`)) {
            this.performBulkAction(action, selectedItems);
        }
    }

    getSelectedItems() {
        const checkboxes = document.querySelectorAll('input[type="checkbox"][data-item-id]:checked');
        return Array.from(checkboxes).map(checkbox => checkbox.getAttribute('data-item-id'));
    }

    async performBulkAction(action, items) {
        try {
            const response = await fetch('/admin/api/bulk-action', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    action: action,
                    items: items
                })
            });

            const result = await response.json();
            
            if (result.success) {
                this.showNotification(`عملیات با موفقیت انجام شد`, 'success');
                this.refreshCurrentView();
            } else {
                this.showNotification(result.message, 'error');
            }
        } catch (error) {
            this.showNotification('خطا در انجام عملیات', 'error');
        }
    }

    exportData(type) {
        // Simple CSV export implementation
        const table = document.querySelector(`[data-export-table="${type}"]`);
        
        if (!table) {
            console.error('Table not found for export:', type);
            return;
        }

        const headers = Array.from(table.querySelectorAll('thead th'))
            .map(th => th.textContent.trim());
        
        const rows = Array.from(table.querySelectorAll('tbody tr'))
            .map(row => 
                Array.from(row.querySelectorAll('td'))
                    .map(td => td.textContent.trim())
                    .map(cell => `"${cell.replace(/"/g, '""')}"`)
                    .join(',')
            );

        const csv = [headers.join(','), ...rows].join('\n');
        this.downloadCSV(csv, `${type}-export-${new Date().toISOString().split('T')[0]}.csv`);
    }

    downloadCSV(csv, filename) {
        const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
        const link = document.createElement('a');
        
        if (link.download !== undefined) {
            const url = URL.createObjectURL(blob);
            link.setAttribute('href', url);
            link.setAttribute('download', filename);
            link.style.visibility = 'hidden';
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        }
    }

    refreshCurrentView() {
        // Reload the current page or tab data
        location.reload();
    }

    showNotification(message, type = 'info') {
        if (window.Mailgram && window.Mailgram.showNotification) {
            window.Mailgram.showNotification(message, type);
        } else {
            // Fallback notification
            alert(message);
        }
    }

    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    async loadTabData(tabName) {
        // Load additional data for specific tabs
        switch (tabName) {
            case 'reports':
                await this.loadReports();
                break;
            case 'analytics':
                await this.loadAnalytics();
                break;
        }
    }

    async loadReports() {
        // Implementation for loading reports data
        console.log('Loading reports data...');
    }

    async loadAnalytics() {
        // Implementation for loading analytics data
        console.log('Loading analytics data...');
    }
}

// Initialize admin panel when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    window.adminPanel = new AdminPanel();
});

// Utility functions for admin
function confirmAction(message) {
    return confirm(message || 'آیا از انجام این عمل مطمئن هستید؟');
}

function toggleUserStatus(userId, currentStatus) {
    if (confirmAction(`آیا می‌خواهید کاربر را ${currentStatus ? 'غیرفعال' : 'فعال'} کنید؟`)) {
        window.location.href = `/admin/toggle_user/${userId}`;
    }
}

function deleteUser(userId, userName) {
    if (confirmAction(`آیا از حذف کاربر "${userName}" مطمئن هستید؟ این عمل غیرقابل برگشت است.`)) {
        window.location.href = `/admin/delete_user/${userId}`;
    }
}

function handleReport(reportId, action) {
    if (confirmAction(`آیا می‌خواهید این گزارش را به عنوان "${action}" علامت‌گذاری کنید؟`)) {
        window.location.href = `/admin/handle_report/${reportId}/${action}`;
    }
}
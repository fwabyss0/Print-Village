/**
 * Print Village Chart.js Rendering Utility
 * Configures dark-theme premium styles, fetches sales / seller metric payloads
 * from API endpoints, and builds stunning charts.
 */

// Shared premium Chart.js Styling Options
const chartTheme = {
    fontFamily: "'Inter', sans-serif",
    textColor: 'rgba(255, 255, 255, 0.7)',
    gridColor: 'rgba(255, 255, 255, 0.05)',
    accentColor: '#6366f1', // Neon Purple-Indigo
    accentSuccess: '#10b981', // Emerald
    accentInfo: '#3b82f6', // Bright Blue
    accentWarning: '#f59e0b', // Amber
    accentDanger: '#ef4444' // Rose
};

function getCommonOptions(title) {
    return {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                labels: {
                    color: chartTheme.textColor,
                    font: { family: chartTheme.fontFamily, size: 11 }
                }
            }
        },
        scales: {
            x: {
                grid: { color: chartTheme.gridColor },
                ticks: { color: chartTheme.textColor, font: { family: chartTheme.fontFamily } }
            },
            y: {
                grid: { color: chartTheme.gridColor },
                ticks: { color: chartTheme.textColor, font: { family: chartTheme.fontFamily } }
            }
        }
    };
}

// ── SELLER ANALYTICS ────────────────────────────────────────────────────────

function loadSellerAnalytics() {
    fetch('/seller/analytics/data')
        .then(res => res.json())
        .then(data => {
            renderDailySales(data.daily);
            renderMonthlySales(data.monthly);
            renderTopProducts(data.top_products);
            renderStatusDist(data.status_dist);
        })
        .catch(err => console.error("Error loading seller analytics:", err));
}

function renderDailySales(dailyData) {
    const ctx = document.getElementById('dailySalesChart');
    if (!ctx) return;

    new Chart(ctx.getContext('2d'), {
        type: 'line',
        data: {
            labels: dailyData.labels,
            datasets: [{
                label: 'Revenue (NPR)',
                data: dailyData.data,
                borderColor: chartTheme.accentColor,
                backgroundColor: 'rgba(99, 102, 241, 0.15)',
                borderWidth: 3,
                fill: true,
                tension: 0.35,
                pointBackgroundColor: chartTheme.accentColor
            }]
        },
        options: getCommonOptions('Daily Sales')
    });
}

function renderMonthlySales(monthlyData) {
    const ctx = document.getElementById('monthlySalesChart');
    if (!ctx) return;

    new Chart(ctx.getContext('2d'), {
        type: 'bar',
        data: {
            labels: monthlyData.labels,
            datasets: [{
                label: 'Monthly Sales (NPR)',
                data: monthlyData.data,
                backgroundColor: 'rgba(59, 130, 246, 0.65)',
                borderColor: chartTheme.accentInfo,
                borderWidth: 1.5,
                borderRadius: 6
            }]
        },
        options: getCommonOptions('Monthly Sales')
    });
}

function renderTopProducts(topData) {
    const ctx = document.getElementById('topProductsChart');
    if (!ctx) return;

    new Chart(ctx.getContext('2d'), {
        type: 'bar',
        data: {
            labels: topData.labels,
            datasets: [{
                label: 'Units Sold',
                data: topData.data,
                backgroundColor: 'rgba(16, 185, 129, 0.65)',
                borderColor: chartTheme.accentSuccess,
                borderWidth: 1.5,
                borderRadius: 6
            }]
        },
        options: {
            ...getCommonOptions('Top Products'),
            indexAxis: 'y' // Horizontal bar
        }
    });
}

function renderStatusDist(statusData) {
    const ctx = document.getElementById('statusDistChart');
    if (!ctx) return;

    new Chart(ctx.getContext('2d'), {
        type: 'doughnut',
        data: {
            labels: statusData.labels,
            datasets: [{
                data: statusData.data,
                backgroundColor: [
                    'rgba(99, 102, 241, 0.8)',
                    'rgba(16, 185, 129, 0.8)',
                    'rgba(239, 44, 68, 0.8)',
                    'rgba(245, 158, 11, 0.8)'
                ],
                borderColor: 'rgba(15, 15, 30, 0.95)',
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'right',
                    labels: {
                        color: chartTheme.textColor,
                        font: { family: chartTheme.fontFamily, size: 11 }
                    }
                }
            }
        }
    });
}

// ── ADMIN ANALYTICS ─────────────────────────────────────────────────────────

function loadAdminAnalytics() {
    fetch('/admin/analytics/data')
        .then(res => res.json())
        .then(data => {
            renderAdminMonthly(data.monthly);
            renderAdminStatus(data.status_dist);
            renderAdminTopSellers(data.top_sellers);
        })
        .catch(err => console.error("Error loading admin analytics:", err));
}

function renderAdminMonthly(monthlyData) {
    const ctx = document.getElementById('adminMonthlyRevenueChart');
    if (!ctx) return;

    new Chart(ctx.getContext('2d'), {
        type: 'line',
        data: {
            labels: monthlyData.labels,
            datasets: [{
                label: 'Platform Sales (NPR)',
                data: monthlyData.data,
                borderColor: chartTheme.accentColor,
                backgroundColor: 'rgba(99, 102, 241, 0.1)',
                borderWidth: 3,
                fill: true,
                tension: 0.35,
                pointBackgroundColor: chartTheme.accentColor
            }]
        },
        options: getCommonOptions('Platform Monthly Volume')
    });
}

function renderAdminStatus(statusData) {
    const ctx = document.getElementById('adminStatusDistChart');
    if (!ctx) return;

    new Chart(ctx.getContext('2d'), {
        type: 'doughnut',
        data: {
            labels: statusData.labels,
            datasets: [{
                data: statusData.data,
                backgroundColor: [
                    'rgba(99, 102, 241, 0.8)',
                    'rgba(16, 185, 129, 0.8)',
                    'rgba(239, 44, 68, 0.8)',
                    'rgba(245, 158, 11, 0.8)'
                ],
                borderColor: 'rgba(15, 15, 30, 0.95)',
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        color: chartTheme.textColor,
                        font: { family: chartTheme.fontFamily, size: 10 }
                    }
                }
            }
        }
    });
}

function renderAdminTopSellers(sellersData) {
    const ctx = document.getElementById('adminTopSellersChart');
    if (!ctx) return;

    new Chart(ctx.getContext('2d'), {
        type: 'bar',
        data: {
            labels: sellersData.labels,
            datasets: [{
                label: 'Total Completed Sales (NPR)',
                data: sellersData.data,
                backgroundColor: 'rgba(59, 130, 246, 0.7)',
                borderColor: chartTheme.accentInfo,
                borderWidth: 1.5,
                borderRadius: 5
            }]
        },
        options: getCommonOptions('Top Sellers Revenue')
    });
}

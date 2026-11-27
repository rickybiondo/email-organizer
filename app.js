// Email Organizer Dashboard App

let labelChart = null;

async function loadDashboard() {
    try {
        const response = await fetch('data/latest.json');
        if (!response.ok) throw new Error('Failed to load data');
        const data = await response.json();
        renderDashboard(data);
    } catch (error) {
        console.error('Dashboard load error:', error);
        document.getElementById('lastUpdated').textContent = 'Error loading data';
    }
}

function renderDashboard(data) {
    const briefing = data.briefing;
    const sections = data.sections;

    // Update summary cards
    updateCard('valProcessed', briefing.summary.total_processed);
    updateCard('valClassified', briefing.summary.total_classified);
    updateCard('valLabelsApplied', briefing.summary.new_labels_applied);
    updateCard('valUnclassified', sections.unclassified?.count || 0);

    // Update last updated
    const updated = new Date(data.last_updated);
    document.getElementById('lastUpdated').textContent = 
        `Last updated: ${updated.toLocaleString()} UTC`;
    document.getElementById('footerDate').textContent = 
        `${updated.toLocaleDateString()} ${updated.toLocaleTimeString()} UTC`;

    // Render chart
    renderChart(data.chart_data);

    // Render sections
    renderSections(sections);
}

function updateCard(elementId, value) {
    const el = document.getElementById(elementId);
    if (el) el.textContent = value;
}

function renderChart(chartData) {
    const ctx = document.getElementById('labelChart').getContext('2d');

    if (labelChart) {
        labelChart.destroy();
    }

    // Filter out Auto/ prefix for cleaner labels
    const labels = chartData.labels.map(l => l.replace('Auto/', ''));
    const values = chartData.values;

    // Colors for different categories
    const colors = labels.map(label => {
        if (label.includes('Important')) return '#ef4444';
        if (label.includes('Work')) return '#3b82f6';
        if (label.includes('Personal')) return '#22c55e';
        if (label.includes('Newsletter')) return '#f59e0b';
        if (label.includes('Promotion')) return '#ec4899';
        if (label.includes('Unclassified')) return '#9ca3af';
        return '#6366f1';
    });

    labelChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: values,
                backgroundColor: colors,
                borderWidth: 2,
                borderColor: '#ffffff',
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    position: 'right',
                    labels: {
                        padding: 15,
                        usePointStyle: true,
                        font: { size: 12 }
                    }
                },
                tooltip: {
                    callbacks: {
                        label: (context) => {
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const percent = ((context.raw / total) * 100).toFixed(1);
                            return `${context.label}: ${context.raw} (${percent}%)`;
                        }
                    }
                }
            }
        }
    });
}

function renderSections(sections) {
    const container = document.getElementById('sectionsContainer');
    const sectionOrder = ['important', 'work', 'personal', 'newsletter', 'promotion', 'unclassified'];

    let html = '';

    for (const key of sectionOrder) {
        const section = sections[key];
        if (!section || section.count === 0) continue;

        html += `
            <section class="email-section">
                <header class="section-header">
                    <h2>${section.title}</h2>
                    <span class="section-badge">${section.count}</span>
                </header>
                <div class="email-list">
        `;

        if (section.emails && section.emails.length > 0) {
            for (const email of section.emails) {
                const labelsHtml = (email.labels || [])
                    .slice(0, 3)
                    .map(l => `<span class="label-tag">${l.replace('Auto/', '')}</span>`)
                    .join('');

                html += `
                    <article class="email-card">
                        <div class="email-header">
                            <span class="email-sender">${escapeHtml(email.sender)}</span>
                            <span class="email-date">${formatDate(email.date)}</span>
                        </div>
                        <h3 class="email-subject">${escapeHtml(email.subject)}</h3>
                        <p class="email-snippet">${escapeHtml(email.snippet)}</p>
                        <div class="email-labels">${labelsHtml}</div>
                    </article>
                `;
            }
        } else {
            html += '<p class="empty-state">No emails in this category</p>';
        }

        html += `
                </div>
            </section>
        `;
    }

    container.innerHTML = html;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatDate(dateStr) {
    if (!dateStr) return '';
    try {
        const date = new Date(dateStr);
        if (isNaN(date.getTime())) return dateStr;
        return date.toLocaleDateString(undefined, { 
            month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' 
        });
    } catch {
        return dateStr;
    }
}

// Keyboard shortcut: 'r' to refresh
document.addEventListener('keydown', (e) => {
    if (e.key === 'r' && !e.ctrlKey && !e.metaKey && !e.altKey) {
        const active = document.activeElement;
        if (active.tagName !== 'INPUT' && active.tagName !== 'TEXTAREA') {
            loadDashboard();
        }
    }
});

const API_BASE = '/api';

document.addEventListener('DOMContentLoaded', () => {
    loadSummary();
    loadAnomalies();

    document.getElementById('btnAsk').addEventListener('click', handleQuery);
    document.getElementById('queryInput').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') handleQuery();
    });
});

function setQuery(text) {
    document.getElementById('queryInput').value = text;
    handleQuery();
}

async function loadSummary() {
    try {
        const res = await fetch(`${API_BASE}/summary`);
        const data = await res.json();
        document.getElementById('valTotal').textContent = data.total_tickets;
        document.getElementById('valOpen').textContent = data.open_tickets;
        document.getElementById('valEscalated').textContent = data.escalated_tickets;
        document.getElementById('valResolved').textContent = data.resolved_tickets;
        document.getElementById('valAvgRating').textContent = data.average_rating || '-';
    } catch (e) {
        console.error('Failed to load summary', e);
    }
}

async function loadAnomalies() {
    try {
        const res = await fetch(`${API_BASE}/anomalies`);
        const data = await res.json();
        
        const cardsHtml = `
            <div class="anomaly-card">
                <h3>Resolution Outliers</h3>
                <div class="count">${data.statistical_outliers.length}</div>
            </div>
            <div class="anomaly-card">
                <h3>Aging High/Critical</h3>
                <div class="count">${data.aging_high_priority.length}</div>
            </div>
            <div class="anomaly-card">
                <h3>Unresolved Critical</h3>
                <div class="count">${data.unresolved_critical.length}</div>
            </div>
        `;
        document.getElementById('anomalyCards').innerHTML = cardsHtml;
        
        let listHtml = '';
        const allAnomalies = [
            ...data.statistical_outliers,
            ...data.aging_high_priority,
            ...data.unresolved_critical
        ];
        
        // deduplicate by ticket_id for display
        const uniqueAnomalies = [];
        const seen = new Set();
        for (const item of allAnomalies) {
            if (!seen.has(item.ticket_id)) {
                seen.add(item.ticket_id);
                uniqueAnomalies.push(item);
            }
        }
        
        if (uniqueAnomalies.length > 0) {
            listHtml += `<table class="data-table">
                <thead><tr><th>Ticket</th><th>Priority</th><th>Status</th><th>Reason</th><th>Summary</th></tr></thead>
                <tbody>`;
            uniqueAnomalies.forEach(a => {
                const pClass = a.priority === 'Critical' ? 'badge-critical' : (a.priority === 'High' ? 'badge-high' : '');
                const sClass = a.status === 'Escalated' ? 'badge-escalated' : 'badge-open';
                listHtml += `
                    <tr>
                        <td><strong>${a.ticket_id}</strong></td>
                        <td><span class="badge ${pClass}">${a.priority}</span></td>
                        <td><span class="badge ${sClass}">${a.status}</span></td>
                        <td class="text-red">${a.anomaly_reason}</td>
                        <td>${a.issue_summary || '-'}</td>
                    </tr>
                `;
            });
            listHtml += `</tbody></table>`;
        } else {
            listHtml = '<p>No anomalies detected.</p>';
        }
        
        document.getElementById('anomaliesList').innerHTML = listHtml;

    } catch (e) {
        console.error('Failed to load anomalies', e);
    }
}

async function handleQuery() {
    const query = document.getElementById('queryInput').value.trim();
    if (!query) return;

    const resContainer = document.getElementById('queryResults');
    const loading = document.getElementById('queryLoading');
    const errorBox = document.getElementById('queryError');
    const content = document.getElementById('queryContent');

    resContainer.classList.remove('hidden');
    loading.classList.remove('hidden');
    errorBox.classList.add('hidden');
    content.classList.add('hidden');

    try {
        const res = await fetch(`${API_BASE}/query`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query })
        });
        
        const data = await res.json();
        
        if (!res.ok) {
            throw new Error(data.detail || 'Query failed');
        }

        loading.classList.add('hidden');
        content.classList.remove('hidden');
        
        document.getElementById('llmBadge').textContent = data.llm_used ? 'Powered by LLM' : 'Fallback Parser';
        document.getElementById('intentCode').textContent = JSON.stringify(data.intent, null, 2);
        document.getElementById('answerText').textContent = data.answer;
        
        renderTable(data.data);

    } catch (e) {
        loading.classList.add('hidden');
        errorBox.classList.remove('hidden');
        errorBox.textContent = e.message;
    }
}

function renderTable(dataArray) {
    const thead = document.getElementById('dtHead');
    const tbody = document.getElementById('dtBody');
    thead.innerHTML = '';
    tbody.innerHTML = '';
    
    if (!dataArray || dataArray.length === 0) return;
    
    const keys = Object.keys(dataArray[0]);
    const trHead = document.createElement('tr');
    keys.forEach(k => {
        const th = document.createElement('th');
        th.textContent = k;
        trHead.appendChild(th);
    });
    thead.appendChild(trHead);
    
    dataArray.forEach(row => {
        const tr = document.createElement('tr');
        keys.forEach(k => {
            const td = document.createElement('td');
            td.textContent = row[k] === null || row[k] === '' ? '-' : row[k];
            tr.appendChild(td);
        });
        tbody.appendChild(tr);
    });
}

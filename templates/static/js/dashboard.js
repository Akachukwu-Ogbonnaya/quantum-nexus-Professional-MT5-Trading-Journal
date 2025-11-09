// static/js/dashboard.js
document.addEventListener('DOMContentLoaded', function () {
  const socket = io('/realtime', { transports: ['websocket'] });
  const connToastEl = document.getElementById('connToast');
  const connToast = new bootstrap.Toast(connToastEl, { delay: 3000 });

  // KPI elements
  const kpiBalance = document.getElementById('kpi-balance');
  const kpiWinrate = document.getElementById('kpi-winrate');
  const kpiAvgRR = document.getElementById('kpi-avgrr');
  const kpiNetProfit = document.getElementById('kpi-netprofit');
  const logPanel = document.getElementById('realtime-log-panel');

  // Charts
  const equityCtx = document.getElementById('equityChart').getContext('2d');
  const wlCtx = document.getElementById('wlChart').getContext('2d');
  let equityChart = new Chart(equityCtx, {
    type: 'line',
    data: { labels: [], datasets: [{ label: 'Balance', data: [], tension: 0.2, borderColor: '#00e5ff', backgroundColor: 'rgba(0,229,255,0.08)' }]},
    options: { responsive:true, plugins:{legend:{display:false}} }
  });
  let wlChart = new Chart(wlCtx, {
    type: 'doughnut',
    data: { labels: ['Win','Loss','Break Even'], datasets:[{ data:[0,0,0], backgroundColor:['#00e5ff','#ff4d4f','#6c757d'] }]},
    options: { responsive:true, plugins:{legend:{position:'bottom'}} }
  });

  function showToast(message) {
    document.getElementById('connToastBody').textContent = message;
    connToast.show();
  }

  socket.on('connect', () => {
    showToast('🔄 Connection Restored');
    socket.emit('subscribe', { channels: ['data','logs'] });
  });

  socket.on('disconnect', () => {
    showToast('⚠️ Connection Lost');
  });

  socket.on('data_update', (payload) => {
    // update KPIs
    try {
      const stats = payload.stats || {};
      const account = payload.account_data || {};
      const all = stats.all || {};
      kpiBalance.textContent = '$' + (account.balance !== undefined ? Number(account.balance).toFixed(2) : '0.00');
      kpiWinrate.textContent = (all.win_rate !== undefined ? all.win_rate : 0) + '%';
      kpiAvgRR.textContent = (all.avg_rr !== undefined ? all.avg_rr : 0).toFixed(2);
      kpiNetProfit.textContent = '$' + (all.net_profit !== undefined ? Number(all.net_profit).toFixed(2) : '0.00');
    } catch (e) {
      console.error('Error updating KPIs', e);
    }

    // update charts if account_history provided
    if (payload.account_history) {
      const labels = payload.account_history.map(r => r.timestamp);
      const balances = payload.account_history.map(r => r.balance);
      equityChart.data.labels = labels;
      equityChart.data.datasets[0].data = balances;
      equityChart.update();
    } else {
      // fetch via API endpoint
      fetch('/api/equity_curve').then(r=>r.json()).then(data=>{
        equityChart.data.labels = data.timestamps || [];
        equityChart.data.datasets[0].data = data.balance || [];
        equityChart.update();
      }).catch(()=>{});
    }

    // update profit/loss distribution
    fetch('/api/profit_loss_distribution').then(r=>r.json()).then(d=>{
      wlChart.data.datasets[0].data = [d.winning,d.losing,d.break_even];
      wlChart.update();
    }).catch(()=>{});
  });

  socket.on('log_update', (entry) => {
    if (!entry) return;
    const node = document.createElement('div');
    node.className = 'log-line';
    node.textContent = `[${entry.timestamp}] ${entry.level}: ${entry.message}`;
    logPanel.prepend(node);
    // trim
    while (logPanel.childElementCount > 200) logPanel.removeChild(logPanel.lastChild);
  });

  // initial load of charts
  fetch('/api/equity_curve').then(r=>r.json()).then(data=>{
    equityChart.data.labels = data.timestamps || [];
    equityChart.data.datasets[0].data = data.balance || [];
    equityChart.update();
  }).catch(()=>{});

  fetch('/api/profit_loss_distribution').then(r=>r.json()).then(d=>{
    wlChart.data.datasets[0].data = [d.winning,d.losing,d.break_even];
    wlChart.update();
  }).catch(()=>{});

  // date filter apply
  document.getElementById('applyFilter').addEventListener('click', ()=>{
    const val = document.getElementById('dateRange').value;
    if (!val) return;
    const parts = val.split('to').map(s=>s.trim());
    let qs = '';
    if (parts.length === 2) qs = '?from=' + encodeURIComponent(parts[0]) + '&to=' + encodeURIComponent(parts[1]);
    fetch('/api/trade_results_data' + qs).then(r=>r.json()).then(res=>{
      const rows = res.trades || [];
      const tableDiv = document.getElementById('tradeResultsTable');
      if (rows.length === 0) {
        tableDiv.innerHTML = '<p class="small text-muted">No trades in selected range.</p>';
        return;
      }
      let html = '<table class="table table-dark table-striped"><thead><tr><th>Entry</th><th>Pair</th><th>Type</th><th>Profit</th><th>Duration</th></tr></thead><tbody>';
      for (const t of rows) {
        html += `<tr><td>${t.entry_time || ''}</td><td>${t.symbol || ''}</td><td>${t.type || ''}</td><td>${t.profit || 0}</td><td>${t.duration || ''}</td></tr>`;
      }
      html += '</tbody></table>';
      tableDiv.innerHTML = html;
    }).catch(()=>{});
  });

});

(() => {
  const els = {
    tabs: document.querySelectorAll('.live-tab'),
    total: document.querySelector('[data-stat-total]'),
    s2xx: document.querySelector('[data-stat-2xx]'),
    s3xx: document.querySelector('[data-stat-3xx]'),
    s4xx: document.querySelector('[data-stat-4xx]'),
    s5xx: document.querySelector('[data-stat-5xx]'),
    s2xxP: document.querySelector('[data-stat-2xx-p]'),
    s3xxP: document.querySelector('[data-stat-3xx-p]'),
    s4xxP: document.querySelector('[data-stat-4xx-p]'),
    s5xxP: document.querySelector('[data-stat-5xx-p]'),
    cAll: document.querySelector('[data-count="all"]'),
    c2xx: document.querySelector('[data-count="2xx"]'),
    c3xx: document.querySelector('[data-count="3xx"]'),
    c4xx: document.querySelector('[data-count="4xx"]'),
    c5xx: document.querySelector('[data-count="5xx"]'),
    errRate: document.querySelector('[data-insight-error-rate]'),
    topPath: document.querySelector('[data-insight-top-path]'),
    method: document.querySelector('[data-insight-method]'),
    avg: document.querySelector('[data-insight-avg]'),
    successRate: document.querySelector('[data-insight-success-rate]'),
    lines: document.getElementById('live-logs-lines'),
    term: document.getElementById('live-logs-terminal'),
    pauseBtn: document.getElementById('live-logs-pause'),
    clearBtn: document.getElementById('live-logs-clear'),
    auto: document.getElementById('live-logs-autoscroll'),
    status: document.getElementById('live-logs-status'),
  };

  let activeTab = 'all';
  let paused = false;
  let lastId = 0;
  let buffer = [];

  function family(status) {
    if (status >= 500) return '5xx';
    if (status >= 400) return '4xx';
    if (status >= 300) return '3xx';
    if (status >= 200) return '2xx';
    return 'all';
  }

  function renderStats() {
    const total = buffer.length;
    const c = { '2xx': 0, '3xx': 0, '4xx': 0, '5xx': 0 };
    const paths = {};
    const methods = {};
    let durSum = 0;
    buffer.forEach(e => {
      const f = family(e.status);
      if (c[f] !== undefined) c[f]++;
      durSum += e.duration || 0;
      if (e.status >= 400) {
        paths[e.path] = (paths[e.path] || 0) + 1;
      }
      methods[e.method] = (methods[e.method] || 0) + 1;
    });
    const pct = n => total ? Math.round((n / total) * 100) + '%' : '0%';
    els.total.textContent = total;
    els.s2xx.textContent = c['2xx']; els.s2xxP.textContent = pct(c['2xx']);
    els.s3xx.textContent = c['3xx']; els.s3xxP.textContent = pct(c['3xx']);
    els.s4xx.textContent = c['4xx']; els.s4xxP.textContent = pct(c['4xx']);
    els.s5xx.textContent = c['5xx']; els.s5xxP.textContent = pct(c['5xx']);
    els.cAll.textContent = total;
    els.c2xx.textContent = c['2xx']; els.c3xx.textContent = c['3xx']; els.c4xx.textContent = c['4xx']; els.c5xx.textContent = c['5xx'];
    els.errRate.textContent = pct(c['4xx'] + c['5xx']);
    if (els.successRate) els.successRate.textContent = pct(c['2xx']);
    const top = Object.entries(paths).sort((a,b)=>b[1]-a[1])[0];
    els.topPath.textContent = top ? `${top[0]} (${top[1]})` : '—';
    const topM = Object.entries(methods).sort((a,b)=>b[1]-a[1])[0];
    els.method.textContent = topM ? topM[0] : '—';
    els.avg.textContent = `avg ${total ? Math.round(durSum/total) : 0} ms`;
  }

  function visible(e) {
    if (activeTab === 'all') return true;
    return family(e.status) === activeTab;
  }

  function color(status) {
    if (status >= 500) return 'text-red-400';
    if (status >= 400) return 'text-amber-300';
    if (status >= 300) return 'text-blue-400';
    return 'text-green-400';
  }

  function render() {
    if (paused) { renderStats(); return; }
    els.lines.innerHTML = '';
    buffer.forEach(e => {
      if (!visible(e)) return;
      const row = document.createElement('div');
      row.className = 'live-line flex gap-3 px-2 py-0.5 rounded';
      row.dataset.id = e.id;
      row.innerHTML = `<span class="text-gray-500 shrink-0">${new Date(e.ts).toLocaleTimeString()}</span><span class="shrink-0">${e.method}</span><span class="shrink-0 truncate max-w-[260px]">${e.path}</span><span class="shrink-0 font-bold ${color(e.status)}">${e.status}</span><span class="text-gray-400">${e.duration}ms</span><span class="truncate">${e.msg}</span>`;
      els.lines.appendChild(row);
      if (e.cause) {
        const cause = document.createElement('div');
        cause.className = 'text-amber-300 pl-6 truncate';
        cause.textContent = e.cause;
        els.lines.appendChild(cause);
      }
    });
    renderStats();
    if (els.auto && els.auto.checked && els.term) {
      requestAnimationFrame(() => {
        els.term.scrollTop = els.term.scrollHeight;
      });
    }
  }

  let debounce;
  function scheduleRender() {
    clearTimeout(debounce);
    debounce = setTimeout(render, 150);
  }

  els.tabs.forEach(btn => btn.addEventListener('click', () => {
    activeTab = btn.dataset.tab;
    els.tabs.forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    render();
  }));
  els.pauseBtn.addEventListener('click', () => {
    paused = !paused;
    els.pauseBtn.textContent = paused ? 'Resume' : 'Pause';
  });
  els.clearBtn.addEventListener('click', () => { buffer = []; render(); });

  function connect() {
    const baseUrl = window.__LIVE_LOGS_STREAM_URL__ || '/admin/live-logs/stream/';
    const url = `${baseUrl}?last_id=${lastId}`;
    const es = new EventSource(url);
    els.status.textContent = 'connecting…';
    es.onopen = () => { els.status.textContent = 'live'; };
    es.onmessage = (ev) => {
      try {
        const data = JSON.parse(ev.data);
        if (ev.lastEventId) lastId = parseInt(ev.lastEventId, 10) || data.id || lastId;
        else if (data.id) lastId = data.id;
        buffer.push(data);
        if (buffer.length > 500) buffer.shift();
        scheduleRender();
      } catch {}
    };
    es.onerror = () => {
      els.status.textContent = 'reconnecting…';
      es.close();
      setTimeout(connect, 3000);
    };
  }
  connect();
})();

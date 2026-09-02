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
    downloadBtn: document.getElementById('live-logs-download'),
    search: document.getElementById('live-logs-search'),
    auto: document.getElementById('live-logs-autoscroll'),
    status: document.getElementById('live-logs-status'),
  };

  let activeTab = 'all';
  let activeRole = 'all';
  let paused = false;
  let lastId = 0;
  let buffer = [];
  let searchQuery = '';

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
    const causes = {};
    let durSum = 0;
    const durations = [];
    let burstCount = 0;
    const now = Date.now();
    buffer.forEach(e => {
      const f = family(e.status);
      if (c[f] !== undefined) c[f]++;
      durSum += e.duration || 0;
      durations.push(e.duration || 0);
      if (e.status >= 400) {
        paths[e.path] = (paths[e.path] || 0) + 1;
        const causeKey = (e.cause || '').slice(0, 60) || 'unknown';
        causes[causeKey] = (causes[causeKey] || 0) + 1;
        // burst: errors in last 60s
        try { if (now - new Date(e.ts).getTime() < 60000) burstCount++; } catch {}
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
    // p95
    durations.sort((a,b)=>a-b);
    const p95 = durations.length ? durations[Math.floor(durations.length*0.95)] : 0;
    els.avg.textContent = `avg ${total ? Math.round(durSum/total) : 0} ms • p95 ${p95}ms${burstCount >= 5 ? ` • BURST ${burstCount}/min` : ''}`;
    // grouped cause insight (reuse topPath second line if needed, but keep topPath as path)
    // Add burst highlight to status
    if (burstCount >= 5) {
      els.status.textContent = `BURST ${burstCount} errors/min`;
      els.status.className = 'ml-auto text-xs font-mono text-red-500 font-bold self-center';
    }
  }

  function highlight(text, query) {
    if (!query || !text) return text;
    try {
      const esc = query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
      return text.replace(new RegExp(`(${esc})`, 'gi'), '<mark class="bg-yellow-300 text-black px-0.5 rounded">$1</mark>');
    } catch { return text; }
  }
  function roleOf(e) { return (e.role || 'guest').toLowerCase(); }
  function visible(e) {
    const tabOk = activeTab === 'all' ? true : family(e.status) === activeTab;
    if (!tabOk) return false;
    const roleOk = activeRole === 'all' ? true : roleOf(e) === activeRole;
    if (!roleOk) return false;
    if (!searchQuery) return true;
    const hay = `${e.method} ${e.path} ${e.cause} ${e.msg} ${e.status} ${e.role}`.toLowerCase();
    return hay.includes(searchQuery.toLowerCase());
  }
  function roleColor(role) {
    const r = (role || '').toLowerCase();
    if (r === 'customer') return 'border-blue-500';
    if (r === 'deliveryman') return 'border-purple-500';
    if (r === 'ops') return 'border-lime-500';
    if (r === 'guest') return 'border-white';
    return 'border-base-700';
  }

  function color(status) {
    if (status >= 500) return 'text-red-400';
    if (status >= 400) return 'text-amber-300';
    if (status >= 300) return 'text-blue-400';
    return 'text-green-400';
  }

  function render() {
    if (paused) { renderStats(); return; }
    // Use DocumentFragment for 1000 lines perf — single reflow
    const frag = document.createDocumentFragment();
    let shown = 0;
    buffer.forEach(e => {
      if (!visible(e)) return;
      shown++;
      const row = document.createElement('div');
      // keep sequential flow, just add vertical line at start to mark group (role)
      row.className = `live-line flex gap-3 px-2 py-0.5 rounded border-l-2 ${roleColor(e.role)}`;
      row.dataset.id = e.id;
      // highlight search matches
      const q = searchQuery;
      row.innerHTML = `<span class="text-gray-500 shrink-0">${new Date(e.ts).toLocaleTimeString()}</span><span class="shrink-0">${highlight(e.method, q)}</span><span class="shrink-0 break-all max-w-[260px]">${highlight(e.path, q)}</span><span class="shrink-0 font-bold ${color(e.status)}">${e.status}</span><span class="text-gray-400">${e.duration}ms</span><span class="break-all whitespace-pre-wrap">${highlight(e.msg, q)}</span>`;
      frag.appendChild(row);
      if (e.cause) {
        const cause = document.createElement('div');
        cause.className = `text-amber-300 pl-6 break-all whitespace-pre-wrap border-l-2 ${roleColor(e.role)} ml-2`;
        cause.innerHTML = highlight(e.cause, q);
        frag.appendChild(cause);
      }
      const sep = document.createElement('div');
      sep.className = 'text-gray-700 text-left py-1 select-none font-mono text-xs';
      sep.style.color = '#4a5568';
      sep.textContent = '------------------------------------------------------------';
      frag.appendChild(sep);
    });
    els.lines.innerHTML = '';
    els.lines.appendChild(frag);
    // Empty state
    if (shown === 0 && buffer.length > 0) {
      const empty = document.createElement('div');
      empty.className = 'text-center text-gray-500 py-8';
      empty.textContent = `No results for "${searchQuery}" — ${buffer.length} lines filtered`;
      els.lines.appendChild(empty);
    }
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
  document.querySelectorAll('.live-role').forEach(btn => btn.addEventListener('click', () => {
    activeRole = btn.dataset.role;
    document.querySelectorAll('.live-role').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    render();
  }));
  if (els.search) {
    let t;
    els.search.addEventListener('input', (e) => {
      clearTimeout(t);
      t = setTimeout(() => { searchQuery = e.target.value.trim(); render(); }, 150);
    });
  }
  if (els.downloadBtn) {
    els.downloadBtn.addEventListener('click', () => {
      const visibleLines = buffer.filter(visible);
      const text = visibleLines.map(e => `${new Date(e.ts).toISOString()} ${e.method} ${e.path} ${e.status} ${e.duration}ms ${e.msg} ${e.cause ? '| cause=' + e.cause : ''} [${e.role}]`).join('\n-----------\n');
      const blob = new Blob([text], {type: 'text/plain'});
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url; a.download = `live-logs-${new Date().toISOString().slice(0,19)}.txt`; a.click();
      URL.revokeObjectURL(url);
    });
  }
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
        if (buffer.length > 1000) buffer.shift();
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

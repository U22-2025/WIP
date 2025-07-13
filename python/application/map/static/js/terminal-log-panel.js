// terminal-log-panel.js
// ログパネルに関するすべての処理をモジュール化
// --------------------------------------------------
// 使い方:
// <script src="terminal-log-panel.js"></script>
// 内部で window.addDemoLog などの関数を公開しているので、
// HTML 側の onclick はそのまま動作します。

(() => {
  // ------------------- TerminalLogPanel -------------------
  class TerminalLogPanel {
    constructor() {
      this.logEntries = document.getElementById('log-entries');
      this.emptyState = document.getElementById('empty-state');
      this.autoScroll = true;
      this.logCount = 0;
      this.totalResponseTime = 0;
      this.packetCount = 0;
      this.totalPacketTime = 0;
      this.initializeEventListeners();
    }

    // ---------------- Initialise ----------------
    initializeEventListeners() {
      this.simulateConnection();
    }

    // Demo: fake connection status switching
    simulateConnection() {
      const connectionDot = document.getElementById('connection-dot');
      const connectionText = document.getElementById('connection-text');
      setInterval(() => {
        const isConnected = Math.random() > 0.05; // 95% 接続状態
        if (isConnected) {
          connectionDot.classList.remove('disconnected');
          connectionText.textContent = 'connected';
        } else {
          connectionDot.classList.add('disconnected');
          connectionText.textContent = 'disconnected';
        }
      }, 10_000);
    }

    // ---------------- Public API ----------------
    appendLog(logData) {
      if (this.emptyState) this.emptyState.style.display = 'none';

      const entry = document.createElement('div');
      entry.className = `log-entry ${logData.level}`;

      const timestamp = new Date(logData.timestamp).toLocaleTimeString('ja-JP', {
        hour12: false,
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
      });

      const levelText = logData.level === 'packet' ? 'pkt' : logData.level;

      entry.innerHTML = `
        <span class="log-timestamp">${timestamp}</span>
        <span class="log-level ${logData.level}">${levelText}</span>
        <span class="log-message">${logData.message}</span>
        ${logData.details ? this.createMetaHTML(logData.details) : ''}
      `;

      this.logEntries.appendChild(entry);

      if (this.autoScroll) this.logEntries.scrollTop = this.logEntries.scrollHeight;

      // Keep latest 100
      const entries = this.logEntries.querySelectorAll('.log-entry');
      if (entries.length > 100) entries[0].remove();
    }

    createMetaHTML(details) {
      const items = [];
      if (details.endpoint) {
        items.push(`<span class="log-meta-item"><span class="log-meta-label">endpoint:</span><span class="log-meta-value">${details.endpoint}</span></span>`);
      }
      if (details.status_code !== undefined) {
        const cls = this.getStatusClass(details.status_code);
        items.push(`<span class="log-meta-item ${cls}"><span class="log-meta-label">status:</span><span class="log-meta-value">${details.status_code}</span></span>`);
      }
      if (details.response_time !== undefined) {
        const cls = this.getResponseClass(details.response_time);
        items.push(`<span class="log-meta-item ${cls}"><span class="log-meta-label">time:</span><span class="log-meta-value">${details.response_time}ms</span></span>`);
      }
      if (details.ip) {
        items.push(`<span class="log-meta-item"><span class="log-meta-label">ip:</span><span class="log-meta-value">${details.ip}</span></span>`);
      }
      if (details.coords) {
        items.push(`<span class="log-meta-item"><span class="log-meta-label">coords:</span><span class="log-meta-value">${details.coords}</span></span>`);
      }
      if (details.area_code) {
        items.push(`<span class="log-meta-item"><span class="log-meta-label">area:</span><span class="log-meta-value">${details.area_code}</span></span>`);
      }
      if (details.flags) {
        items.push(`<span class="log-meta-item"><span class="log-meta-label">flags:</span><span class="log-meta-value">${details.flags}</span></span>`);
      }
      return items.length ? `<div class="log-meta">${items.join('')}</div>` : '';
    }

    getStatusClass(code) {
      if (code >= 200 && code < 300) return 'status-200';
      if (code >= 300 && code < 400) return 'status-300';
      if (code >= 400 && code < 500) return 'status-400';
      if (code >= 500) return 'status-500';
      return '';
    }

    getResponseClass(ms) {
      if (ms < 200) return 'response-fast';
      if (ms < 1_000) return 'response-slow';
      return 'response-very-slow';
    }

    updateMetrics(total, avgMs, pktTotal, pktAvgMs) {
      document.getElementById('total-count').textContent = total;
      document.getElementById('avg-response').textContent = avgMs;
      document.getElementById('packet-count').textContent = pktTotal;
      document.getElementById('packet-avg-response').textContent = pktAvgMs;
    }

    clearLogs() {
      this.logEntries.innerHTML = '';
      // recreate empty state
      this.emptyState = document.createElement('div');
      this.emptyState.className = 'empty-state';
      this.emptyState.id = 'empty-state';
      this.emptyState.innerHTML = `<div class="empty-state-icon">📝</div><div>Waiting for logs...</div>`;
      this.logEntries.appendChild(this.emptyState);
    }

    toggleAutoScroll() {
      this.autoScroll = !this.autoScroll;
      document.getElementById('auto-scroll-text').textContent = this.autoScroll ? 'auto' : 'manual';
    }

    togglePanel() {
      const panel = document.getElementById('log-panel');
      panel.style.display = panel.style.display === 'none' ? 'flex' : 'none';
    }
  }

  // ---------- グローバルインスタンスと DEMO ----------
  const logPanel = new TerminalLogPanel();
  window.logPanel = logPanel;

  // HTML の onclick から呼ばれる関数を window に公開
  window.addDemoLog = function (level) {
    const messages = {
      info: ['Weather API request initiated', 'Cache lookup performed', 'User session validated'],
      success: ['Weather data retrieved successfully', 'Location coordinates resolved', 'API response processed'],
      warning: ['Rate limit threshold reached', 'Cache miss occurred', 'Slow response detected'],
      error: ['Weather API request failed', 'Database connection timeout', 'Invalid coordinates provided'],
      packet: ['WebSocket message received', 'Real-time data packet processed', 'Client connection established']
    };

    const endpoints = ['/api/weather', '/api/geocoding', '/api/forecast', '/ws'];
    const message = messages[level][Math.floor(Math.random() * messages[level].length)];
    const endpoint = endpoints[Math.floor(Math.random() * endpoints.length)];
    const responseTime = Math.floor(Math.random() * 1_500) + 50;

    let statusCode;
    if (level === 'success') statusCode = [200, 201, 204][Math.floor(Math.random() * 3)];
    else if (level === 'warning') statusCode = [429, 301, 302][Math.floor(Math.random() * 3)];
    else if (level === 'error') statusCode = [400, 404, 500, 502][Math.floor(Math.random() * 4)];
    else statusCode = 200;

    const logData = {
      type: 'log',
      timestamp: new Date().toISOString(),
      level: level,
      message: message,
      details: {
        endpoint: endpoint,
        response_time: responseTime,
        status_code: statusCode,
        ip: `192.168.1.${Math.floor(Math.random() * 255)}`
      }
    };

    logPanel.appendLog(logData);

    // metrics
    if (level === 'packet') {
      logPanel.packetCount++;
      logPanel.totalPacketTime += responseTime;
    } else {
      logPanel.logCount++;
      logPanel.totalResponseTime += responseTime;
    }

    logPanel.updateMetrics(
      logPanel.logCount,
      logPanel.logCount ? Math.floor(logPanel.totalResponseTime / logPanel.logCount) : 0,
      logPanel.packetCount,
      logPanel.packetCount ? Math.floor(logPanel.totalPacketTime / logPanel.packetCount) : 0
    );
  };

  window.clearLogs = () => logPanel.clearLogs();
  window.toggleAutoScroll = () => logPanel.toggleAutoScroll();
  window.togglePanel = () => logPanel.togglePanel();

  // 初期化メッセージ
  setTimeout(() => {
    logPanel.appendLog({
      type: 'log',
      timestamp: new Date().toISOString(),
      level: 'info',
      message: 'Weather monitoring system initialized',
      details: {
        endpoint: '/system/init',
        response_time: 45,
        status_code: 200,
        ip: '127.0.0.1'
      }
    });
  }, 500);
})();

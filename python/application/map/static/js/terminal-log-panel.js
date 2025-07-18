// terminal-log-panel.js (bulk-enabled)
// --------------------------------------------------
// ログパネル UI ロジック（単発ログ + bulkログ両対応）
//
// 使い方概要:
//   <script src="terminal-log-panel.js"></script>
//   const ws = new WebSocket("ws://.../ws");
//   ws.onmessage = (ev) => window.handleLogPayload(ev.data);
//
// サーバー側が bulk メッセージ ({type:"bulk",count:n,logs:[...JSON文字列...]}) を
// 1秒ごと等のレートで送信してくる想定。従来の単発 {type:"log",...} 形式とも両立。
// --------------------------------------------------

(() => {
  'use strict';

  /* ---------------------------------- Consts --------------------------------- */
  const MAX_LOG_ENTRIES = 100;   // 表示上の最大保持行数

  /* --------------------------- TerminalLogPanel ------------------------------ */
  class TerminalLogPanel {
    constructor() {
      this.logEntries = document.getElementById('log-entries');
      this.emptyState = document.getElementById('empty-state');
      this.autoScroll = true;
      this.logCount = 0;          // info/success/warning/error の累積件数
      this.totalResponseTime = 0; // 上記平均算出用
      this.packetCount = 0;       // packet ログ累積件数
      this.totalPacketTime = 0;   // packet 平均算出用
      this.receivedSinceLastMetrics = 0; // bulk 受信計数（任意用途）
      this.initializeEventListeners();
    }

    /* -------------------------- Initialise events -------------------------- */
    initializeEventListeners() {
      this.simulateConnection();
    }

    // Demo: fake connection status switching (UIデモ用)
    simulateConnection() {
      const connectionDot = document.getElementById('connection-dot');
      const connectionText = document.getElementById('connection-text');
      if (!connectionDot || !connectionText) return; // 要素が無い場合はスキップ
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

    /* ------------------------------ Public API ----------------------------- */

    /** 単発ログ 1 件を画面に追加。欠損フィールドは自動補完。 */
    appendLog(logData) {
      if (!this.logEntries) return;
      if (!logData || typeof logData !== 'object') return;

      // 防御的補完
      if (!logData.timestamp) logData.timestamp = new Date().toISOString();
      if (!logData.level) logData.level = 'info';
      if (!logData.message) logData.message = '';

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
        <span class="log-message">${this._escape(logData.message)}</span>
        ${logData.details ? this.createMetaHTML(logData.details) : ''}
      `;

      this.logEntries.appendChild(entry);

      if (this.autoScroll) {
        this.logEntries.scrollTop = this.logEntries.scrollHeight;
      }

      // 上限超過で最古を削除
      const entries = this.logEntries.querySelectorAll('.log-entry');
      if (entries.length > MAX_LOG_ENTRIES) entries[0].remove();

      // メトリクス簡易更新（任意）
      if (logData.level === 'packet') {
        this.packetCount++;
        if (logData.details?.response_time != null) {
          this.totalPacketTime += Number(logData.details.response_time) || 0;
        }
      } else {
        this.logCount++;
        if (logData.details?.response_time != null) {
          this.totalResponseTime += Number(logData.details.response_time) || 0;
        }
      }
      this._updateDerivedMetrics();
    }

    /** bulk 配信で届いた JSON文字列配列を展開して appendLog() する。 */
    appendBulk(rawLogs) {
      if (!Array.isArray(rawLogs) || rawLogs.length === 0) return;
      for (const raw of rawLogs) {
        try {
          const obj = JSON.parse(raw);
          // metrics → updateMetrics()
          if (obj && obj.type === 'metrics') {
            this.updateMetrics(
              obj.total ?? this.logCount,
              obj.avg_ms ?? Math.floor(this.totalResponseTime / Math.max(this.logCount, 1)),
              obj.packet_total ?? this.packetCount,
              obj.packet_avg_ms ?? Math.floor(this.totalPacketTime / Math.max(this.packetCount, 1))
            );
            continue;
          }
          // log or unknown → appendLog()
          this.appendLog(obj);
        } catch (_err) {
          // JSON parse失敗 → 生文字列扱い
          this.appendLog({
            type: 'log',
            timestamp: new Date().toISOString(),
            level: 'info',
            message: String(raw),
            details: { raw: true }
          });
        }
      }
    }

    /** metrics 数値を UI に反映。 */
    updateMetrics(total, avgMs, pktTotal, pktAvgMs) {
      const totalEl = document.getElementById('total-count');
      const avgEl = document.getElementById('avg-response');
      const pktCntEl = document.getElementById('packet-count');
      const pktAvgEl = document.getElementById('packet-avg-response');
      if (totalEl) totalEl.textContent = total;
      if (avgEl) avgEl.textContent = avgMs;
      if (pktCntEl) pktCntEl.textContent = pktTotal;
      if (pktAvgEl) pktAvgEl.textContent = pktAvgMs;
    }

    /** ログ表示を全部消して初期状態に戻す。 */
    clearLogs() {
      if (!this.logEntries) return;
      this.logEntries.innerHTML = '';
      // recreate empty state
      this.emptyState = document.createElement('div');
      this.emptyState.className = 'empty-state';
      this.emptyState.id = 'empty-state';
      this.emptyState.innerHTML = `\n        <div class="empty-state-icon">📝</div>\n        <div>Waiting for logs...</div>\n      `;
      this.logEntries.appendChild(this.emptyState);
      // countersリセット
      this.logCount = 0;
      this.totalResponseTime = 0;
      this.packetCount = 0;
      this.totalPacketTime = 0;
      this.receivedSinceLastMetrics = 0;
      this.updateMetrics(0, 0, 0, 0);
    }

    /** auto-scroll 切り替え */
    toggleAutoScroll() {
      this.autoScroll = !this.autoScroll;
      const el = document.getElementById('auto-scroll-text');
      if (el) el.textContent = this.autoScroll ? 'auto' : 'manual';
    }

    /** パネル開閉 */
    togglePanel() {
      const panel = document.getElementById('log-panel');
      if (!panel) return;
      panel.style.display = panel.style.display === 'none' ? 'flex' : 'none';
    }

    /* --------------------------- HTML helpers ------------------------------ */

    createMetaHTML(details) {
      const items = [];
      if (details.endpoint) {
        items.push(`<span class="log-meta-item"><span class="log-meta-label">endpoint:</span><span class="log-meta-value">${this._escape(details.endpoint)}</span></span>`);
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
        items.push(`<span class="log-meta-item"><span class="log-meta-label">ip:</span><span class="log-meta-value">${this._escape(details.ip)}</span></span>`);
      }
      if (details.coords) {
        items.push(`<span class="log-meta-item"><span class="log-meta-label">coords:</span><span class="log-meta-value">${this._escape(details.coords)}</span></span>`);
      }
      if (details.area_code) {
        items.push(`<span class="log-meta-item"><span class="log-meta-label">area:</span><span class="log-meta-value">${this._escape(details.area_code)}</span></span>`);
      }
      if (details.flags) {
        items.push(`<span class="log-meta-item"><span class="log-meta-label">flags:</span><span class="log-meta-value">${this._escape(details.flags)}</span></span>`);
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

    /* --------------------------- internal utils --------------------------- */

    _updateDerivedMetrics() {
      // 簡易平均（整数 ms）
      const avgMs = this.logCount ? Math.floor(this.totalResponseTime / this.logCount) : 0;
      const pktAvgMs = this.packetCount ? Math.floor(this.totalPacketTime / this.packetCount) : 0;
      this.updateMetrics(this.logCount, avgMs, this.packetCount, pktAvgMs);
    }

    _escape(str) {
      return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
    }
  }

  /* ---------------------- グローバルインスタンス公開 ----------------------- */
  const logPanel = new TerminalLogPanel();
  window.logPanel = logPanel;

  /* ---------------------- WebSocket payload ハンドラ ----------------------- */
  // ws.onmessage = (ev) => window.handleLogPayload(ev.data)
  window.handleLogPayload = function(raw) {
    let data = raw;
    if (typeof raw === 'string') {
      try {
        data = JSON.parse(raw);
      } catch (_err) {
        // プレーン文字列 → 単発ログ扱い
        logPanel.appendLog({
          type: 'log',
          timestamp: new Date().toISOString(),
          level: 'info',
          message: raw
        });
        return;
      }
    }

    if (!data || typeof data !== 'object') return;

    // bulk モード
    if (data.type === 'bulk' && Array.isArray(data.logs)) {
      logPanel.appendBulk(data.logs);
      return;
    }

    // metrics 単発
    if (data.type === 'metrics') {
      logPanel.updateMetrics(
        data.total ?? logPanel.logCount,
        data.avg_ms ?? 0,
        data.packet_total ?? logPanel.packetCount,
        data.packet_avg_ms ?? 0,
      );
      return;
    }

    // 通常ログ
    if (data.type === 'log' || data.level) {
      logPanel.appendLog(data);
      return;
    }

    // fallback
    logPanel.appendLog({
      type: 'log',
      timestamp: new Date().toISOString(),
      level: 'info',
      message: JSON.stringify(data)
    });
  };

  /* --------------------------- Demo helpers ------------------------------- */
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

    // metrics (Demo internal counters)
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

})();

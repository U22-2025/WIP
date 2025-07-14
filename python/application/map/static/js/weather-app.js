// weather_app.js – ログ機能を TerminalLogPanel に委譲したフルバージョン
// ----------------------------------------------------------------------
// 注意:
//   1. HTML 側で `terminal-log-panel.js` が先に読み込まれ、
//      `window.logPanel` が利用可能になっていること。
//   2. 本ファイルでは appendLog / updateMetrics を削除。
//      WebSocket からのログ・メトリクス出力は logPanel に直接送る。
//   3. そのほかの天気取得・地図・チャート機能は元実装を維持。

class WeatherApp {
  constructor() {
    this.map = null;
    this.currentMarker = null;

    // --- ステータス管理 ---
    this.weatherCodeMap = {};
    this.isWeatherCodeLoaded = false;
    this.errorCodeMap = {};
    this.isErrorCodeLoaded = false;
    this.currentTheme = 'default';

    // --- エフェクト / パーティクル ---
    this.particleManager = null;
    this.isLightningActive = false;

    // --- 現在位置・週間予報 ---
    this.currentLat = null;
    this.currentLng = null;
    this.isWeeklyForecastVisible = false;

    // --- チャート ---
    this.currentChart = null;
    this.currentChartType = 'temperature';
    this.weeklyDataForChart = null;

    // --- WebSocket ---
    this.ws = null;

    // ------------------------------------------------------------------
    // 天気アイコンマッピング
    //  （元コードをそのまま掲載 – 100〜450 台ほぼフル）
    // ------------------------------------------------------------------
    this.weatherIconMap = {
      /* 晴れ系（100番台） */
      '100': 'fas fa-sun','101': 'fas fa-cloud-sun','102': 'fas fa-cloud-sun-rain','103': 'fas fa-cloud-sun-rain','104': 'fas fa-cloud-snow','105': 'fas fa-cloud-snow','106': 'fas fa-cloud-snow','107': 'fas fa-cloud-snow','108': 'fas fa-cloud-bolt','110': 'fas fa-cloud-sun','111': 'fas fa-cloud-sun','112': 'fas fa-cloud-sun-rain','113': 'fas fa-cloud-sun-rain','114': 'fas fa-cloud-rain','115': 'fas fa-cloud-snow','116': 'fas fa-cloud-snow','117': 'fas fa-snowflake','118': 'fas fa-cloud-snow','119': 'fas fa-cloud-bolt','120': 'fas fa-cloud-sun-rain','121': 'fas fa-cloud-sun-rain','122': 'fas fa-cloud-sun-rain','123': 'fas fa-cloud-bolt','124': 'fas fa-cloud-snow','125': 'fas fa-cloud-bolt','126': 'fas fa-cloud-rain','127': 'fas fa-cloud-rain','128': 'fas fa-cloud-rain','129': 'fas fa-cloud-rain','130': 'fas fa-smog','131': 'fas fa-smog','132': 'fas fa-cloud-sun','140': 'fas fa-cloud-bolt','160': 'fas fa-cloud-snow','170': 'fas fa-cloud-snow','181': 'fas fa-cloud-snow',
      /* 曇り系（200番台） */
      '200': 'fas fa-cloud','201': 'fas fa-cloud-sun','202': 'fas fa-cloud-rain','203': 'fas fa-cloud-rain','204': 'fas fa-cloud-snow','205': 'fas fa-cloud-snow','206': 'fas fa-cloud-snow','207': 'fas fa-cloud-snow','208': 'fas fa-cloud-bolt','209': 'fas fa-smog','210': 'fas fa-cloud-sun','211': 'fas fa-cloud-sun','212': 'fas fa-cloud-rain','213': 'fas fa-cloud-rain','214': 'fas fa-cloud-rain','215': 'fas fa-cloud-snow','216': 'fas fa-cloud-snow','217': 'fas fa-snowflake','218': 'fas fa-cloud-snow','219': 'fas fa-cloud-bolt','220': 'fas fa-cloud-rain','221': 'fas fa-cloud-rain','222': 'fas fa-cloud-rain','223': 'fas fa-cloud-sun','224': 'fas fa-cloud-rain','225': 'fas fa-cloud-rain','226': 'fas fa-cloud-rain','227': 'fas fa-cloud-rain','228': 'fas fa-cloud-snow','229': 'fas fa-cloud-snow','230': 'fas fa-cloud-snow','231': 'fas fa-smog','240': 'fas fa-cloud-bolt','250': 'fas fa-cloud-bolt','260': 'fas fa-cloud-snow','270': 'fas fa-cloud-snow','281': 'fas fa-cloud-snow',
      /* 雨系（300番台） */
      '300': 'fas fa-cloud-rain','301': 'fas fa-cloud-sun-rain','302': 'fas fa-cloud-rain','303': 'fas fa-cloud-snow','304': 'fas fa-cloud-snow','306': 'fas fa-cloud-showers-heavy','307': 'fas fa-wind','308': 'fas fa-wind','309': 'fas fa-cloud-snow','311': 'fas fa-cloud-sun-rain','313': 'fas fa-cloud-rain','314': 'fas fa-cloud-snow','315': 'fas fa-snowflake','316': 'fas fa-cloud-sun','317': 'fas fa-cloud','320': 'fas fa-cloud-sun-rain','321': 'fas fa-cloud-rain','322': 'fas fa-cloud-snow','323': 'fas fa-cloud-sun','324': 'fas fa-cloud-sun','325': 'fas fa-cloud-sun','326': 'fas fa-cloud-snow','327': 'fas fa-cloud-snow','328': 'fas fa-cloud-showers-heavy','329': 'fas fa-cloud-snow','340': 'fas fa-cloud-snow','350': 'fas fa-cloud-bolt','361': 'fas fa-cloud-sun','371': 'fas fa-cloud',
      /* 雪系（400番台） */
      '400': 'fas fa-snowflake','401': 'fas fa-cloud-snow','402': 'fas fa-snowflake','403': 'fas fa-cloud-snow','405': 'fas fa-snowflake','406': 'fas fa-wind','407': 'fas fa-wind','409': 'fas fa-cloud-snow','411': 'fas fa-cloud-sun','413': 'fas fa-cloud','414': 'fas fa-cloud-rain','420': 'fas fa-cloud-sun','421': 'fas fa-cloud','422': 'fas fa-cloud-rain','423': 'fas fa-cloud-rain','424': 'fas fa-cloud-rain','425': 'fas fa-snowflake','426': 'fas fa-cloud-snow','427': 'fas fa-cloud-snow','450': 'fas fa-cloud-bolt'
    };

    // 天気アイコン用クラス名（簡易分類）
    this.weatherIconClassMap = {
      '100': 'sunny','101': 'sunny','110': 'sunny','111': 'sunny','132': 'sunny',
      '300': 'rainy','301': 'rainy','302': 'rainy','306': 'rainy','311': 'rainy','313': 'rainy','320': 'rainy','321': 'rainy','328': 'rainy',
      '307': 'windy','308': 'windy','406': 'windy','407': 'windy'
    };

    // 実行開始
    this.init();
  }

  // ------------------------------------------------------------------
  // 共通ユーティリティ
  // ------------------------------------------------------------------
  getErrorMessage(code) {
    if (this.isErrorCodeLoaded && code && this.errorCodeMap[String(code)]) {
      return this.errorCodeMap[String(code)];
    }
    return '不明なエラーが発生しました';
  }

  getCSSVariable(name) {
    const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
    const fallback = {
      '--chart-text-primary': '#2d3436',
      '--chart-text-secondary': '#636e72',
      '--chart-grid-color': 'rgba(182,190,195,0.3)'
    };
    return v || fallback[name] || '#2d3436';
  }

  // ------------------------------------------------------------------
  // 災害情報フォーマット
  // ------------------------------------------------------------------
  formatDisasterList(list) {
    if (!Array.isArray(list) || list.length === 0) return '';
    return list.map(item => {
      const [kind, time] = item.split('_');
      if (time) {
        return `<span class="disaster-item"><span class="kind">${kind}</span> <span class="time">(${time})</span></span>`;
      }
      return `<span class="disaster-item"><span class="kind">${kind}</span></span>`;
    }).join('<span class="disaster-sep">, </span>');
  }


  // 新しい災害情報解析
  parseDisasterInfo(disasterArray) {
    if (!disasterArray || disasterArray.length === 0) return [];
    const parsed = [];
    disasterArray.forEach(str => {
      const parts = str.split(',');
      parts.forEach(part => {
        const trimmed = part.trim();
        if (trimmed) {
        const range = trimmed.match(/(\d{4}[\/\-]\d{2}[\/\-]\d{2}[T\s]\d{2}:\d{2}(?::\d{2})?(?:[+\-]\d{2}:?\d{2})?)から(\d{4}[\/\-]\d{2}[\/\-]\d{2}[T\s]\d{2}:\d{2}(?::\d{2})?(?:[+\-]\d{2}:?\d{2})?)まで/);
          let type = trimmed;
          let timeRange = null;
          if (range) {
            type = trimmed.replace(range[0], '').replace(/_$/, '');
            timeRange = { start: range[1], end: range[2] };
          } else if (trimmed.includes('_')) {
            const idx = trimmed.indexOf('_');
            type = trimmed.slice(0, idx);
            const tPart = trimmed.slice(idx + 1);
            if (tPart) {
              timeRange = { start: tPart };
            }
          }
          let icon = 'fas fa-exclamation-circle';
          if (type.includes('降灰')) icon = 'fas fa-mountain';
          else if (type.includes('噴石')) icon = 'fas fa-exclamation-circle';
          else if (type.includes('津波')) icon = 'fas fa-water';
          else if (type.includes('地震')) icon = 'fas fa-house-crack';
          parsed.push({ type, icon, timeRange, original: trimmed });
        }
      });
    });
    return parsed;
  }

  formatDisasterTime(str) {
    if (!str) return '';
    try {
      const d = new Date(str);
      if (!isNaN(d)) {
        const y = d.getFullYear();
        const m = String(d.getMonth() + 1).padStart(2, '0');
        const day = String(d.getDate()).padStart(2, '0');
        const h = String(d.getHours()).padStart(2, '0');
        const min = String(d.getMinutes()).padStart(2, '0');
        return `${y}/${m}/${day} ${h}:${min}`;
      }
    } catch (e) {
      /* ignore */
    }
    return str.replace('T', ' ').replace('_', ' ');
  }

  generatePopupDisasterHTML(disasterArray) {
    const parsed = this.parseDisasterInfo(disasterArray);
    if (parsed.length === 0) return '';
    const items = parsed.map(d => {
      let time = '';
      if (d.timeRange) {
        if (d.timeRange.end) {
          time = `<div class="disaster-time">${this.formatDisasterTime(d.timeRange.start)} ~ ${this.formatDisasterTime(d.timeRange.end)}</div>`;
        } else if (d.timeRange.start) {
          time = `<div class="disaster-time">${this.formatDisasterTime(d.timeRange.start)}</div>`;
        }
      }
      return `<div class="disaster-item"><i class="${d.icon} disaster-item-icon"></i><div class="disaster-item-content"><div class="disaster-type">${d.type}</div>${time}</div></div>`;
    }).join('');
    return `<div class="disaster-alert" role="alert"><div class="disaster-header"><i class="fas fa-exclamation-triangle disaster-icon"></i><span>緊急災害情報</span></div><div class="disaster-items">${items}</div></div>`;
  }

  /* generateWeeklyDisasterHTML は不要になったため削除 */

  // ------------------------------------------------------------------
  // 初期化
  // ------------------------------------------------------------------
  async init() {
    console.log('WeatherApp 初期化開始');
    try {
      await this.loadWeatherCodes();
      await this.loadErrorCodes();
      this.particleManager = new ParticleSystemManager();
      await this.initializeMap();
      this.setupEventListeners();
      this.applyTimeTheme();
      this.initializeWebSocket();
      console.log('WeatherApp 初期化完了');
    } catch (err) {
      console.error('WeatherApp 初期化エラー:', err);
    }
  }

  // ------------------------------------------------------------------
  // API 設定ファイル読み込み
  // ------------------------------------------------------------------
  async loadWeatherCodes() {
    try {
      const res = await fetch('/static/json/weather_code.json');
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      this.weatherCodeMap = data.codes || {};
      this.isWeatherCodeLoaded = true;
    } catch (err) {
      console.error('天気コード読み込みエラー:', err);
      this.weatherCodeMap = { '100': '晴れ', '200': '曇り', '300': '雨', '400': '雪' };
      this.isWeatherCodeLoaded = true;
    }
  }

  async loadErrorCodes() {
    try {
      const res = await fetch('/static/json/error_code.json');
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      this.errorCodeMap = data.codes || {};
      this.isErrorCodeLoaded = true;
    } catch (err) {
      console.error('エラーコード読み込みエラー:', err);
      this.errorCodeMap = {};
      this.isErrorCodeLoaded = false;
    }
  }

  // ------------------------------------------------------------------
  // 地図
  // ------------------------------------------------------------------
  async initializeMap() {
    const japanBounds = L.latLngBounds([20, 122], [46, 154]);
    this.map = L.map('map', {
      zoomControl: true,
      attributionControl: true,
      maxBounds: japanBounds,
      maxBoundsViscosity: 1.0
    }).setView([35.6895, 139.6917], 6);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '© OpenStreetMap contributors',
      maxZoom: 18
    }).addTo(this.map);
    this.setupMapEvents();
  }

  setupMapEvents() {
    this.map.on('click', (e) => this.handleMapClick(e.latlng.lat, e.latlng.lng));
    if (window.innerWidth <= 768) {
      this.map.on('click', () => {
        setTimeout(() => {
          const sidebar = document.getElementById('sidebar');
          if (sidebar && sidebar.classList.contains('active')) sidebar.classList.remove('active');
        }, 100);
      });
    }
  }

  // ------------------------------------------------------------------
  // 地図クリック → API 呼び出し・UI 更新
  // ------------------------------------------------------------------
  async handleMapClick(lat, lng) {
    this.currentLat = lat;
    this.currentLng = lng;

    if (this.currentMarker) this.map.removeLayer(this.currentMarker);
    this.currentMarker = L.marker([lat, lng], {
      icon: L.divIcon({ className: 'custom-marker', html: '<div style="background: var(--primary-color); width: 24px; height: 24px; border-radius: 50%; border: 4px solid white; box-shadow: 0 4px 12px rgba(0,0,0,0.4);"></div>', iconSize: [24, 24], iconAnchor: [12, 12] })
    }).addTo(this.map);

    this.showLoading();
    try {
      const res = await fetch('/weekly_forecast', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ lat, lng })
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      if (data.status === 'ok' && data.weekly_forecast) {
        const array = Object.values(data.weekly_forecast).sort((a, b) => a.day_number - b.day_number);
        const today = array[0];
        const current = {
          status: 'ok',
          weather: {
            weather_code: today.weather_code,
            temperature: today.temperature,
            precipitation_prob: today.precipitation_prob,
            visibility: today.visibility || '--',
            wind_speed: today.wind_speed || '--',
            pressure: today.pressure || '--',
            humidity: today.humidity || '--',
            uv_index: today.uv_index || '--'
          },
          disaster: today.disaster || []
        };
        this.displayWeatherInfo(current, lat, lng);
        if (this.currentMarker) this.currentMarker.bindPopup(this.createPopupContent(current, lat, lng)).openPopup();
        this.weeklyDataForChart = array;
        this.showWeeklyForecast();
        if (this.isWeeklyForecastVisible) this.displayWeeklyForecastData(array);
      } else if (data.status === 'error') {
        this.handleAPIError(lat, lng, data.error_code);
      } else {
        throw new Error('無効な週間予報レスポンス');
      }
    } catch (err) {
      console.error('週間予報取得エラー:', err);
      this.handleAPIError(lat, lng);
    } finally {
      this.hideLoading();
    }
  }

  // ------------------------------------------------------------------
  // API エラー / UI
  // ------------------------------------------------------------------
  handleAPIError(lat, lng, errorCode = null) {
    const msg = this.getErrorMessage(errorCode);
    const noData = document.getElementById('no-data');
    if (noData) {
      noData.innerHTML = `<i class="fas fa-exclamation-triangle"></i><p>${msg}</p>`;
      noData.style.display = 'block';
    }
    const wc = document.getElementById('weather-content');
    if (wc) wc.style.display = 'none';
    this.hideWeeklyForecast();
    const weekly = document.getElementById('weekly-data');
    if (weekly) weekly.innerHTML = '';
    this.weeklyDataForChart = null;
    const dummy = { status: 'ok', weather: { weather_code: '100', temperature: '--', precipitation_prob: '--' }, disaster: [] };
    if (this.currentMarker) this.currentMarker.bindPopup(this.createPopupContent(dummy, lat, lng)).openPopup();
  }

  // ------------------------------------------------------------------
  // 現在の天気 → UI
  // ------------------------------------------------------------------
  displayWeatherInfo(data, lat, lng) {
    document.getElementById('no-data').style.display = 'none';
    document.getElementById('weather-content').style.display = 'block';
    let code = '100';
    if (data.weather && data.weather.weather_code !== undefined && data.weather.weather_code !== null) {
      code = String(data.weather.weather_code);
    }
    const wt = this.getWeatherTheme(code);
    const tt = this.getTimeTheme();
    this.applyTheme(wt, tt);
    this.startWeatherEffects(code);
  }

  updateDetailItem(id, value) {
    const el = document.getElementById(id);
    if (el) el.textContent = value;
  }

  createPopupContent(data, lat, lng) {
    let code = '100', temp = '--', precip = '--';
    if (data.weather) {
      if (data.weather.weather_code !== undefined) code = String(data.weather.weather_code);
      if (data.weather.temperature !== undefined) temp = data.weather.temperature;
      if (data.weather.precipitation_prob !== undefined && data.weather.precipitation_prob !== null) precip = data.weather.precipitation_prob;
    }
    const disaster = this.generatePopupDisasterHTML(data.disaster);
    const iconClass = this.weatherIconMap[code] || 'fas fa-sun';
    const name = this.weatherCodeMap[code] || '天気情報不明';
    return `<div class="popup-content"><div class="popup-weather-icon"><i class="${iconClass}"></i></div><div class="popup-description">${name}</div><div class="popup-weather-data"><div class="popup-temp-container"><div class="popup-temp">${temp !== '--' ? temp + '°C' : '--°C'}</div><div class="popup-temp-label">気温</div></div><div class="popup-precipitation_prob-container"><div class="popup-precipitation_prob">${precip !== '--' ? precip + '%' : '--'}</div><div class="popup-precipitation_prob-label">降水確率</div></div></div>${disaster}<div class="popup-coords">緯度: ${lat.toFixed(4)}, 経度: ${lng.toFixed(4)}</div></div>`;
  }

  // ------------------------------------------------------------------
  // テーマ / エフェクト
  // ------------------------------------------------------------------
  getWeatherTheme(code) {
    code = String(code);
    const first = code.charAt(0);
    if (code.match(/08|19|23|25|40|50/)) return 'stormy';
    if (first === '4' || code.match(/04|15|16|17|18/)) return 'snowy';
    if (first === '3' || code.match(/02|12|13|14/)) return 'rainy';
    if (first === '2' || code.match(/01|11/)) return 'cloudy';
    return 'sunny';
  }

  getTimeTheme() {
    const h = new Date().getHours();
    if (h >= 6 && h < 10) return 'morning';
    if (h >= 10 && h < 16) return 'noon';
    if (h >= 16 && h < 19) return 'evening';
    return 'night';
  }

  applyTheme(wTheme, tTheme) {
    const b = document.body;
    b.classList.remove('theme-sunny', 'theme-cloudy', 'theme-rainy', 'theme-snowy', 'theme-stormy');
    b.classList.remove('time-morning', 'time-noon', 'time-evening', 'time-night');
    if (wTheme !== 'default') b.classList.add('theme-' + wTheme);
    b.classList.add('time-' + tTheme);
    this.currentTheme = wTheme;
  }

  applyTimeTheme() {
    const tTheme = this.getTimeTheme();
    const b = document.body;
    b.classList.remove('time-morning', 'time-noon', 'time-evening', 'time-night');
    b.classList.add('time-' + tTheme);
  }

  // パーティクル & 雷
  startWeatherEffects(code) {
    code = String(code);
    this.particleManager.stopEffect();
    const lightning = document.getElementById('lightning-effect');
    if (lightning) lightning.style.display = 'none';
    this.isLightningActive = false;
    if (code.match(/08|19|23|25|40|50/)) {
      this.startLightningEffect();
      this.particleManager.startEffect('rain');
    } else if (code.charAt(0) === '4' || code.match(/04|15|16|17|18/)) {
      this.particleManager.startEffect('snow');
    } else if (code.charAt(0) === '3' || code.match(/02|12|13|14/)) {
      this.particleManager.startEffect('rain');
    } else if (code.match(/07|06/)) {
      this.particleManager.startEffect('wind');
    }
  }

  startLightningEffect() {
    if (this.isLightningActive) return;
    this.isLightningActive = true;
    const el = document.getElementById('lightning-effect');
    if (el) {
      el.style.display = 'block';
      setTimeout(() => { if (el) el.style.display = 'none'; this.isLightningActive = false; }, 4000);
    }
  }

  // ------------------------------------------------------------------
  // 各種イベント
  // ------------------------------------------------------------------
  setupEventListeners() {
    const hideWeeklyBtn = document.getElementById('hide-weekly-btn');
    if (hideWeeklyBtn) hideWeeklyBtn.addEventListener('click', () => this.hideWeeklyForecast());


    window.addEventListener('resize', () => { if (this.map) this.map.invalidateSize(); });

    const tabSwitch = document.getElementById('viewSwitch');
    if (tabSwitch) tabSwitch.addEventListener('change', (e) => this.switchTab(e.target.checked ? 'chart' : 'list'));

    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        const sb = document.getElementById('sidebar');
        if (sb && sb.classList.contains('active')) sb.classList.remove('active');
        const wf = document.getElementById('weekly-forecast');
        if (wf && wf.style.display !== 'none') this.hideWeeklyForecast();
      }
    });
  }

  toggleSidebar() {
    const sb = document.getElementById('sidebar');
    if (sb) sb.classList.toggle('active');
  }

  // モバイル: 週間予報切り替え
  showWeeklyForecastMobile() {
    const panel = document.getElementById('log-panel');
    const sb = document.getElementById('sidebar');
    const wf = document.getElementById('weekly-forecast');
    if (!wf) return;
    const wfVisible = wf.style.display !== 'none';

    if (wfVisible) {
      this.hideWeeklyForecast();
      return;
    }

    if (panel && panel.style.display !== 'none' && window.getComputedStyle(panel).display !== 'none') {
      panel.style.display = 'none';
    }

    if (sb && !sb.classList.contains('active')) sb.classList.add('active');

    this.showWeeklyForecast();
  }

  // モバイル: ログパネル切り替え
  toggleLogPanelMobile() {
    const panel = document.getElementById('log-panel');
    const wf = document.getElementById('weekly-forecast');
    if (!panel) return;

    const panelVisible = panel.style.display !== 'none' && window.getComputedStyle(panel).display !== 'none';

    if (panelVisible) {
      panel.style.display = 'none';
      if (wf && wf.style.display !== 'none') this.hideWeeklyForecast();
      return;
    }

    if (wf && wf.style.display !== 'none') this.hideWeeklyForecast();
    panel.style.display = 'flex';
  }

  showLoading() { const lo = document.getElementById('loading-overlay'); if (lo) lo.style.display = 'flex'; }
  hideLoading() { const lo = document.getElementById('loading-overlay'); if (lo) lo.style.display = 'none'; }

  // ------------------------------------------------------------------
  // 週間予報 (取得 & UI)
  // ------------------------------------------------------------------
  showWeeklyForecast() {
    const wf = document.getElementById('weekly-forecast');
    const wl = document.getElementById('weekly-loading');
    if (!wf || !wl) return;
    wf.style.display = 'block';
    this.isWeeklyForecastVisible = true;
    if (this.weeklyDataForChart) {
      this.displayWeeklyForecastData(this.weeklyDataForChart);
    } else {
      wl.style.display = 'flex';
    }
  }

  hideWeeklyForecast() {
    const wf = document.getElementById('weekly-forecast');
    if (wf) wf.style.display = 'none';
    this.isWeeklyForecastVisible = false;
  }

  displayWeeklyForecastData(array) {
    const wf = document.getElementById('weekly-forecast');
    const wd = document.getElementById('weekly-data');
    const wl = document.getElementById('weekly-loading');
    if (!wf || !wd) return;
    wf.style.display = 'block';
    this.isWeeklyForecastVisible = true;
    if (wl) wl.style.display = 'none';
    this.weeklyDataForChart = array;
    const dayNames = { Monday:'月',Tuesday:'火',Wednesday:'水',Thursday:'木',Friday:'金',Saturday:'土',Sunday:'日' };
    let html = '';
    array.forEach((d, i) => {
      const code = d.weather_code ? String(d.weather_code) : '100';
      const icon = this.weatherIconMap[code] || 'fas fa-sun';
      const date = new Date(d.date);
      const dayName = dayNames[d.day_of_week] || d.day_of_week.slice(0,1);
      const dateStr = `${date.getMonth()+1}/${date.getDate()}`;
      html += `<div class="${i===0?'weekly-day today':'weekly-day'}"><div class="day-info"><div class="day-name">${i===0?'今日':dayName}</div><div class="day-date">${dateStr}</div></div><div class="day-weather"><i class="${icon}"></i></div><div class="day-temp">${(d.temperature!==undefined&&d.temperature!=='--')?d.temperature+'°C':'--°C'}</div><div class="day-precipitation_prob"><i class="fas fa-umbrella"></i>${(d.precipitation_prob!==undefined&&d.precipitation_prob!=='--'&&d.precipitation_prob!==null)?d.precipitation_prob+'%':'--'}</div></div>`;
    });
    wd.innerHTML = html;
    wd.style.display = 'block';
  }

  // ------------------------------------------------------------------
  // タブ & チャート
  // ------------------------------------------------------------------
  switchTab(tab) {
    document.querySelectorAll('.tab-btn').forEach(btn => { btn.classList.toggle('active', btn.dataset.tab === tab); });
    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
    const tgt = document.getElementById(`weekly-${tab}-view`);
    if (tgt) tgt.classList.add('active');
    if (tab === 'chart' && this.weeklyDataForChart) setTimeout(()=>this.drawChart('combined'),100);
  }

  switchChartType(type) {
    this.currentChartType = type;
    document.querySelectorAll('.chart-tab-btn').forEach(btn => btn.classList.toggle('active', btn.dataset.chart === type));
    if (this.weeklyDataForChart) this.drawChart(type);
  }

  drawChart(type) {
    if (!this.weeklyDataForChart || typeof Chart === 'undefined') return;
    const canvas = document.getElementById('weather-chart');
    if (!canvas) return;
    if (this.currentChart) this.currentChart.destroy();
    const ctx = canvas.getContext('2d');
    const labels = this.weeklyDataForChart.map((d,i)=> i===0? '今日' : `${new Date(d.date).getMonth()+1}/${new Date(d.date).getDate()}`);
    const temps = this.weeklyDataForChart.map(d=> d.temperature!==undefined&&d.temperature!=='--'? parseFloat(d.temperature):null);
    const precs = this.weeklyDataForChart.map(d=> d.precipitation_prob!==undefined&&d.precipitation_prob!=='--'&&d.precipitation_prob!==null? parseFloat(d.precipitation_prob):0);
    const common = {
      responsive:true,maintainAspectRatio:false,
      plugins:{ legend:{display:true,position:'top',labels:{font:{family:"'SF Pro Display',-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif",size:12},usePointStyle:true,padding:15,color:'#2d3436'}},tooltip:{mode:'index',intersect:false,backgroundColor:'rgba(255,255,255,0.95)',titleColor:'#2d3436',bodyColor:'#636e72',borderColor:'rgba(102,126,234,0.2)',borderWidth:1,cornerRadius:8,displayColors:true}},
      scales:{ x:{grid:{display:false},ticks:{font:{family:"'SF Pro Display',-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif",size:11},color:'#636e72'}}, y:{grid:{color:'rgba(182,190,195,0.3)',lineWidth:1},ticks:{font:{family:"'SF Pro Display',-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif",size:11},color:'#636e72'}} }
    };
    let cfg;
    if (type==='temperature') {
      cfg = { type:'line', data:{ labels, datasets:[{ label:'気温 (°C)', data:temps, borderColor:'#667eea', backgroundColor:'rgba(102,126,234,0.1)', borderWidth:3, fill:true, tension:0.4, pointBackgroundColor:'#667eea', pointBorderColor:'#ffffff', pointBorderWidth:2, pointRadius:6, pointHoverRadius:8 }] }, options:{ ...common, scales:{ ...common.scales, y:{ ...common.scales.y, title:{ display:true,text:'気温 (°C)',font:{family:"'SF Pro Display'",size:12},color:this.getCSSVariable('--chart-text-secondary') } } } } };
    } else if (type==='precipitation_prob') {
      cfg = { type:'bar', data:{ labels, datasets:[{ label:'降水確率 (%)', data:precs, backgroundColor:precs.map(v=> v>=70?'rgba(231,76,60,0.8)':v>=50?'rgba(230,126,34,0.8)':v>=30?'rgba(241,196,15,0.8)':'rgba(52,152,219,0.8)'), borderColor:precs.map(v=> v>=70?'#e74c3c':v>=50?'#e67e22':v>=30?'#f1c40f':'#3498db'), borderWidth:2, borderRadius:4, borderSkipped:false }] }, options:{ ...common, scales:{ ...common.scales, y:{ ...common.scales.y, min:0,max:100,title:{ display:true,text:'降水確率 (%)',font:{family:"'SF Pro Display'",size:12},color:this.getCSSVariable('--chart-text-secondary') } } } } };
    } else { // combined
      cfg = { type:'line', data:{ labels, datasets:[{ label:'気温 (°C)', data:temps, borderColor:'#667eea', backgroundColor:'rgba(102,126,234,0.1)', borderWidth:3, fill:false, tension:0.4, pointBackgroundColor:'#667eea', pointBorderColor:'#ffffff', pointBorderWidth:2, pointRadius:6, pointHoverRadius:8, yAxisID:'y' },{ label:'降水確率 (%)', data:precs, type:'bar', backgroundColor:'rgba(79,172,254,0.6)', borderColor:'#4facfe', borderWidth:1, borderRadius:3, yAxisID:'y1' }] }, options:{ ...common, scales:{ x:common.scales.x, y:{ ...common.scales.y, position:'left', title:{ display:true,text:'気温 (°C)',font:{family:"'SF Pro Display'",size:12},color:this.getCSSVariable('--chart-text-secondary') } }, y1:{ ...common.scales.y, position:'right', min:0,max:100, title:{ display:true,text:'降水確率 (%)',font:{family:"'SF Pro Display'",size:12},color:this.getCSSVariable('--chart-text-secondary') }, grid:{ drawOnChartArea:false } } } } };
    }
    try { this.currentChart = new Chart(ctx, cfg); } catch (err) { console.error('グラフ描画エラー:', err); }
  }

  displayWeeklyForecast(array) {
    const wd = document.getElementById('weekly-data');
    if (!wd) return;
    const dayNames = { Monday:'月',Tuesday:'火',Wednesday:'水',Thursday:'木',Friday:'金',Saturday:'土',Sunday:'日' };
    let html='';
    array.forEach((d,i)=>{
      const code = d.weather_code? String(d.weather_code):'100';
      const icon = this.weatherIconMap[code] || 'fas fa-sun';
      const date = new Date(d.date);
      const dayName = dayNames[d.day_of_week] || d.day_of_week.slice(0,1);
      const dateStr = `${date.getMonth()+1}/${date.getDate()}`;
    html += `<div class="${i===0?'weekly-day today':'weekly-day'}"><div class="day-info"><div class="day-name">${i===0?'今日':dayName}</div><div class="day-date">${dateStr}</div></div><div class="day-weather"><i class="${icon}"></i></div><div class="day-temp">${(d.temperature!==undefined&&d.temperature!=='--')?d.temperature+'°C':'--°C'}</div><div class="day-precipitation_prob"><i class="fas fa-umbrella"></i>${(d.precipitation_prob!==undefined&&d.precipitation_prob!=='--'&&d.precipitation_prob!==null)?d.precipitation_prob+'%':'--'}</div></div>`;
    });
    wd.innerHTML = html;
    wd.style.display = 'block';
  }

  handleWeeklyForecastError(code=null) {
    const wd = document.getElementById('weekly-data');
    if (!wd) return;
    const msg = this.getErrorMessage(code);
    wd.innerHTML = `<div class="weekly-error"><div style="text-align:center;padding:20px;color:var(--text-secondary);"><i class="fas fa-exclamation-triangle" style="font-size:24px;margin-bottom:10px;"></i><div>${msg}</div><div style="font-size:12px;margin-top:5px;">しばらく時間をおいて再度お試しください</div></div></div>`;
    wd.style.display = 'block';
    this.weeklyDataForChart = null;
  }

  // ------------------------------------------------------------------
  // WebSocket – logPanel 連携
  // ------------------------------------------------------------------
  initializeWebSocket() {
    const connect = () => {
      const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
      this.ws = new WebSocket(`${proto}//${location.host}/ws`);
      const lp = window.logPanel;
      this.ws.onopen = () => lp.appendLog({ type: 'log', timestamp: Date.now(), level: 'success', message: 'WebSocket 接続完了' });
      this.ws.onmessage = (e) => {
        try {
          const data = JSON.parse(e.data);
          if (data.type === 'metrics') {
            lp.updateMetrics(data.total, data.avg_ms, data.packet_total, data.packet_avg_ms);
          } else if (data.type === 'log') {
            lp.appendLog(data);
          }
        } catch {
          lp.appendLog({ type: 'log', timestamp: Date.now(), level: 'warning', message: e.data });
        }
      };
      this.ws.onclose = () => { lp.appendLog({ type: 'log', timestamp: Date.now(), level: 'warning', message: 'WebSocket 切断 - 再接続します' }); setTimeout(connect, 3000); };
      this.ws.onerror = (e) => console.error('WebSocket エラー:', e);
    };
    connect();
  }
}

// ----------------------------------------------------------------------
// ParticleSystemManager – 変更なし
// ----------------------------------------------------------------------
class ParticleSystemManager {
  constructor() {
    this.particles = [];
    this.container = document.getElementById('particle-system');
    this.maxParticles = 50;
    this.intervalId = null;
  }
  createParticle(type) {
    if (!this.container || this.particles.length >= this.maxParticles) return;
    const p = document.createElement('div');
    const w = window.innerWidth, h = window.innerHeight;
    switch (type) {
      case 'rain':
        p.className = 'rain-particle';
        p.style.left = Math.random()*(w+100)-50+'px';
        p.style.top = '-20px';
        p.style.animationDuration = (Math.random()*0.5+0.5)+'s';
        break;
      case 'snow':
        p.className = 'snow-particle';
        p.style.left = Math.random()*(w+100)-50+'px';
        p.style.top = '-20px';
        p.style.animationDuration = (Math.random()*2+2)+'s';
        break;
      case 'wind':
        p.className = 'wind-particle';
        p.style.left = '-50px';
        p.style.top = Math.random()*h+'px';
        p.style.animationDuration = (Math.random()*1+1)+'s';
        break;
    }
    this.container.appendChild(p);
    this.particles.push(p);
    p.addEventListener('animationend',()=>this.removeParticle(p));
  }
  removeParticle(p){
    const i = this.particles.indexOf(p);
    if(i>-1){this.particles.splice(i,1);if(p.parentNode)p.parentNode.removeChild(p);} }
  startEffect(type){
    this.stopEffect();
    const intv = type==='rain'?100:type==='snow'?200:type==='wind'?300:null;
    if(!intv) return;
    this.intervalId = setInterval(()=>this.createParticle(type), intv);
  }
  stopEffect(){
    if(this.intervalId){clearInterval(this.intervalId);this.intervalId=null;}
    this.particles.forEach(p=>{if(p.parentNode)p.parentNode.removeChild(p);});
    this.particles=[];
  }
}

// ----------------------------------------------------------------------
// グローバル関数 & 初期化
// ----------------------------------------------------------------------
window.toggleSidebar = function(){ const sb=document.getElementById('sidebar'); if(sb) sb.classList.toggle('active'); };

let weatherApp;
document.addEventListener('DOMContentLoaded',()=>{ 
  console.log('DOM loaded – WeatherApp init'); 
  weatherApp = new WeatherApp();
  document.addEventListener('wheel', e=>{ if(e.ctrlKey) e.preventDefault(); }, { passive:false });
  document.addEventListener('keydown', e=>{ if(e.ctrlKey && ['+','-','=','0'].includes(e.key)) e.preventDefault(); });
  document.addEventListener('touchstart', e=>{ if(e.touches && e.touches.length>1) e.preventDefault(); }, { passive:false });
});
window.addEventListener('load',()=>{ if(!weatherApp){ console.log('window load – WeatherApp re-init'); weatherApp = new WeatherApp(); } });

if(typeof module!=='undefined' && module.exports){ module.exports = { WeatherApp, ParticleSystemManager }; }

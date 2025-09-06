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
    this.landmarkMarker = null;
    this.landmarkLayer = null; // 複数ランドマーク表示用レイヤー
    this.autoFitLandmarks = false; // ピン表示時の自動ズーム調整を無効化（必要なら true に）
    this.maxLandmarkPins = 100; // 一度に描画するピン数の上限（応答性優先）
    this.lastClickToken = 0; // 競合防止用トークン
    this.weatherAbortCtl = null; // /weekly_forecast の中断用
    this.currentAbortCtl = null; // /current_weather の中断用
    this.pinRenderTimers = []; // ピン分割描画のタイマー保持

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
    this.lastLandmarks = null; // 直近のランドマークデータを保持

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

  // シンプルなデバウンス
  _debounce(fn, delay = 200) {
    let t = null;
    return (...args) => {
      if (t) clearTimeout(t);
      t = setTimeout(() => fn.apply(this, args), delay);
    };
  }

  // ------------------------------------------------------------------
  // 共通ユーティリティ
  // ------------------------------------------------------------------
  getErrorMessage(code) {
    if (this.isErrorCodeLoaded && code) {
      const codeStr = String(code);
      // 各カテゴリーから検索
      const allErrors = { 
        ...this.errorCodeMap.client_errors, 
        ...this.errorCodeMap.connection_errors, 
        ...this.errorCodeMap.server_errors 
      };
      if (allErrors[codeStr]) {
        return allErrors[codeStr].message;
      }
    }
    return '不明なエラーが発生しました';
  }

  getErrorDetails(code) {
    if (this.isErrorCodeLoaded && code) {
      const codeStr = String(code);
      // 各カテゴリーから検索
      const allErrors = { 
        ...this.errorCodeMap.client_errors, 
        ...this.errorCodeMap.connection_errors, 
        ...this.errorCodeMap.server_errors 
      };
      if (allErrors[codeStr]) {
        return {
          message: allErrors[codeStr].message,
          description: allErrors[codeStr].description,
          serverType: allErrors[codeStr].server_type,
          category: this.getErrorCategory(codeStr)
        };
      }
    }
    return null;
  }

  getErrorCategory(code) {
    if (!code) return null;
    const codeStr = String(code);
    if (this.errorCodeMap.client_errors && this.errorCodeMap.client_errors[codeStr]) {
      return 'client_error';
    }
    if (this.errorCodeMap.connection_errors && this.errorCodeMap.connection_errors[codeStr]) {
      return 'connection_error';
    }
    if (this.errorCodeMap.server_errors && this.errorCodeMap.server_errors[codeStr]) {
      return 'server_error';
    }
    return null;
  }

  getErrorCategoryInfo(category) {
    switch (category) {
      case 'client_error':
        return {
          categoryInfo: {
            name: 'クライアントエラー',
            description: 'リクエストに問題があります'
          },
          actionableInfo: {
            title: '対処方法',
            message: 'クライアント側で修正可能です。座標や入力データを確認してください。',
            icon: 'fas fa-tools',
            class: 'fixable'
          }
        };
      case 'connection_error':
        return {
          categoryInfo: {
            name: '接続エラー',
            description: 'サーバーとの接続に問題があります'
          },
          actionableInfo: {
            title: '対処方法',
            message: 'サーバー側の問題です。しばらく時間をおいて再度お試しください。',
            icon: 'fas fa-clock',
            class: 'wait'
          }
        };
      case 'server_error':
        return {
          categoryInfo: {
            name: 'サーバーエラー',
            description: 'サーバー内部で問題が発生しました'
          },
          actionableInfo: {
            title: '対処方法',
            message: 'サーバー側の問題です。システム管理者にお問い合わせください。',
            icon: 'fas fa-phone-alt',
            class: 'contact'
          }
        };
      default:
        return {
          categoryInfo: {
            name: '不明なエラー',
            description: 'エラーの詳細が不明です'
          },
          actionableInfo: {
            title: '対処方法',
            message: 'しばらく時間をおいて再度お試しください。',
            icon: 'fas fa-question',
            class: 'unknown'
          }
        };
    }
  }

  getErrorIcon(category) {
    switch (category) {
      case 'client_error':
        return 'fas fa-user-times';
      case 'connection_error':
        return 'fas fa-wifi';
      case 'server_error':
        return 'fas fa-server';
      default:
        return 'fas fa-question-circle';
    }
  }

  getServerTypeName(serverType) {
    switch (serverType) {
      case 'location_server':
        return '位置情報サーバー';
      case 'query_server':
        return 'クエリサーバー';
      case 'weather_server':
        return '気象サーバー';
      default:
        return serverType;
    }
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
  // 風データ処理
  // ------------------------------------------------------------------
  parseWindDirection(windText) {
    if (!windText || windText === '--' || windText === null) return null;
    
    // 風向きマッピング（度数）
    const directionMap = {
      '北': 0, '北北東': 22.5, '北東': 45, '東北東': 67.5,
      '東': 90, '東南東': 112.5, '南東': 135, '南南東': 157.5,
      '南': 180, '南南西': 202.5, '南西': 225, '西南西': 247.5,
      '西': 270, '西北西': 292.5, '北西': 315, '北北西': 337.5
    };
    
    // 複数の風向きがある場合（"南の風　後　北の風"など）は最初の風向きを使用
    const firstDirection = windText.split(/[後時から]/)[0].trim();
    
    // 風向きを抽出
    for (const [direction, angle] of Object.entries(directionMap)) {
      if (firstDirection.includes(direction)) {
        return angle;
      }
    }
    
    return null;
  }

  extractWindSpeed(windText) {
    if (!windText || windText === '--' || windText === null) return null;
    
    // 数値（アラビア数字）を優先的に抽出（単位と組み合わせの場合のみ）
    const numberMatch = windText.match(/(\d+(?:\.\d+)?)\s*(?:メートル|m\/s|m|メ|㍍)/i);
    if (numberMatch) {
      return numberMatch[1] + 'm/s';
    }
    
    // 漢数字を抽出（単位と組み合わせの場合のみ）
    const kanjiNumbers = {
      '一': 1, '二': 2, '三': 3, '四': 4, '五': 5, '六': 6, '七': 7, '八': 8, '九': 9, '十': 10,
      '１': 1, '２': 2, '３': 3, '４': 4, '５': 5, '６': 6, '７': 7, '８': 8, '９': 9
    };
    
    for (const [kanji, value] of Object.entries(kanjiNumbers)) {
      // 単位が必ず含まれている場合のみ数値として認識
      if (windText.includes(kanji) && (windText.includes('メートル') || windText.includes('m/s') || windText.includes('m'))) {
        // 地名（区、市、県など）の数字を除外
        const kanjiIndex = windText.indexOf(kanji);
        const afterKanji = windText.substring(kanjiIndex + 1, kanjiIndex + 3);
        if (afterKanji.includes('区') || afterKanji.includes('市') || afterKanji.includes('県') || afterKanji.includes('町')) {
          continue; // 地名の数字なのでスキップ
        }
        return value + 'm/s';
      }
    }
    
    // 数値が見つからない場合は強弱表現を抽出
    // より多くの強弱表現を網羅的にチェック
    const strengthPatterns = [
      { pattern: /やや強く/, text: 'やや強く' },
      { pattern: /強く/, text: '強く' },
      { pattern: /弱く/, text: '弱く' },
      { pattern: /非常に強く/, text: '非常に強く' },
      { pattern: /極めて強く/, text: '極めて強く' },
      { pattern: /猛烈に/, text: '猛烈' }
    ];
    
    for (const strength of strengthPatterns) {
      if (strength.pattern.test(windText)) {
        return strength.text;
      }
    }
    
    // 風速に関する数値的表現をチェック（単位なしでも）
    const speedPatterns = [
      { pattern: /秒速\s*(\d+(?:\.\d+)?)\s*メートル/, replacement: '$1m/s' },
      { pattern: /(\d+(?:\.\d+)?)\s*m\/s/, replacement: '$1m/s' },
      { pattern: /(\d+(?:\.\d+)?)\s*ノット/, replacement: (match, p1) => (parseFloat(p1) * 0.514).toFixed(1) + 'm/s' },
    ];
    
    for (const speed of speedPatterns) {
      const match = windText.match(speed.pattern);
      if (match) {
        if (typeof speed.replacement === 'function') {
          return speed.replacement(match[0], match[1]);
        } else {
          return windText.replace(speed.pattern, speed.replacement);
        }
      }
    }
    
    // デフォルトは空文字（風向きのみ表示）
    return '';
  }

  generateWindArrow(angle, strength = '弱') {
    if (angle === null) return '<span class="wind-no-data">--</span>';
    
    let strengthClass = 'wind-weak';
    
    // 数値の場合はm/sの値で色を決定
    if (strength && strength.includes('m/s')) {
      const speedValue = parseFloat(strength);
      if (speedValue >= 8) strengthClass = 'wind-strong';
      else if (speedValue >= 4) strengthClass = 'wind-medium';
      else strengthClass = 'wind-weak';
    } else {
      // 文字表現の場合
      const strengthMap = {
        '弱く': 'wind-weak',
        'やや強く': 'wind-medium', 
        '強く': 'wind-strong'
      };
      strengthClass = strengthMap[strength] || 'wind-weak';
    }
    
    return `<div class="wind-arrow ${strengthClass}" style="transform: rotate(${angle}deg)">
      <i class="fas fa-long-arrow-alt-up"></i>
    </div>`;
  }

  formatWindDisplay(windText) {
    const angle = this.parseWindDirection(windText);
    const strength = this.extractWindSpeed(windText);
    const arrow = this.generateWindArrow(angle, strength);
    
    if (angle === null) {
      return { arrow: arrow, text: windText || '--' };
    }
    
    // 簡潔な風向き表示
    const directionNames = {
      0: '北', 22.5: '北北東', 45: '北東', 67.5: '東北東',
      90: '東', 112.5: '東南東', 135: '南東', 157.5: '南南東',
      180: '南', 202.5: '南南西', 225: '南西', 247.5: '西南西',
      270: '西', 292.5: '西北西', 315: '北西', 337.5: '北北西'
    };
    
    const directionName = directionNames[angle] || '不明';
    
    // 数値がある場合は数値を優先表示、なければ強弱表現を表示
    let displayText = directionName;
    if (strength) {
      if (strength.includes('m/s')) {
        displayText = `${directionName} ${strength}`;
      } else if (strength !== '') {
        // ポップアップでは簡潔に表示
        const shortStrength = strength.replace('やや強く', '中').replace('強く', '強').replace('弱く', '弱');
        displayText = `${directionName}${shortStrength}`;
      }
    }
    
    return {
      arrow: arrow,
      text: displayText
    };
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

  generatePopupAlertHTML(alertArray) {
    if (!alertArray || alertArray.length === 0) return '';
    
    // 警報の種類別にグループ化して重複を除去
    const alertTypes = {};
    alertArray.forEach(alert => {
      const trimmed = alert.trim();
      if (trimmed) {
        alertTypes[trimmed] = (alertTypes[trimmed] || 0) + 1;
      }
    });

    if (Object.keys(alertTypes).length === 0) return '';

    // 警報の重要度でソート（警報 > 注意報）
    const sortedAlerts = Object.entries(alertTypes).sort(([a], [b]) => {
      const aIsWarning = a.includes('警報');
      const bIsWarning = b.includes('警報');
      if (aIsWarning && !bIsWarning) return -1;
      if (!aIsWarning && bIsWarning) return 1;
      return a.localeCompare(b);
    });

    // 表示数を制限（最大6個）
    const displayAlerts = sortedAlerts.slice(0, 6);
    const hiddenCount = sortedAlerts.length - displayAlerts.length;

    const items = displayAlerts.map(([alert, count]) => {
      const icon = alert.includes('警報') ? 'fas fa-exclamation-triangle' : 'fas fa-exclamation-circle';
      const countDisplay = count > 1 ? ` (×${count})` : '';
      return `<span class="alert-item"><i class="${icon} alert-item-icon"></i><span class="alert-text">${alert}${countDisplay}</span></span>`;
    }).join('');

    const hiddenText = hiddenCount > 0 ? `<span class="alert-hidden">他${hiddenCount}件</span>` : '';
    
    return `<div class="alert-warning" role="alert"><div class="alert-header"><i class="fas fa-triangle-exclamation alert-icon"></i><span>気象警報・注意報</span></div><div class="alert-items">${items}${hiddenText}</div></div>`;
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
      this.errorCodeMap = data || {};
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
    // クリックはデバウンスして無駄な連続リクエストを抑制
    const debounced = this._debounce((lat, lng) => this.handleMapClick(lat, lng), 200);
    this.map.on('click', (e) => debounced(e.latlng.lat, e.latlng.lng));
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
    const clickToken = Date.now();
    this.lastClickToken = clickToken;

    if (this.currentMarker) this.map.removeLayer(this.currentMarker);
    this.currentMarker = L.marker([lat, lng], {
      icon: L.divIcon({ className: 'custom-marker', html: '<div style="background: var(--primary-color); width: 24px; height: 24px; border-radius: 50%; border: 4px solid white; box-shadow: 0 4px 12px rgba(0,0,0,0.4);"></div>', iconSize: [24, 24], iconAnchor: [12, 12] }),
      zIndexOffset: 1000
    }).addTo(this.map);

    // 進行中のリクエストがあればキャンセル
    try { if (this.weatherAbortCtl) this.weatherAbortCtl.abort(); } catch(_) {}
    try { if (this.currentAbortCtl) this.currentAbortCtl.abort(); } catch(_) {}
    this.weatherAbortCtl = new AbortController();
    this.currentAbortCtl = new AbortController();

    this.showLoading();

    // 先に現在の天気を素早く取得して即表示（レスポンス改善）
    (async () => {
      try {
        const res = await fetch('/current_weather', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ lat, lng }),
          signal: this.currentAbortCtl.signal
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        if (this.lastClickToken !== clickToken) return; // 最新のみ反映
        if (data.status === 'ok' && data.today) {
          const t = data.today || {};
          const current = {
            status: 'ok',
            weather: {
              weather_code: t.weather_code,
              temperature: t.temperature,
              precipitation_prob: t.precipitation_prob,
              visibility: t.visibility || '--',
              wind_speed: t.wind_speed || '--',
              wind: t.wind || '--',
              pressure: t.pressure || '--',
              humidity: t.humidity || '--',
              uv_index: t.uv_index || '--'
            },
            disaster: t.disaster || [],
            alert: t.alert || []
          };
          this.displayWeatherInfo(current, lat, lng);
          if (this.currentMarker) this.currentMarker.bindPopup(this.createPopupContent(current, lat, lng)).openPopup();
          // 先にローディングを解除（週予報は後で更新）
          this.hideLoading();
        }
      } catch (err) {
        if (err && err.name === 'AbortError') {
          console.debug('current_weather aborted');
        } else {
          console.debug('current_weather error (fallback to weekly):', err);
        }
      }
    })();

    try {
      const res = await fetch('/weekly_forecast', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ lat, lng }),
        signal: this.weatherAbortCtl.signal
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
            wind: today.wind || '--',
            pressure: today.pressure || '--',
            humidity: today.humidity || '--',
            uv_index: today.uv_index || '--'
          },
          disaster: today.disaster || [],
          alert: today.alert || []
        };
        // 最新のクリックであれば UI 更新
        if (this.lastClickToken === clickToken) {
          this.displayWeatherInfo(current, lat, lng);
          if (this.currentMarker) this.currentMarker.bindPopup(this.createPopupContent(current, lat, lng)).openPopup();
          this.displayWeeklyForecastData(array);
          // 1リクエスト化: 受け取ったランドマークを描画・サイドバー反映
          if (Array.isArray(data.landmarks)) {
            this.lastLandmarks = { landmarks: data.landmarks, area_name: data.area_name };
            this.renderLandmarkPins(data.landmarks);
            const landmarksView = document.getElementById('landmarks-view');
            if (landmarksView && landmarksView.classList.contains('active')) {
              this.displayLandmarks(data.landmarks, data.area_name);
            }
          } else {
            this.lastLandmarks = null;
            this.clearLandmarkPins();
          }
        }
      } else if (data.status === 'error') {
        if (this.lastClickToken === clickToken) this.handleAPIError(lat, lng, data.error_code);
      } else {
        throw new Error('無効な週間予報レスポンス');
      }
    } catch (err) {
      if (err && err.name === 'AbortError') {
        // 最新クリックにより中断されたリクエスト。ログだけして抜ける
        console.debug('weekly_forecast aborted');
      } else {
        console.error('週間予報取得エラー:', err);
      }
      if (this.lastClickToken === clickToken) this.handleAPIError(lat, lng);
    } finally {
      if (this.lastClickToken === clickToken) this.hideLoading();
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
    const dummy = { status: 'ok', weather: { weather_code: '100', temperature: '--', precipitation_prob: '--' }, disaster: [], alert: [] };
    if (this.currentMarker) this.currentMarker.bindPopup(this.createErrorPopupContent(msg, errorCode, lat, lng)).openPopup();
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
    let code = '100', temp = '--', precip = '--', wind = '';
    if (data.weather) {
      if (data.weather.weather_code !== undefined) code = String(data.weather.weather_code);
      if (data.weather.temperature !== undefined) temp = data.weather.temperature;
      if (data.weather.precipitation_prob !== undefined && data.weather.precipitation_prob !== null) precip = data.weather.precipitation_prob;
      if (data.weather.wind !== undefined) wind = data.weather.wind;
    }
    
    const disaster = this.generatePopupDisasterHTML(data.disaster);
    const alert = this.generatePopupAlertHTML(data.alert);
    const iconClass = this.weatherIconMap[code] || 'fas fa-sun';
    const name = this.weatherCodeMap[code] || '天気情報不明';
    
    // 風データの処理
    const windDisplay = this.formatWindDisplay(wind);
    
    return `<div class="popup-content">
      <div class="popup-weather-icon"><i class="${iconClass}"></i></div>
      <div class="popup-description">${name}</div>
      <div class="popup-weather-data">
        <div class="popup-temp-container">
          <div class="popup-temp">${temp !== '--' ? temp + '°C' : '--°C'}</div>
          <div class="popup-temp-label">気温</div>
        </div>
        <div class="popup-precipitation_prob-container">
          <div class="popup-precipitation_prob">${precip !== '--' ? precip + '%' : '--'}</div>
          <div class="popup-precipitation_prob-label">降水確率</div>
        </div>
        <div class="popup-wind-container">
          <div class="popup-wind-main">
            ${windDisplay.arrow}
            <div class="popup-wind-text">${windDisplay.text}</div>
          </div>
          <div class="popup-wind-label">風向・風速</div>
        </div>
      </div>
      ${alert}${disaster}
      <div class="popup-coords">緯度: ${lat.toFixed(4)}, 経度: ${lng.toFixed(4)}</div>
    </div>`;
  }

  createErrorPopupContent(message, errorCode, lat, lng) {
    const errorCodeDisplay = errorCode ? `<div class="popup-error-code">エラーコード: ${errorCode}</div>` : '';
    
    // エラーの詳細情報を取得
    const errorDetails = this.getErrorDetails(errorCode);
    let detailsHTML = '';
    
    if (errorDetails) {
      const { categoryInfo, actionableInfo } = this.getErrorCategoryInfo(errorDetails.category);
      const icon = this.getErrorIcon(errorDetails.category);
      
      detailsHTML = `
        <div class="popup-error-details">
          <div class="error-category-header">
            <i class="${icon}"></i>
            <strong>${categoryInfo.name}</strong>
          </div>
          <div class="error-detail-item">
            <strong>問題:</strong> ${errorDetails.description}
          </div>
          <div class="error-actionable-info ${actionableInfo.class}">
            <i class="${actionableInfo.icon}"></i>
            <strong>${actionableInfo.title}:</strong> ${actionableInfo.message}
          </div>
          ${errorDetails.serverType ? `<div class="error-detail-item"><strong>関連サーバ:</strong> ${this.getServerTypeName(errorDetails.serverType)}</div>` : ''}
        </div>
      `;
    }
    
    return `<div class="popup-content popup-error"><div class="popup-weather-icon"><i class="fas fa-exclamation-triangle" style="color: #e74c3c;"></i></div><div class="popup-description error-message">${message}</div>${errorCodeDisplay}${detailsHTML}<div class="popup-coords">緯度: ${lat.toFixed(4)}, 経度: ${lng.toFixed(4)}</div></div>`;
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
    const toggleBtn = document.querySelector('.mobile-toggle');
    if (toggleBtn) toggleBtn.addEventListener('click', this.toggleSidebar);

    const showWeeklyBtn = document.getElementById('show-weekly-btn');
    if (showWeeklyBtn) showWeeklyBtn.addEventListener('click', () => this.showWeeklyForecast());

    const hideWeeklyBtn = document.getElementById('hide-weekly-btn');
    if (hideWeeklyBtn) hideWeeklyBtn.addEventListener('click', () => this.hideWeeklyForecast());


    window.addEventListener('resize', () => { if (this.map) this.map.invalidateSize(); });

    // タブボタンのイベントリスナーを設定
    document.querySelectorAll('.tab-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const tab = e.target.closest('.tab-btn').dataset.tab;
        this.switchTab(tab);
      });
    });

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
    const wfVisible = wf && wf.style.display !== 'none';

    if (wfVisible) {
      this.hideWeeklyForecast();
      if (panel) panel.style.display = 'none';
      return;
    }

    if (panel && panel.style.display !== 'none' && window.getComputedStyle(panel).display !== 'none') {
      panel.style.display = 'none';
    }

    if (sb && !sb.classList.contains('active')) sb.classList.add('active');

    if (window.innerWidth <= 768 && sb && !sb.classList.contains('active')) sb.classList.add('active');
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
  async showWeeklyForecast() {
    if (!this.currentLat || !this.currentLng) return;
    const wf = document.getElementById('weekly-forecast');
    const wl = document.getElementById('weekly-loading');
    const wd = document.getElementById('weekly-data');
    if (!wf) return;
    wf.style.display = 'block';
    this.isWeeklyForecastVisible = true;
    wl.style.display = 'flex';
    wd.style.display = 'none';
    try {
      const res = await fetch('/weekly_forecast', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ lat: this.currentLat, lng: this.currentLng }) });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      if (data.status === 'ok' && data.weekly_forecast) {
        const array = Object.values(data.weekly_forecast).sort((a, b) => a.day_number - b.day_number);
        this.displayWeeklyForecast(array);
      } else if (data.status === 'error') {
        this.handleWeeklyForecastError(data.error_code);
      } else throw new Error('無効な週間予報レスポンス');
    } catch (err) {
      console.error('週間予報取得エラー:', err);
      this.handleWeeklyForecastError();
    } finally { wl.style.display = 'none'; }
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
      
      // 風データの処理
      const windData = d.wind || '';
      const windDisplay = this.formatWindDisplay(windData);
      
      console.log("LAYOUT UPDATE: Creating 4-column layout structure");
      html += `<div class="${i===0?'weekly-day today':'weekly-day'}">
        <div class="day-info">
          <div class="day-name">${i===0?'今日':dayName}</div>
          <div class="day-date">${dateStr}</div>
        </div>
        <div class="day-weather">
          <i class="${icon}"></i>
        </div>
        <div class="day-temp">${(d.temperature!==undefined&&d.temperature!=='--')?d.temperature+'°C':'--°C'}</div>
        <div class="day-precip-wind">
          <div class="day-precipitation_prob">
            <i class="fas fa-umbrella"></i>${(d.precipitation_prob!==undefined&&d.precipitation_prob!=='--'&&d.precipitation_prob!==null)?d.precipitation_prob+'%':'--'}
          </div>
          <div class="day-wind">
            ${windDisplay.arrow}
            <span class="wind-text">${windDisplay.text}</span>
          </div>
        </div>
      </div>`;
    });
    wd.innerHTML = html;
    wd.style.display = 'block';
  }

  // ------------------------------------------------------------------
  // タブ & チャート
  // ------------------------------------------------------------------
  switchTab(tab) {
    document.querySelectorAll('.tab-btn').forEach(btn => { 
      btn.classList.toggle('active', btn.dataset.tab === tab); 
    });
    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
    
    let targetId;
    switch(tab) {
      case 'weekly-list-view':
        targetId = 'weekly-list-view';
        break;
      case 'weekly-chart-view':
        targetId = 'weekly-chart-view';
        break;
      case 'landmarks-view':
        targetId = 'landmarks-view';
        this.loadLandmarks();
        break;
      default:
        targetId = 'weekly-list-view';
        break;
    }
    
    const tgt = document.getElementById(targetId);
    if (tgt) tgt.classList.add('active');
    
    if (tab === 'weekly-chart-view' && this.weeklyDataForChart) {
      setTimeout(() => this.drawChart('combined'), 100);
    }
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
      
      // 風データの処理
      const windData = d.wind || '';
      const windDisplay = this.formatWindDisplay(windData);
      
    console.log("LAYOUT UPDATE 2: Creating 4-column layout structure in displayWeeklyForecast");
    html += `<div class="${i===0?'weekly-day today':'weekly-day'}">
      <div class="day-info">
        <div class="day-name">${i===0?'今日':dayName}</div>
        <div class="day-date">${dateStr}</div>
      </div>
      <div class="day-weather">
        <i class="${icon}"></i>
      </div>
      <div class="day-temp">${(d.temperature!==undefined&&d.temperature!=='--')?d.temperature+'°C':'--°C'}</div>
      <div class="day-precip-wind">
        <div class="day-precipitation_prob">
          <i class="fas fa-umbrella"></i>${(d.precipitation_prob!==undefined&&d.precipitation_prob!=='--'&&d.precipitation_prob!==null)?d.precipitation_prob+'%':'--'}
        </div>
        <div class="day-wind">
          ${windDisplay.arrow}
          <span class="wind-text">${windDisplay.text}</span>
        </div>
      </div>
    </div>`;
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

      this.ws.onopen = () => lp.appendLog({
        type: 'log',
        timestamp: new Date().toISOString(),
        level: 'success',
        message: 'WebSocket 接続完了'
      });

      // bulk対応：terminal-log-panel.js が提供する共通ハンドラに委譲
      this.ws.onmessage = (e) => {
        const lp = window.logPanel;
        let payload;
        try { payload = JSON.parse(e.data); }
        catch {
          lp.appendLog({type:'log',timestamp:new Date().toISOString(),level:'warning',message:e.data});
          return;
        }

        // bulk
        if (payload.type === 'bulk' && Array.isArray(payload.logs)) {
          payload.logs.forEach(item => {
            let obj = item;
            // （後方互換）要素が文字列なら JSON.parse
            if (typeof item === 'string') {
              try { obj = JSON.parse(item); } catch {/*skip this*/ return;}
            }
            if (obj.type === 'metrics') {
              lp.updateMetrics(obj.total ?? 0, obj.avg_ms ?? 0, obj.packet_total ?? 0, obj.packet_avg_ms ?? 0);
            } else {
              lp.appendLog(obj);
            }
          });
          return;
        }

        // metrics 単発
        if (payload.type === 'metrics') {
          lp.updateMetrics(payload.total ?? 0, payload.avg_ms ?? 0,
                          payload.packet_total ?? 0, payload.packet_avg_ms ?? 0);
          return;
        }

        // 単発ログ
        if (payload.type === 'log' || payload.level) {
          lp.appendLog(payload);
          return;
        }

        // fallback
        lp.appendLog({type:'log',timestamp:new Date().toISOString(),level:'info',message:e.data});
      };

      this.ws.onclose = () => {
        lp.appendLog({
          type: 'log',
          timestamp: new Date().toISOString(),
          level: 'warning',
          message: 'WebSocket 切断 - 再接続します'
        });
        setTimeout(connect, 3000);
      };

      this.ws.onerror = (e) => console.error('WebSocket エラー:', e);
    };
    connect();
  }

  // ------------------------------------------------------------------
  // ランドマーク機能
  // ------------------------------------------------------------------
  loadLandmarks() {
    if (
      this.lastLandmarks &&
      Array.isArray(this.lastLandmarks.landmarks) &&
      this.lastLandmarks.landmarks.length > 0
    ) {
      this.displayLandmarks(
        this.lastLandmarks.landmarks,
        this.lastLandmarks.area_name || '不明'
      );
    } else {
      this.showLandmarksEmpty();
    }
  }

  displayLandmarks(landmarks, areaName = '不明') {
    const landmarksEmpty = document.getElementById('landmarks-empty');
    const landmarksList = document.getElementById('landmarks-list');

    if (landmarksEmpty) landmarksEmpty.style.display = 'none';
    if (!landmarksList) return;

    // 表示用に距離を付与して昇順ソート
    const currentLat = this.currentLat;
    const currentLng = this.currentLng;
    const sortedLandmarks = (landmarks || []).map(l => {
      const dist = (l && l.distance !== undefined)
        ? Number(l.distance)
        : this.calculateDistance(currentLat, currentLng, l.latitude, l.longitude);
      return { ...l, distance: dist };
    }).sort((a, b) => {
      const da = (a.distance !== undefined) ? Number(a.distance) : Number.POSITIVE_INFINITY;
      const db = (b.distance !== undefined) ? Number(b.distance) : Number.POSITIVE_INFINITY;
      return da - db; // 距離の昇順
    });

    // ヘッダーを追加
    let html = `
      <div class="landmarks-header">
        <div class="landmarks-title">
          <i class="fas fa-map-marker-alt"></i>
          ${areaName} の観光地
        </div>
        <div class="landmarks-count">${landmarks.length}件</div>
      </div>
    `;

    // ランドマークリストを生成
    sortedLandmarks.forEach((landmark, index) => {
      // APIから提供された距離 or 計算距離を使用（既に昇順にソート済み）
      const distance = landmark.distance;

      html += `
        <div class="landmark-item" onclick="weatherApp.focusLandmark(${landmark.latitude}, ${landmark.longitude}, '${landmark.name.replace(/'/g, "\\'")}')">
          <div class="landmark-icon">
            <i class="fas fa-map-marker-alt"></i>
          </div>
          <div class="landmark-info">
            <div class="landmark-name" title="${landmark.name}">${landmark.name}</div>
            <div class="landmark-coords">${landmark.latitude.toFixed(4)}, ${landmark.longitude.toFixed(4)}</div>
          </div>
          <div class="landmark-distance">${distance}km</div>
        </div>
      `;
    });

    landmarksList.innerHTML = html;
    landmarksList.style.display = 'block';
  }

  showLandmarksEmpty(message = '地図をクリックしてエリアを選択すると<br>周辺の観光地が表示されます') {
    const landmarksEmpty = document.getElementById('landmarks-empty');
    const landmarksList = document.getElementById('landmarks-list');
    
    if (landmarksList) landmarksList.style.display = 'none';
    if (landmarksEmpty) {
      landmarksEmpty.innerHTML = `
        <i class="fas fa-map-marker-alt"></i>
        <p>${message}</p>
      `;
      landmarksEmpty.style.display = 'block';
    }
  }

  calculateDistance(lat1, lng1, lat2, lng2) {
    const R = 6371; // 地球の半径（km）
    const dLat = this.toRad(lat2 - lat1);
    const dLng = this.toRad(lng2 - lng1);
    const a = Math.sin(dLat/2) * Math.sin(dLat/2) +
              Math.cos(this.toRad(lat1)) * Math.cos(this.toRad(lat2)) *
              Math.sin(dLng/2) * Math.sin(dLng/2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
    const distance = R * c;
    return Math.round(distance * 10) / 10; // 小数点第1位まで
  }

  toRad(value) {
    return value * Math.PI / 180;
  }

  focusLandmark(lat, lng, name) {
    if (this.map) {
      this.map.setView([lat, lng], 15);
      
      // 既存のランドマーカーマーカーがあれば削除
      if (this.landmarkMarker) {
        this.map.removeLayer(this.landmarkMarker);
        this.landmarkMarker = null;
      }

      // 該当施設の位置を示すマーカーを表示（保持）
      this.landmarkMarker = L.marker([lat, lng]).addTo(this.map);
      this.landmarkMarker.bindPopup(`
        <div class="popup-content">
          <div class="popup-area"><i class="fas fa-map-marker-alt"></i> ${name}</div>
          <div class="popup-coords">${lat.toFixed(4)}, ${lng.toFixed(4)}</div>
        </div>
      `).openPopup();
    }
  }

  // 既存のランドマークピンを全削除
  clearLandmarkPins() {
    if (this.landmarkLayer && this.map) {
      this.landmarkLayer.clearLayers();
    }
    // 進行中の分割描画を停止
    if (this.pinRenderTimers && this.pinRenderTimers.length) {
      this.pinRenderTimers.forEach(id => clearTimeout(id));
      this.pinRenderTimers = [];
    }
  }

  // 渡されたランドマーク配列を地図上にピンとして描画
  renderLandmarkPins(landmarks) {
    if (!this.map) return;
    if (!this.landmarkLayer) {
      this.landmarkLayer = L.layerGroup().addTo(this.map);
    } else {
      this.landmarkLayer.clearLayers();
    }

    const bounds = [];
    // 距離の昇順に近いものから上限まで描画（distance がなければ順序そのまま）
    let list = Array.isArray(landmarks) ? landmarks.slice() : [];
    const hasDistance = list.length > 0 && list.some(l => l && l.distance !== undefined);
    if (hasDistance) {
      list.sort((a, b) => Number(a.distance ?? Infinity) - Number(b.distance ?? Infinity));
    }
    const toRender = list.slice(0, this.maxLandmarkPins);

    // 分割描画: 50件ずつ追加して体感速度を改善
    const batchSize = 50;
    let idx = 0;
    const addBatch = () => {
      const end = Math.min(idx + batchSize, toRender.length);
      for (let i = idx; i < end; i++) {
        const l = toRender[i];
        if (l && typeof l.latitude === 'number' && typeof l.longitude === 'number') {
          const m = L.marker([l.latitude, l.longitude]);
          m.bindPopup(`<div class="popup-content">
              <div class="popup-area"><i class="fas fa-map-marker-alt"></i> ${l.name || '施設'}</div>
              <div class="popup-coords">${l.latitude.toFixed(4)}, ${l.longitude.toFixed(4)}</div>
            </div>`);
          m.addTo(this.landmarkLayer);
          bounds.push([l.latitude, l.longitude]);
        }
      }
      idx = end;
      if (idx < toRender.length) {
        const id = setTimeout(addBatch, 0);
        this.pinRenderTimers.push(id);
      }
    };
    // 既存タイマー停止
    this.pinRenderTimers.forEach(id => clearTimeout(id));
    this.pinRenderTimers = [];
    addBatch();

    // ピンが複数ある場合でもデフォルトでは自動ズームしない
    if (this.autoFitLandmarks && bounds.length >= 2) {
      try { this.map.fitBounds(bounds, { padding: [30, 30], maxZoom: 14 }); } catch (_) {}
    }
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
document.addEventListener('DOMContentLoaded',()=>{ console.log('DOM loaded – WeatherApp init'); weatherApp = new WeatherApp(); });
window.addEventListener('load',()=>{ if(!weatherApp){ console.log('window load – WeatherApp re-init'); weatherApp = new WeatherApp(); } });

if(typeof module!=='undefined' && module.exports){ module.exports = { WeatherApp, ParticleSystemManager }; }

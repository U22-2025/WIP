// 次世代天気サイト - メインJavaScriptファイル

class WeatherApp {
    constructor() {
        this.map = null;
        this.currentMarker = null;
        this.weatherCodeMap = {};
        this.isWeatherCodeLoaded = false;
        this.errorCodeMap = {};
        this.isErrorCodeLoaded = false;
        this.currentTheme = 'default';
        this.particleManager = null;
        this.isLightningActive = false;
        this.currentLat = null;
        this.currentLng = null;
        this.isWeeklyForecastVisible = false;
        this.currentChart = null;
        this.currentChartType = 'temperature';
        this.weeklyDataForChart = null;
        this.disasterInfo = null;

        // 天気アイコンマッピング
        this.weatherIconMap = {
            // 晴れ系（100番台）
            '100': 'fas fa-sun',
            '101': 'fas fa-cloud-sun',
            '102': 'fas fa-cloud-sun-rain',
            '103': 'fas fa-cloud-sun-rain',
            '104': 'fas fa-cloud-snow',
            '105': 'fas fa-cloud-snow',
            '106': 'fas fa-cloud-snow',
            '107': 'fas fa-cloud-snow',
            '108': 'fas fa-cloud-bolt',
            '110': 'fas fa-cloud-sun',
            '111': 'fas fa-cloud-sun',
            '112': 'fas fa-cloud-sun-rain',
            '113': 'fas fa-cloud-sun-rain',
            '114': 'fas fa-cloud-rain',
            '115': 'fas fa-cloud-snow',
            '116': 'fas fa-cloud-snow',
            '117': 'fas fa-snowflake',
            '118': 'fas fa-cloud-snow',
            '119': 'fas fa-cloud-bolt',
            '120': 'fas fa-cloud-sun-rain',
            '121': 'fas fa-cloud-sun-rain',
            '122': 'fas fa-cloud-sun-rain',
            '123': 'fas fa-cloud-bolt',
            '124': 'fas fa-cloud-snow',
            '125': 'fas fa-cloud-bolt',
            '126': 'fas fa-cloud-rain',
            '127': 'fas fa-cloud-rain',
            '128': 'fas fa-cloud-rain',
            '129': 'fas fa-cloud-rain',
            '130': 'fas fa-smog',
            '131': 'fas fa-smog',
            '132': 'fas fa-cloud-sun',
            '140': 'fas fa-cloud-bolt',
            '160': 'fas fa-cloud-snow',
            '170': 'fas fa-cloud-snow',
            '181': 'fas fa-cloud-snow',

            // 曇り系（200番台）
            '200': 'fas fa-cloud',
            '201': 'fas fa-cloud-sun',
            '202': 'fas fa-cloud-rain',
            '203': 'fas fa-cloud-rain',
            '204': 'fas fa-cloud-snow',
            '205': 'fas fa-cloud-snow',
            '206': 'fas fa-cloud-snow',
            '207': 'fas fa-cloud-snow',
            '208': 'fas fa-cloud-bolt',
            '209': 'fas fa-smog',
            '210': 'fas fa-cloud-sun',
            '211': 'fas fa-cloud-sun',
            '212': 'fas fa-cloud-rain',
            '213': 'fas fa-cloud-rain',
            '214': 'fas fa-cloud-rain',
            '215': 'fas fa-cloud-snow',
            '216': 'fas fa-cloud-snow',
            '217': 'fas fa-snowflake',
            '218': 'fas fa-cloud-snow',
            '219': 'fas fa-cloud-bolt',
            '220': 'fas fa-cloud-rain',
            '221': 'fas fa-cloud-rain',
            '222': 'fas fa-cloud-rain',
            '223': 'fas fa-cloud-sun',
            '224': 'fas fa-cloud-rain',
            '225': 'fas fa-cloud-rain',
            '226': 'fas fa-cloud-rain',
            '227': 'fas fa-cloud-rain',
            '228': 'fas fa-cloud-snow',
            '229': 'fas fa-cloud-snow',
            '230': 'fas fa-cloud-snow',
            '231': 'fas fa-smog',
            '240': 'fas fa-cloud-bolt',
            '250': 'fas fa-cloud-bolt',
            '260': 'fas fa-cloud-snow',
            '270': 'fas fa-cloud-snow',
            '281': 'fas fa-cloud-snow',

            // 雨系（300番台）
            '300': 'fas fa-cloud-rain',
            '301': 'fas fa-cloud-sun-rain',
            '302': 'fas fa-cloud-rain',
            '303': 'fas fa-cloud-snow',
            '304': 'fas fa-cloud-snow',
            '306': 'fas fa-cloud-showers-heavy',
            '307': 'fas fa-wind',
            '308': 'fas fa-wind',
            '309': 'fas fa-cloud-snow',
            '311': 'fas fa-cloud-sun-rain',
            '313': 'fas fa-cloud-rain',
            '314': 'fas fa-cloud-snow',
            '315': 'fas fa-snowflake',
            '316': 'fas fa-cloud-sun',
            '317': 'fas fa-cloud',
            '320': 'fas fa-cloud-sun-rain',
            '321': 'fas fa-cloud-rain',
            '322': 'fas fa-cloud-snow',
            '323': 'fas fa-cloud-sun',
            '324': 'fas fa-cloud-sun',
            '325': 'fas fa-cloud-sun',
            '326': 'fas fa-cloud-snow',
            '327': 'fas fa-cloud-snow',
            '328': 'fas fa-cloud-showers-heavy',
            '329': 'fas fa-cloud-snow',
            '340': 'fas fa-cloud-snow',
            '350': 'fas fa-cloud-bolt',
            '361': 'fas fa-cloud-sun',
            '371': 'fas fa-cloud',

            // 雪系（400番台）
            '400': 'fas fa-snowflake',
            '401': 'fas fa-cloud-snow',
            '402': 'fas fa-snowflake',
            '403': 'fas fa-cloud-snow',
            '405': 'fas fa-snowflake',
            '406': 'fas fa-wind',
            '407': 'fas fa-wind',
            '409': 'fas fa-cloud-snow',
            '411': 'fas fa-cloud-sun',
            '413': 'fas fa-cloud',
            '414': 'fas fa-cloud-rain',
            '420': 'fas fa-cloud-sun',
            '421': 'fas fa-cloud',
            '422': 'fas fa-cloud-rain',
            '423': 'fas fa-cloud-rain',
            '424': 'fas fa-cloud-rain',
            '425': 'fas fa-snowflake',
            '426': 'fas fa-cloud-snow',
            '427': 'fas fa-cloud-snow',
            '450': 'fas fa-cloud-bolt'
        };

        // 天気アイコンのクラス名マッピング
        this.weatherIconClassMap = {
            // 晴れ系
            '100': 'sunny',
            '101': 'sunny',
            '110': 'sunny',
            '111': 'sunny',
            '132': 'sunny',
            // 雨系
            '300': 'rainy',
            '301': 'rainy',
            '302': 'rainy',
            '306': 'rainy',
            '311': 'rainy',
            '313': 'rainy',
            '320': 'rainy',
            '321': 'rainy',
            '328': 'rainy',
            // 風系
            '307': 'windy',
            '308': 'windy',
            '406': 'windy',
            '407': 'windy'
        };

        this.init();
    }

    getErrorMessage(code) {
        if (this.isErrorCodeLoaded && code && this.errorCodeMap[String(code)]) {
            return this.errorCodeMap[String(code)];
        }
        return '不明なエラーが発生しました';
    }

    // 初期化
    async init() {
        console.log('WeatherApp初期化開始');

        try {
            // 天気コードを読み込み
            await this.loadWeatherCodes();
            // エラーコードを読み込み
            await this.loadErrorCodes();

            // パーティクルシステムを初期化
            this.particleManager = new ParticleSystemManager();

            // 地図を初期化
            await this.initializeMap();

            // イベントリスナーを設定
            this.setupEventListeners();

            // 時間帯別テーマを適用
            this.applyTimeTheme();

            console.log('WeatherApp初期化完了');
        } catch (error) {
            console.error('WeatherApp初期化エラー:', error);
        }
    }

    // CSS変数を取得するヘルパー関数（フォールバック付き）
    getCSSVariable(variableName) {
        const value = getComputedStyle(document.documentElement).getPropertyValue(variableName).trim();
        // フォールバック値を設定
        const fallbacks = {
            '--chart-text-primary': '#2d3436',
            '--chart-text-secondary': '#636e72',
            '--chart-grid-color': 'rgba(182, 190, 195, 0.3)'
        };
        return value || fallbacks[variableName] || '#2d3436';
    }

    // 天気コードを読み込む
    async loadWeatherCodes() {
        try {
            console.log('天気コードを読み込み中...');
            const response = await fetch('./weather_code.json');
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            this.weatherCodeMap = await response.json();
            this.isWeatherCodeLoaded = true;
            console.log('天気コードの読み込み完了:', Object.keys(this.weatherCodeMap).length + '個のコード');
        } catch (error) {
            console.error('天気コード読み込みエラー:', error);
            // フォールバック: 基本的な天気コード
            this.weatherCodeMap = {
                '100': '晴れ',
                '200': '曇り',
                '300': '雨',
                '400': '雪'
            };
            this.isWeatherCodeLoaded = true;
        }
    }

    // エラーコードを読み込む
    async loadErrorCodes() {
        try {
            const response = await fetch('./error_code.json');
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            this.errorCodeMap = await response.json();
            this.isErrorCodeLoaded = true;
        } catch (error) {
            console.error('エラーコード読み込みエラー:', error);
            this.errorCodeMap = {};
            this.isErrorCodeLoaded = false;
        }
    }

    // 地図初期化
    async initializeMap() {
        try {
            console.log('地図初期化開始');

            this.map = L.map('map', {
                zoomControl: true,
                attributionControl: true,
                preferCanvas: false
            }).setView([35.6895, 139.6917], 6);

            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
                maxZoom: 18,
                tileSize: 256,
                zoomOffset: 0
            }).addTo(this.map);

            console.log('地図が正常に初期化されました');
            this.setupMapEvents();

        } catch (error) {
            console.error('地図初期化エラー:', error);
        }
    }

    // 地図イベント設定
    setupMapEvents() {
        console.log('地図イベント設定開始');

        this.map.on('click', (e) => {
            this.handleMapClick(e.latlng.lat, e.latlng.lng);
        });

        // モバイル用: 地図クリックでサイドバーを閉じる
        if (window.innerWidth <= 768) {
            this.map.on('click', () => {
                setTimeout(() => {
                    const sidebar = document.getElementById('sidebar');
                    if (sidebar.classList.contains('active')) {
                        sidebar.classList.remove('active');
                    }
                }, 100);
            });
        }
    }

    // 地図クリック処理
    async handleMapClick(lat, lng) {
        console.log(`地図がクリックされました: 緯度=${lat}, 経度=${lng}`);

        // 現在の座標を保存
        this.currentLat = lat;
        this.currentLng = lng;

        // 既存マーカー削除
        if (this.currentMarker) {
            this.map.removeLayer(this.currentMarker);
        }

        // 新しいマーカー作成
        try {
            this.currentMarker = L.marker([lat, lng], {
                icon: L.divIcon({
                    className: 'custom-marker',
                    html: '<div style="background: var(--primary-color); width: 24px; height: 24px; border-radius: 50%; border: 4px solid white; box-shadow: 0 4px 12px rgba(0,0,0,0.4); cursor: pointer;"></div>',
                    iconSize: [24, 24],
                    iconAnchor: [12, 12]
                })
            });

            this.currentMarker.addTo(this.map);
        } catch (markerError) {
            console.error('マーカー作成エラー:', markerError);
        }

        this.showLoading();

        try {
            // 週間予報データを取得（今日の分も含まれる）
            const weeklyResponse = await fetch('/weekly_forecast', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    lat: lat,
                    lng: lng
                })
            });

            if (!weeklyResponse.ok) {
                throw new Error(`HTTP error! status: ${weeklyResponse.status}`);
            }

            const weeklyData = await weeklyResponse.json();
            console.log('週間予報データ:', weeklyData);

            if (weeklyData.status === 'ok' && weeklyData.weekly_forecast && Object.keys(weeklyData.weekly_forecast).length > 0) {
                const forecastArray = Object.values(weeklyData.weekly_forecast).sort((a, b) => a.day_number - b.day_number);
                // 今日の天気情報（day=0）を現在の天気として表示
                const todayWeather = forecastArray[0];
                const currentWeatherData = {
                    status: 'ok',
                    weather: {
                        weather_code: todayWeather.weather_code,
                        temperature: todayWeather.temperature,
                        precipitation_prob: todayWeather.precipitation_prob,
                        // その他のフィールドがあれば追加
                        visibility: todayWeather.visibility || '--',
                        wind_speed: todayWeather.wind_speed || '--',
                        pressure: todayWeather.pressure || '--',
                        humidity: todayWeather.humidity || '--',
                        uv_index: todayWeather.uv_index || '--'
                    }
                };

                // 現在の天気情報を表示
                this.displayWeatherInfo(currentWeatherData, lat, lng);
                if (this.currentMarker) {
                    this.currentMarker.bindPopup(this.createPopupContent(currentWeatherData, lat, lng)).openPopup();
                }

                // 週間予報を自動的に表示
                this.displayWeeklyForecastData(forecastArray);

                // 災害情報を取得して表示
                if (weeklyData.area_code) {
                    await this.fetchDisasterInfo(weeklyData.area_code);
                }

            } else if (weeklyData.status === 'error') {
                this.handleAPIError(lat, lng, weeklyData.error_code);
            } else {
                throw new Error('無効な週間予報レスポンス');
            }
        } catch (error) {
            console.error('週間予報取得エラー:', error);
            this.handleAPIError(lat, lng);
        } finally {
            this.hideLoading();
        }
    }

    // APIエラー処理
    handleAPIError(lat, lng, errorCode = null) {
        const message = this.getErrorMessage(errorCode);
        const noData = document.getElementById('no-data');
        if (noData) {
            noData.innerHTML = `<i class="fas fa-exclamation-triangle"></i><p>${message}</p>`;
            noData.style.display = 'block';
        }

        // データ表示領域を非表示
        const weatherContent = document.getElementById('weather-content');
        if (weatherContent) {
            weatherContent.style.display = 'none';
        }

        // 週間予報をクリア
        this.hideWeeklyForecast();
        const weeklyDataContainer = document.getElementById('weekly-data');
        if (weeklyDataContainer) {
            weeklyDataContainer.innerHTML = '';
        }
        this.weeklyDataForChart = null;

        // マーカーのポップアップのみ更新（ダミーデータ表示）
        const sampleData = {
            status: 'ok',
            weather: {
                weather_code: '100',
                temperature: '--',
                precipitation_prob: '--'
            }
        };

        if (this.currentMarker) {
            this.currentMarker.bindPopup(this.createPopupContent(sampleData, lat, lng)).openPopup();
        }
    }

    // 天気情報表示
    displayWeatherInfo(data, lat, lng) {
        console.log('天気情報表示開始:', data);

        document.getElementById('no-data').style.display = 'none';
        document.getElementById('weather-content').style.display = 'block';

        // 天気情報の処理
        let weatherCode = '100';

        if (data.weather) {
            if (data.weather.weather_code !== undefined && data.weather.weather_code !== null) {
                weatherCode = data.weather.weather_code.toString();
            }
        }

        console.log('処理された天気データ:', {
            weatherCode
        });

        // テーマとエフェクトを適用
        const weatherTheme = this.getWeatherTheme(weatherCode);
        const timeTheme = this.getTimeTheme();
        this.applyTheme(weatherTheme, timeTheme);
        this.startWeatherEffects(weatherCode);
    }

    // 詳細項目更新
    updateDetailItem(id, value) {
        const element = document.getElementById(id);
        if (element) {
            element.textContent = value;
        }
    }

    // ポップアップコンテンツ生成
    createPopupContent(data, lat, lng) {
        let weatherCode = '100';
        let temperature = '--';
        let precipitation_prob = '--';

        if (data.weather) {
            if (data.weather.weather_code !== undefined) {
                weatherCode = data.weather.weather_code.toString();
            }
            if (data.weather.temperature !== undefined) {
                temperature = data.weather.temperature;
            }
            if (data.weather.precipitation_prob !== undefined && data.weather.precipitation_prob !== null) {
                precipitation_prob = data.weather.precipitation_prob;
            }
        }

        const iconClass = this.weatherIconMap[weatherCode] || 'fas fa-sun';
        const weatherName = this.weatherCodeMap[weatherCode] || '天気情報不明';
        const temp = temperature !== '--' ? `${temperature}°C` : '--°C';
        const precipitation_probText = precipitation_prob !== '--' && precipitation_prob !== null && precipitation_prob !== undefined ?
            `${precipitation_prob}%` : '--';

        return `
            <div class="popup-content">
                <div class="popup-weather-icon">
                    <i class="${iconClass}"></i>
                </div>
                <div class="popup-description">${weatherName}</div>
                <div class="popup-weather-data">
                    <div class="popup-temp-container">
                        <div class="popup-temp">${temp}</div>
                        <div class="popup-temp-label">気温</div>
                    </div>
                    <div class="popup-precipitation_prob-container">
                        <div class="popup-precipitation_prob">${precipitation_probText}</div>
                        <div class="popup-precipitation_prob-label">降水確率</div>
                    </div>
                </div>
                <div class="popup-coords">緯度: ${lat.toFixed(4)}, 経度: ${lng.toFixed(4)}</div>
            </div>
        `;
    }

    // 天気連動テーマシステム
    getWeatherTheme(weatherCode) {
        const code = weatherCode.toString();
        const firstDigit = code.charAt(0);

        // 雷系
        if (code.includes('08') || code.includes('19') || code.includes('23') ||
            code.includes('25') || code.includes('40') || code.includes('50')) {
            return 'stormy';
        }
        // 雪系
        if (firstDigit === '4' || code.includes('04') || code.includes('15') ||
            code.includes('16') || code.includes('17') || code.includes('18')) {
            return 'snowy';
        }
        // 雨系
        if (firstDigit === '3' || code.includes('02') || code.includes('12') ||
            code.includes('13') || code.includes('14')) {
            return 'rainy';
        }
        // 曇り系
        if (firstDigit === '2' || code.includes('01') || code.includes('11')) {
            return 'cloudy';
        }
        // 晴れ系
        if (firstDigit === '1' || code === '100') {
            return 'sunny';
        }

        return 'default';
    }

    // 時間帯別テーマ取得
    getTimeTheme() {
        const hour = new Date().getHours();
        if (hour >= 6 && hour < 10) return 'morning';
        if (hour >= 10 && hour < 16) return 'noon';
        if (hour >= 16 && hour < 19) return 'evening';
        return 'night';
    }

    // テーマ適用
    applyTheme(weatherTheme, timeTheme) {
        const body = document.body;

        // 既存のテーマクラスを削除
        body.classList.remove('theme-sunny', 'theme-cloudy', 'theme-rainy', 'theme-snowy', 'theme-stormy');
        body.classList.remove('time-morning', 'time-noon', 'time-evening', 'time-night');

        // 新しいテーマを適用
        if (weatherTheme !== 'default') {
            body.classList.add(`theme-${weatherTheme}`);
        }
        body.classList.add(`time-${timeTheme}`);

        this.currentTheme = weatherTheme;
    }

    // 時間帯テーマのみ適用
    applyTimeTheme() {
        const timeTheme = this.getTimeTheme();
        const body = document.body;

        // 既存の時間帯テーマクラスを削除
        body.classList.remove('time-morning', 'time-noon', 'time-evening', 'time-night');

        // 新しい時間帯テーマを適用
        body.classList.add(`time-${timeTheme}`);
    }

    // 天気エフェクト開始
    startWeatherEffects(weatherCode) {
        const code = weatherCode.toString();

        // パーティクルエフェクトを停止
        this.particleManager.stopEffect();

        // 雷エフェクトを停止
        const lightningElement = document.getElementById('lightning-effect');
        if (lightningElement) {
            lightningElement.style.display = 'none';
        }
        this.isLightningActive = false;

        // 天気に応じたエフェクトを開始
        if (code.includes('08') || code.includes('19') || code.includes('23') ||
            code.includes('25') || code.includes('40') || code.includes('50')) {
            // 雷雨
            this.startLightningEffect();
            this.particleManager.startEffect('rain');
        } else if (code.charAt(0) === '4' || code.includes('04') || code.includes('15') ||
            code.includes('16') || code.includes('17') || code.includes('18')) {
            // 雪
            this.particleManager.startEffect('snow');
        } else if (code.charAt(0) === '3' || code.includes('02') || code.includes('12') ||
            code.includes('13') || code.includes('14')) {
            // 雨
            this.particleManager.startEffect('rain');
        } else if (code.includes('07') || code.includes('08') || code.includes('06') || code.includes('07')) {
            // 風
            this.particleManager.startEffect('wind');
        }
    }

    // 雷エフェクト開始
    startLightningEffect() {
        if (this.isLightningActive) return;

        this.isLightningActive = true;
        const lightningElement = document.getElementById('lightning-effect');
        if (lightningElement) {
            lightningElement.style.display = 'block';

            setTimeout(() => {
                lightningElement.style.display = 'none';
                this.isLightningActive = false;
            }, 4000);
        }
    }

    // イベントリスナー設定
    setupEventListeners() {
        // サイドバートグルボタン
        const toggleBtn = document.querySelector('.mobile-toggle');
        if (toggleBtn) {
            toggleBtn.addEventListener('click', this.toggleSidebar);
        }

        // 週間予報ボタン
        const showWeeklyBtn = document.getElementById('show-weekly-btn');
        if (showWeeklyBtn) {
            showWeeklyBtn.addEventListener('click', () => {
                this.showWeeklyForecast();
            });
        }

        const hideWeeklyBtn = document.getElementById('hide-weekly-btn');
        if (hideWeeklyBtn) {
            hideWeeklyBtn.addEventListener('click', () => {
                this.hideWeeklyForecast();
            });
        }

        // ウィンドウリサイズ
        window.addEventListener('resize', () => {
            if (this.map) {
                this.map.invalidateSize();
            }
        });

        // スイッチ切り替えイベント
        const tabSwitch = document.getElementById('viewSwitch');
        if (tabSwitch) {
            tabSwitch.addEventListener('change', (e) => {
                this.switchTab(e.target.checked ? 'chart' : 'list');
            });
        }

        // キーボードイベント
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                const sidebar = document.getElementById('sidebar');
                if (sidebar && sidebar.classList.contains('active')) {
                    sidebar.classList.remove('active');
                }
                const weeklyForecast = document.getElementById('weekly-forecast');
                if (weeklyForecast && weeklyForecast.style.display !== 'none') {
                    this.hideWeeklyForecast();
                }
            }
        });
    }

    // サイドバー表示切り替え
    toggleSidebar() {
        const sidebar = document.getElementById('sidebar');
        if (sidebar) {
            sidebar.classList.toggle('active');
        }
    }

    // ローディング表示
    showLoading() {
        const loadingOverlay = document.getElementById('loading-overlay');
        if (loadingOverlay) {
            loadingOverlay.style.display = 'flex';
        }
    }

    // ローディング非表示
    hideLoading() {
        const loadingOverlay = document.getElementById('loading-overlay');
        if (loadingOverlay) {
            loadingOverlay.style.display = 'none';
        }
    }

    // 週間予報表示
    async showWeeklyForecast() {
        if (!this.currentLat || !this.currentLng) {
            console.warn('座標が設定されていません');
            return;
        }

        const weeklyForecast = document.getElementById('weekly-forecast');
        const weeklyLoading = document.getElementById('weekly-loading');
        const weeklyData = document.getElementById('weekly-data');

        if (!weeklyForecast) return;

        // 週間予報パネルを表示
        weeklyForecast.style.display = 'block';
        this.isWeeklyForecastVisible = true;

        // ローディング表示
        weeklyLoading.style.display = 'flex';
        weeklyData.style.display = 'none';

        try {
            const response = await fetch('/weekly_forecast', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    lat: this.currentLat,
                    lng: this.currentLng
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            console.log('週間予報データ:', data);

            if (data.status === 'ok' && data.weekly_forecast && Object.keys(data.weekly_forecast).length > 0) {
                const forecastArray = Object.values(data.weekly_forecast).sort((a, b) => a.day_number - b.day_number);
                this.displayWeeklyForecast(forecastArray);
            } else if (data.status === 'error') {
                this.handleWeeklyForecastError(data.error_code);
            } else {
                throw new Error('無効な週間予報レスポンス');
            }
        } catch (error) {
            console.error('週間予報取得エラー:', error);
            this.handleWeeklyForecastError();
        } finally {
            weeklyLoading.style.display = 'none';
        }
    }

    // 週間予報非表示
    hideWeeklyForecast() {
        const weeklyForecast = document.getElementById('weekly-forecast');
        if (weeklyForecast) {
            weeklyForecast.style.display = 'none';
            this.isWeeklyForecastVisible = false;
        }
    }

    // 週間予報データを直接表示（クリック時用）
    displayWeeklyForecastData(weeklyData) {
        const weeklyForecast = document.getElementById('weekly-forecast');
        const weeklyDataContainer = document.getElementById('weekly-data');
        const weeklyLoading = document.getElementById('weekly-loading');

        if (!weeklyForecast || !weeklyDataContainer) return;

        // 週間予報パネルを表示
        weeklyForecast.style.display = 'block';
        this.isWeeklyForecastVisible = true;

        // ローディング表示を非表示にする
        if (weeklyLoading) {
            weeklyLoading.style.display = 'none';
        }

        // グラフ用データを保存
        this.weeklyDataForChart = weeklyData;

        // 日本語の曜日マッピング
        const dayNames = {
            'Monday': '月',
            'Tuesday': '火',
            'Wednesday': '水',
            'Thursday': '木',
            'Friday': '金',
            'Saturday': '土',
            'Sunday': '日'
        };

        // 週間予報データを表示
        let weeklyHTML = '';
        weeklyData.forEach((dayData, index) => {
            const weatherCode = dayData.weather_code ? dayData.weather_code.toString() : '100';
            const iconClass = this.weatherIconMap[weatherCode] || 'fas fa-sun';
            const weatherName = this.weatherCodeMap[weatherCode] || '天気情報不明';
            const temperature = dayData.temperature !== undefined && dayData.temperature !== '--' ?
                `${dayData.temperature}°C` : '--°C';
            const precipitation_prob = dayData.precipitation_prob !== undefined &&
                dayData.precipitation_prob !== '--' &&
                dayData.precipitation_prob !== null ?
                `${dayData.precipitation_prob}%` : '--';

            // 日付処理
            const date = new Date(dayData.date);
            const dayName = dayNames[dayData.day_of_week] || dayData.day_of_week.substring(0, 1);
            const dateStr = `${date.getMonth() + 1}/${date.getDate()}`;

            // 今日かどうかを判定
            const isToday = index === 0;
            const dayClass = isToday ? 'weekly-day today' : 'weekly-day';

            weeklyHTML += `
                <div class="${dayClass}">
                    <div class="day-info">
                        <div class="day-name">${isToday ? '今日' : dayName}</div>
                        <div class="day-date">${dateStr}</div>
                    </div>
                    <div class="day-weather">
                        <i class="${iconClass}"></i>
                    </div>
                    <div class="day-temp">${temperature}</div>
                    <div class="day-precipitation_prob">
                        <i class="fas fa-umbrella"></i>
                        ${precipitation_prob}
                    </div>
                </div>
            `;
        });

        weeklyDataContainer.innerHTML = weeklyHTML;
        weeklyDataContainer.style.display = 'block';
    }

    // タブ切り替え
    switchTab(tabType) {
        console.log('タブ切り替え:', tabType);

        // タブボタンのアクティブ状態を更新
        const tabBtns = document.querySelectorAll('.tab-btn');
        tabBtns.forEach(btn => {
            btn.classList.remove('active');
            if (btn.dataset.tab === tabType) {
                btn.classList.add('active');
            }
        });

        // タブコンテンツの表示切り替え
        const tabContents = document.querySelectorAll('.tab-content');
        tabContents.forEach(content => {
            content.classList.remove('active');
        });

        const targetContent = document.getElementById(`weekly-${tabType}-view`);
        if (targetContent) {
            targetContent.classList.add('active');

            // グラフタブが選択された場合、複合グラフを描画
            if (tabType === 'chart' && this.weeklyDataForChart) {
                setTimeout(() => {
                    this.drawChart('combined');
                }, 100);
            }
        }
    }

    // チャートタイプ切り替え
    switchChartType(chartType) {
        console.log('チャートタイプ切り替え:', chartType);

        this.currentChartType = chartType;

        // チャートタブボタンのアクティブ状態を更新
        const chartTabBtns = document.querySelectorAll('.chart-tab-btn');
        chartTabBtns.forEach(btn => {
            btn.classList.remove('active');
            if (btn.dataset.chart === chartType) {
                btn.classList.add('active');
            }
        });

        // グラフを再描画
        if (this.weeklyDataForChart) {
            this.drawChart(chartType);
        }
    }

    // グラフ描画
    drawChart(chartType) {
        if (!this.weeklyDataForChart || !Chart) {
            console.warn('グラフデータまたはChart.jsが利用できません');
            return;
        }

        const canvas = document.getElementById('weather-chart');
        if (!canvas) {
            console.warn('グラフキャンバスが見つかりません');
            return;
        }

        // 既存のチャートを破棄
        if (this.currentChart) {
            this.currentChart.destroy();
        }

        const ctx = canvas.getContext('2d');

        // データ準備
        const labels = this.weeklyDataForChart.map((day, index) => {
            if (index === 0) return '今日';
            const date = new Date(day.date);
            return `${date.getMonth() + 1}/${date.getDate()}`;
        });

        const temperatures = this.weeklyDataForChart.map(day =>
            day.temperature !== undefined && day.temperature !== '--' ? parseFloat(day.temperature) : null
        );

        const precipitation_probs = this.weeklyDataForChart.map(day =>
            day.precipitation_prob !== undefined && day.precipitation_prob !== '--' && day.precipitation_prob !== null ?
            parseFloat(day.precipitation_prob) : 0
        );

        // チャート設定（CSS変数を使用）
        const commonOptions = {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: true,
                    position: 'top',
                    labels: {
                        font: {
                            family: "'SF Pro Display', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
                            size: 12
                        },
                        usePointStyle: true,
                        padding: 15,
                        color: '#2d3436'
                    }
                },
                tooltip: {
                    mode: 'index',
                    intersect: false,
                    backgroundColor: 'rgba(255, 255, 255, 0.95)',
                    titleColor: '#2d3436',
                    bodyColor: '#636e72',
                    borderColor: 'rgba(102, 126, 234, 0.2)',
                    borderWidth: 1,
                    cornerRadius: 8,
                    displayColors: true
                }
            },
            scales: {
                x: {
                    grid: {
                        display: false
                    },
                    ticks: {
                        font: {
                            family: "'SF Pro Display', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
                            size: 11
                        },
                        color: '#636e72'
                    }
                },
                y: {
                    grid: {
                        color: 'rgba(182, 190, 195, 0.3)',
                        lineWidth: 1
                    },
                    ticks: {
                        font: {
                            family: "'SF Pro Display', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
                            size: 11
                        },
                        color: '#636e72'
                    }
                }
            }
        };

        let chartConfig;

        switch (chartType) {
            case 'temperature':
                chartConfig = {
                    type: 'line',
                    data: {
                        labels: labels,
                        datasets: [{
                            label: '気温 (°C)',
                            data: temperatures,
                            borderColor: '#667eea',
                            backgroundColor: 'rgba(102, 126, 234, 0.1)',
                            borderWidth: 3,
                            fill: true,
                            tension: 0.4,
                            pointBackgroundColor: '#667eea',
                            pointBorderColor: '#ffffff',
                            pointBorderWidth: 2,
                            pointRadius: 6,
                            pointHoverRadius: 8
                        }]
                    },
                    options: {
                        ...commonOptions,
                        scales: {
                            ...commonOptions.scales,
                            y: {
                                ...commonOptions.scales.y,
                                title: {
                                    display: true,
                                    text: '気温 (°C)',
                                    font: {
                                        family: "'SF Pro Display', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
                                        size: 12
                                    },
                                    color: this.getCSSVariable('--chart-text-secondary')
                                }
                            }
                        }
                    }
                };
                break;

            case 'precipitation_prob':
                chartConfig = {
                    type: 'bar',
                    data: {
                        labels: labels,
                        datasets: [{
                            label: '降水確率 (%)',
                            data: precipitation_probs,
                            backgroundColor: precipitation_probs.map(val =>
                                val >= 70 ? 'rgba(231, 76, 60, 0.8)' :
                                val >= 50 ? 'rgba(230, 126, 34, 0.8)' :
                                val >= 30 ? 'rgba(241, 196, 15, 0.8)' :
                                'rgba(52, 152, 219, 0.8)'
                            ),
                            borderColor: precipitation_probs.map(val =>
                                val >= 70 ? '#e74c3c' :
                                val >= 50 ? '#e67e22' :
                                val >= 30 ? '#f1c40f' :
                                '#3498db'
                            ),
                            borderWidth: 2,
                            borderRadius: 4,
                            borderSkipped: false
                        }]
                    },
                    options: {
                        ...commonOptions,
                        scales: {
                            ...commonOptions.scales,
                            y: {
                                ...commonOptions.scales.y,
                                min: 0,
                                max: 100,
                                title: {
                                    display: true,
                                    text: '降水確率 (%)',
                                    font: {
                                        family: "'SF Pro Display', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
                                        size: 12
                                    },
                                    color: this.getCSSVariable('--chart-text-secondary')
                                }
                            }
                        }
                    }
                };
                break;

            case 'combined':
                chartConfig = {
                    type: 'line',
                    data: {
                        labels: labels,
                        datasets: [{
                                label: '気温 (°C)',
                                data: temperatures,
                                borderColor: '#667eea',
                                backgroundColor: 'rgba(102, 126, 234, 0.1)',
                                borderWidth: 3,
                                fill: false,
                                tension: 0.4,
                                pointBackgroundColor: '#667eea',
                                pointBorderColor: '#ffffff',
                                pointBorderWidth: 2,
                                pointRadius: 6,
                                pointHoverRadius: 8,
                                yAxisID: 'y'
                            },
                            {
                                label: '降水確率 (%)',
                                data: precipitation_probs,
                                type: 'bar',
                                backgroundColor: 'rgba(79, 172, 254, 0.6)',
                                borderColor: '#4facfe',
                                borderWidth: 1,
                                borderRadius: 3,
                                yAxisID: 'y1'
                            }
                        ]
                    },
                    options: {
                        ...commonOptions,
                        scales: {
                            x: commonOptions.scales.x,
                            y: {
                                ...commonOptions.scales.y,
                                type: 'linear',
                                display: true,
                                position: 'left',
                                title: {
                                    display: true,
                                    text: '気温 (°C)',
                                    font: {
                                        family: "'SF Pro Display', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
                                        size: 12
                                    },
                                    color: this.getCSSVariable('--chart-text-secondary')
                                }
                            },
                            y1: {
                                ...commonOptions.scales.y,
                                type: 'linear',
                                display: true,
                                position: 'right',
                                min: 0,
                                max: 100,
                                title: {
                                    display: true,
                                    text: '降水確率 (%)',
                                    font: {
                                        family: "'SF Pro Display', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
                                        size: 12
                                    },
                                    color: this.getCSSVariable('--chart-text-secondary')
                                },
                                grid: {
                                    drawOnChartArea: false
                                }
                            }
                        }
                    }
                };
                break;

            default:
                console.warn('不明なチャートタイプ:', chartType);
                return;
        }

        // チャートを作成
        try {
            this.currentChart = new Chart(ctx, chartConfig);
            console.log('グラフ描画完了:', chartType);
        } catch (error) {
            console.error('グラフ描画エラー:', error);
        }
    }

    // 週間予報データ表示（従来のメソッド）
    displayWeeklyForecast(weeklyData) {
        const weeklyDataContainer = document.getElementById('weekly-data');
        if (!weeklyDataContainer) return;

        // 日本語の曜日マッピング
        const dayNames = {
            'Monday': '月',
            'Tuesday': '火',
            'Wednesday': '水',
            'Thursday': '木',
            'Friday': '金',
            'Saturday': '土',
            'Sunday': '日'
        };

        // 週間予報データを表示
        let weeklyHTML = '';
        weeklyData.forEach((dayData, index) => {
            const weatherCode = dayData.weather_code ? dayData.weather_code.toString() : '100';
            const iconClass = this.weatherIconMap[weatherCode] || 'fas fa-sun';
            const weatherName = this.weatherCodeMap[weatherCode] || '天気情報不明';
            const temperature = dayData.temperature !== undefined && dayData.temperature !== '--' ?
                `${dayData.temperature}°C` : '--°C';
            const precipitation_prob = dayData.precipitation_prob !== undefined &&
                dayData.precipitation_prob !== '--' &&
                dayData.precipitation_prob !== null ?
                `${dayData.precipitation_prob}%` : '--';

            // 日付処理
            const date = new Date(dayData.date);
            const dayName = dayNames[dayData.day_of_week] || dayData.day_of_week.substring(0, 1);
            const dateStr = `${date.getMonth() + 1}/${date.getDate()}`;

            // 今日かどうかを判定
            const isToday = index === 0;
            const dayClass = isToday ? 'weekly-day today' : 'weekly-day';

            weeklyHTML += `
                <div class="${dayClass}">
                    <div class="day-info">
                        <div class="day-name">${isToday ? '今日' : dayName}</div>
                        <div class="day-date">${dateStr}</div>
                    </div>
                    <div class="day-weather">
                        <i class="${iconClass}"></i>
                    </div>
                    <div class="day-temp">${temperature}</div>
                    <div class="day-precipitation_prob">
                        <i class="fas fa-umbrella"></i>
                        ${precipitation_prob}
                    </div>
                </div>
            `;
        });

        weeklyDataContainer.innerHTML = weeklyHTML;
        weeklyDataContainer.style.display = 'block';
    }

    // 災害情報を取得して表示
    async fetchDisasterInfo(areaCode) {
        try {
            const response = await fetch('/disaster_info', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ area_code: areaCode })
            });
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();
            if (data.status === 'ok') {
                this.displayDisasterInfo(data.disaster);
            } else {
                this.displayDisasterInfo([]);
            }
        } catch (error) {
            console.error('災害情報取得エラー:', error);
            this.displayDisasterInfo([]);
        }
    }

    // 災害情報表示
    displayDisasterInfo(list) {
        const container = document.getElementById('disaster-info');
        if (!container) return;
        if (list && list.length > 0) {
            container.innerHTML = '<ul>' + list.map(d => `<li>${d}</li>`).join('') + '</ul>';
        } else {
            container.innerHTML = '<p>災害情報はありません</p>';
        }
        container.style.display = 'block';
    }

    // 週間予報エラー処理
    handleWeeklyForecastError(errorCode = null) {
        const weeklyDataContainer = document.getElementById('weekly-data');
        if (!weeklyDataContainer) return;

        // エラー時のダミーデータを表示
        const message = this.getErrorMessage(errorCode);
        const errorHTML = `
            <div class="weekly-error">
                <div style="text-align: center; padding: 20px; color: var(--text-secondary);">
                    <i class="fas fa-exclamation-triangle" style="font-size: 24px; margin-bottom: 10px;"></i>
                    <div>${message}</div>
                    <div style="font-size: 12px; margin-top: 5px;">しばらく時間をおいて再度お試しください</div>
                </div>
            </div>
        `;

        weeklyDataContainer.innerHTML = errorHTML;
        weeklyDataContainer.style.display = 'block';
        this.weeklyDataForChart = null;
    }
}

// パーティクルシステム管理クラス
class ParticleSystemManager {
    constructor() {
        this.particles = [];
        this.container = document.getElementById('particle-system');
        this.maxParticles = 50;
        this.intervalId = null;
    }

    createParticle(type) {
        if (!this.container || this.particles.length >= this.maxParticles) return;

        const particle = document.createElement('div');
        const windowWidth = window.innerWidth;
        const windowHeight = window.innerHeight;

        switch (type) {
            case 'rain':
                particle.className = 'rain-particle';
                particle.style.left = Math.random() * (windowWidth + 100) - 50 + 'px';
                particle.style.top = '-20px';
                particle.style.animationDuration = (Math.random() * 0.5 + 0.5) + 's';
                break;

            case 'snow':
                particle.className = 'snow-particle';
                particle.style.left = Math.random() * (windowWidth + 100) - 50 + 'px';
                particle.style.top = '-20px';
                particle.style.animationDuration = (Math.random() * 2 + 2) + 's';
                break;

            case 'wind':
                particle.className = 'wind-particle';
                particle.style.left = '-50px';
                particle.style.top = Math.random() * windowHeight + 'px';
                particle.style.animationDuration = (Math.random() * 1 + 1) + 's';
                break;
        }

        this.container.appendChild(particle);
        this.particles.push(particle);

        // アニメーション終了後に削除
        particle.addEventListener('animationend', () => {
            this.removeParticle(particle);
        });
    }

    removeParticle(particle) {
        const index = this.particles.indexOf(particle);
        if (index > -1) {
            this.particles.splice(index, 1);
            if (particle.parentNode) {
                particle.parentNode.removeChild(particle);
            }
        }
    }

    startEffect(type) {
        this.stopEffect();

        const createParticleInterval = () => {
            this.createParticle(type);
        };

        // パーティクル生成間隔
        let interval;
        switch (type) {
            case 'rain':
                interval = 100;
                break;
            case 'snow':
                interval = 200;
                break;
            case 'wind':
                interval = 300;
                break;
            default:
                return;
        }

        this.intervalId = setInterval(createParticleInterval, interval);
    }

    stopEffect() {
        if (this.intervalId) {
            clearInterval(this.intervalId);
            this.intervalId = null;
        }

        // 既存のパーティクルを削除
        this.particles.forEach(particle => {
            if (particle.parentNode) {
                particle.parentNode.removeChild(particle);
            }
        });
        this.particles = [];
    }
}

// グローバル関数（HTML側で使用する場合）
window.toggleSidebar = function() {
    const sidebar = document.getElementById('sidebar');
    if (sidebar) {
        sidebar.classList.toggle('active');
    }
};

// アプリケーション初期化
let weatherApp;

// DOMロード完了後に初期化
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM読み込み完了 - WeatherApp初期化開始');
    weatherApp = new WeatherApp();
});

// ウィンドウロード完了後にも初期化（保険）
window.addEventListener('load', function() {
    if (!weatherApp) {
        console.log('ウィンドウロード完了 - WeatherApp再初期化');
        weatherApp = new WeatherApp();
    }
});

// エクスポート（モジュール使用時）
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { WeatherApp, ParticleSystemManager };
}

# C++ ReportClient 実装計画

## 📋 概要

Python版 `ReportClient` の分析に基づき、C++版ReportClientの実装計画を策定しました。Python版はシンプルでIoT機器向けの基本的なセンサーデータ送信機能に特化している一方、現在のC++ヘッダーは過度に複雑化しています。

## 🔍 Python版 ReportClient 分析結果

### 基本構造
- **目的**: IoT機器からサーバーへのセンサーデータプッシュ配信
- **プロトコル**: Type 4 (ReportRequest) → Type 5 (ReportResponse)
- **認証**: 環境変数ベースの簡単なパスフレーズ認証
- **通信**: 単一UDP送信（バッチ処理なし）

### 主要機能
1. **データ設定**: `set_sensor_data()`, `set_area_code()` など個別設定メソッド
2. **データ送信**: `send_report_data()` 同期送信、`send_report_data_async()` 非同期送信
3. **データ管理**: `get_current_data()`, `clear_data()` でメンバ変数管理
4. **デバッグ**: 統一デバッグロガー使用
5. **認証**: 環境変数 `REPORT_SERVER_PASSPHRASE` によるシンプル認証

### センサーデータフィールド
- `area_code`: エリアコード（文字列/数値）
- `weather_code`: 天気コード（オプション）
- `temperature`: 気温（摂氏、オプション）
- `precipitation_prob`: 降水確率（0-100%、オプション）
- `alert`: 警報情報リスト（オプション）
- `disaster`: 災害情報リスト（オプション）

### パケット形式
- **ReportRequest**: Type 4、拡張フィールドで警報・災害情報
- **ReportResponse**: Type 5、ACK応答またはデータ付き応答

---

## 🚨 現在のC++実装の問題点

### 過度な複雑化
現在の `report_client.hpp` は以下の不要な機能を含んでいます：

❌ **Python版に存在しない機能（削除対象）**
- バッチ処理・キューイング機能
- データ圧縮・暗号化
- パフォーマンスメトリクス・統計収集
- バックプレッシャー制御
- 重複検出機能
- 自動リトライ・サーキットブレーカー
- ファクトリーパターン
- 複雑な非同期処理

### 互換性の欠如
- Python版とのAPI互換性なし
- パケット形式の相違
- 認証方式の相違

---

## 🎯 実装計画

### Phase 1: 基盤整備 (1週間) ✅ **完了** (2025-01-17)

#### 1.1 パケット構造の修正
- [x] **Python互換ReportPacket作成**
  - [x] `cpp/include/wiplib/packet/report_packet_compat.hpp` 新規作成
  - [x] Python版 `ReportRequest`/`ReportResponse` と同等のパケット構造
  - [x] Type 4/Type 5 パケット対応
  - [x] 拡張フィールド（alert/disaster）対応

#### 1.2 基本データ構造定義
- [x] **SensorData構造体の簡素化**
  - [x] Python版と同等のフィールドのみ
  - [x] 不要なデータ品質・圧縮フィールド削除
  - [x] `std::optional` で各フィールドをオプション化

#### 1.3 CMake統合とビルドシステム
- [x] **CMakeLists.txt更新**
  - [x] `src/packet/report_packet_compat.cpp` 追加
  - [x] PacketType enum拡張（Type 4/5/6/7対応）
  - [x] Flags構造体のPython互換性修正
  - [x] 基本ビルド確認完了

### Phase 2: シンプルなReportClient実装 (1-2週間)

#### 2.1 基本クライアント実装
- [x] **cpp/include/wiplib/client/simple_report_client.hpp** 作成
  ```cpp
  class SimpleReportClient {
  public:
      SimpleReportClient(std::string host = "localhost", uint16_t port = 4112, bool debug = false);
      
      // Python互換API
      void set_sensor_data(const std::string& area_code, 
                          std::optional<int> weather_code = {},
                          std::optional<float> temperature = {},
                          std::optional<int> precipitation_prob = {},
                          std::optional<std::vector<std::string>> alert = {},
                          std::optional<std::vector<std::string>> disaster = {});
      
      void set_area_code(const std::string& area_code);
      void set_weather_code(int weather_code);
      void set_temperature(float temperature);
      void set_precipitation_prob(int precipitation_prob);
      void set_alert(const std::vector<std::string>& alert);
      void set_disaster(const std::vector<std::string>& disaster);
      
      wiplib::Result<ReportResult> send_report_data();
      std::future<wiplib::Result<ReportResult>> send_report_data_async();
      
      std::map<std::string, std::any> get_current_data() const;
      void clear_data();
      void close();
      
  private:
      std::string host_;
      uint16_t port_;
      bool debug_;
      
      // センサーデータ（Python版と同様にメンバ変数で保持）
      std::optional<std::string> area_code_;
      std::optional<int> weather_code_;
      std::optional<float> temperature_;
      std::optional<int> precipitation_prob_;
      std::optional<std::vector<std::string>> alert_;
      std::optional<std::vector<std::string>> disaster_;
      
      // 認証設定
      bool auth_enabled_;
      std::string auth_passphrase_;
  };
  ```

#### 2.2 認証機能統合
- [x] **環境変数ベース認証**
  - `REPORT_SERVER_REQUEST_AUTH_ENABLED`
  - `REPORT_SERVER_PASSPHRASE`
  - Python版と同等の認証フロー

#### 2.3 実装ファイル作成
- [x] **cpp/src/client/simple_report_client.cpp** 実装
  - [x] UDP通信実装
  - [x] パケット送受信処理（ID割当・DNS解決対応）
  - [x] エラーハンドリング
  - [x] デバッグログ統合

### Phase 3: Python互換性確保 (1週間) ✅ **完了** (2025-01-19)

#### 3.1 API互換性テスト
- [x] **Python版との動作比較テスト** ✅
  - [x] 同一データでのパケット形式比較
  - [x] レスポンス処理の比較
  - [x] エラーハンドリングの比較
  - [x] `tests/integration/test_simple_report_client.cpp` 作成

#### 3.2 統合とテスト
- [x] **CMakeLists.txt更新** ✅
  - [x] `src/client/simple_report_client.cpp` 追加済み
  - [x] `tests/integration/test_simple_report_client.cpp` 追加
  - [x] テストビルド確認完了

#### 3.3 ドキュメント作成
- [x] **使用例とチュートリアル** ✅
  - [x] Python版と同等の使用例 (`examples/simple_report_client_tutorial.cpp`)
  - [x] API変換ガイド (`docs/PYTHON_TO_CPP_MIGRATION_GUIDE.md`)
  - [x] 完全なコード例とベストプラクティス

### Phase 4: 高度機能（オプション） (1週間)

#### 4.1 便利機能追加
- [ ] **一括送信関数**
  ```cpp
  wiplib::Result<ReportResult> send_sensor_report(
      const std::string& area_code,
      std::optional<int> weather_code = {},
      std::optional<float> temperature = {},
      std::optional<int> precipitation_prob = {},
      // ... 他のパラメータ
      const std::string& host = "localhost",
      uint16_t port = 4112,
      bool debug = false
  );
  ```

#### 4.2 既存Client統合
- [ ] **`Client` クラスにReportClient統合**
  - Python版 `Client` との互換性確保
  - 統一インターフェース提供

---

## 📁 ファイル構成

### Phase 1で作成されたファイル ✅
```
cpp/
├── include/wiplib/packet/
│   ├── report_packet_compat.hpp          # Python互換パケット定義 ✅
│   └── types.hpp                         # パケット型拡張 ✅
└── src/packet/
    └── report_packet_compat.cpp          # Python互換パケット実装 ✅
```

### Phase 1で修正されたファイル ✅
- `cpp/CMakeLists.txt` - report_packet_compat.cpp追加 ✅
- `cpp/include/wiplib/packet/types.hpp` - Type 4/5/6/7追加、Flagsフィールド名修正 ✅
- `cpp/src/packet/codec.cpp` - Flagsフィールド名対応 ✅
- `cpp/src/client/weather_client.cpp` - Flagsフィールド名対応 ✅
- `cpp/src/client/query_client.cpp` - Flagsフィールド名対応 ✅
- `cpp/src/utils/auth.cpp` - Flagsフィールド名対応 ✅

### Phase 2以降で予定されているファイル
```
cpp/
├── include/wiplib/client/
│   └── simple_report_client.hpp          # シンプルなReportClient（未実装）
├── src/client/
│   └── simple_report_client.cpp          # 実装ファイル（未実装）
└── tests/integration/
    └── test_simple_report_client.cpp     # テストファイル（未実装）
```

---

## 🚀 期待される成果

### ✅ Python完全互換性
- API・パケット形式・認証方式の完全一致
- 既存Pythonコードの移植が容易

### ✅ シンプルで保守しやすい実装
- 過度な複雑化を回避
- Python版の設計思想を維持

### ✅ 段階的な実装
- 基本機能から開始
- 必要に応じて機能拡張

### ✅ パフォーマンス向上
- C++によるネイティブ実装
- Python版より高速な処理

---

## 📊 工数見積もり

| Phase | 内容 | 推定工数 | 優先度 |
|-------|------|----------|--------|
| Phase 1 | 基盤整備 | 1週間 | ★★★ |
| Phase 2 | 基本実装 | 1-2週間 | ★★★ |
| Phase 3 | 互換性確保 | 1週間 | ★★★ |
| Phase 4 | 高度機能 | 1週間 | ★☆☆ |

**合計: 4-5週間**

---

## 🔄 実装方針

### 段階的アプローチ
1. **最小機能版**: Python版と同等の基本機能のみ
2. **互換性確保**: 完全なPython互換性達成
3. **機能拡張**: 必要に応じて追加機能実装

### 品質保証
- Python版との比較テスト
- 単体・統合テスト
- ドキュメント整備

この計画により、Python版ReportClientと完全互換性を持つ、シンプルで保守しやすいC++実装が実現できます。

# C++版WIPクライアントの実行方法

## 概要
C++版のWIPクライアントは既にビルド済みで、実行可能ファイルが以下の場所にあります：
- メインクライアント: `cpp/build/wip_client_cli`
- テストプログラム: `cpp/build/wiplib_tests`
- パケット生成ツール: `cpp/build/wip_packet_gen`
- パケットデコードツール: `cpp/build/wip_packet_decode`

## 認証設定の修正内容

**Python互換の環境変数サポート**：
- C++クライアントが`QUERY_GENERATOR_REQUEST_AUTH_ENABLED`と`QUERY_SERVER_PASSPHRASE`を使用するように修正
- `WIP_CLIENT_AUTH_ENABLED`は使用しない

修正ファイル: `cpp/src/utils/auth_config.cpp`

## 実行方法

### 1. メインクライアント (wip_client_cli)

#### Python互換の環境変数使用
```bash
# 認証を有効にして実行
export QUERY_GENERATOR_REQUEST_AUTH_ENABLED=true
export QUERY_SERVER_PASSPHRASE=your_passphrase
./cpp/build/wip_client_cli --host 127.0.0.1 --port 4111 --area 130010

# 実行例
export QUERY_GENERATOR_REQUEST_AUTH_ENABLED=true
export QUERY_SERVER_PASSPHRASE=test
./cpp/build/wip_client_cli --host 127.0.0.1 --port 4111 --area 130010 --weather --temperature
```

#### 基本構文
```bash
# エリアコード指定
./cpp/build/wip_client_cli --host <HOST> --port <PORT> --area <AREA_CODE> [flags]

# 座標指定
./cpp/build/wip_client_cli --host <HOST> --port <PORT> --coords <LAT> <LON> [flags]
```

#### 実行例
```bash
# エリアコード指定で天気と気温を取得
./cpp/build/wip_client_cli --host 127.0.0.1 --port 4110 --area 130010 --weather --temperature

# 座標指定で天気情報を取得
./cpp/build/wip_client_cli --host 127.0.0.1 --port 4110 --coords 35.6895 139.6917 --weather

# 降水確率や災害情報も含めて取得
./cpp/build/wip_client_cli --host 127.0.0.1 --port 4110 --area 011000 --weather --temperature --precipitation --disaster
```

#### 利用可能なフラグ
- `--weather` (デフォルト有効): 天気情報を取得
- `--no-weather`: 天気情報を無効化
- `--temperature` (デフォルト有効): 気温情報を取得
- `--no-temperature`: 気温情報を無効化
- `--precipitation`: 降水確率を取得
- `--alerts`: 警報情報を取得
- `--disaster`: 災害情報を取得
- `--day <0-7>`: 予報日数を指定

#### 認証関連オプション
```bash
# 認証を有効にする
./cpp/build/wip_client_cli --host 127.0.0.1 --port 4111 --area 130010 --auth-enabled

# 認証を無効にする
./cpp/build/wip_client_cli --host 127.0.0.1 --port 4111 --area 130010 --no-auth-enabled

# レスポンス検証を有効にする
./cpp/build/wip_client_cli --host 127.0.0.1 --port 4111 --area 130010 --verify-response

# 認証パスワードを直接指定
./cpp/build/wip_client_cli --host 127.0.0.1 --port 4111 --area 130010 --auth-query <PASSPHRASE>
```

### 2. テストプログラム
```bash
./cpp/build/wiplib_tests
```

### 3. パケット操作ツール
```bash
# パケット生成
./cpp/build/wip_packet_gen

# パケットデコード
./cpp/build/wip_packet_decode

# ラウンドトリップテスト
./cpp/build/wip_packet_roundtrip
```

## ビルド方法（必要な場合）

### CMakeを使用
```bash
# 設定
cmake -S cpp -B cpp/build -DCMAKE_BUILD_TYPE=Release

# ビルド
cmake --build cpp/build --config Release -j
```

### CMakeを使わない簡易ビルド
```bash
# Linuxの場合
./cpp/tools/build_no_cmake.sh

# Windowsの場合
./cpp/tools/build_no_cmake.bat
```

## トラブルシューティング

### 認証が動作しない場合
1. 環境変数が正しく設定されているか確認
2. パスフレーズが正しいか確認
3. サーバーが認証を要求しているか確認

### ビルドエラーが発生する場合
1. compatibilityモジュールのエラーは無視可能
2. 主要なクライアント機能は正常に動作
3. 必要に応じてCMakeなしビルドを使用
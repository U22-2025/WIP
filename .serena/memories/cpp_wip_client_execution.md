# C++版WIPクライアントの実行方法

## 概要
C++版のWIPクライアントは既にビルド済みで、実行可能ファイルが以下の場所にあります：
- メインクライアント: `cpp/build/wip_client_cli`
- テストプログラム: `cpp/build/wiplib_tests`
- パケット生成ツール: `cpp/build/wip_packet_gen`
- パケットデコードツール: `cpp/build/wip_packet_decode`

## 実行方法

### 1. メインクライアント (wip_client_cli)

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
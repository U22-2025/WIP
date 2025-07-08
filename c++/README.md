# C++ Implementation

このフォルダには `common` と `WIP_Client` パッケージの簡易C++実装を収録しています。
Python版を参考にクラス構成のみ再現した軽量なサンプルです。

## 依存
- C++17
- OpenSSL (HMAC計算に使用)
- OpenSSL 開発パッケージ (例: libssl-dev)
- [nlohmann/json](https://github.com/nlohmann/json)

## ビルド例
```bash
mkdir build && cd build
cmake .. && make
```
OpenSSL の開発パッケージがインストールされていない場合、`cmake ..` でエラーになります。

単一ファイルを直接 `g++` でビルドする場合は、必ず `-std=c++17` オプションを指定してください。

ビルド後、`wip_example` 実行ファイルを使用すると Python 版 `client.py` と同様の挙動を簡易的に試せます。

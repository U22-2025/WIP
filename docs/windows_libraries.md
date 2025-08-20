# Windows向け依存ライブラリ

WIP の C++ コンポーネントで将来的に利用予定の外部ライブラリについて、
Windows での入手方法と `find_package` が探索するパスの設定方法をまとめる。

## Boost
- **バイナリ配布**: 公式の [boost-binaries](https://sourceforge.net/projects/boost/files/boost-binaries/) で各バージョンの Windows 用ビルドが提供されている。`choco install boost` や `vcpkg install boost` でも取得可能。
- **CMake での検出**: `BOOST_ROOT` 環境変数、または `-DBOOST_ROOT=C:/local/boost_1_84_0` のようにパスを指定する。
- **見つからない場合**: `bootstrap.bat` → `b2` でソースからビルドする。代替としては `asio` 単体版の利用を検討する。

## OpenSSL
- **バイナリ配布**: [slproweb](https://slproweb.com/products/Win32OpenSSL.html) が Win32/Win64 向けのインストーラを提供。`choco install openssl` や `vcpkg install openssl` も利用可能。
- **CMake での検出**: `OPENSSL_ROOT_DIR` に `C:/OpenSSL-Win64` などのインストール先を設定する。
  例: `cmake -S cpp -B build -DOPENSSL_ROOT_DIR=C:/OpenSSL-Win64`
- **見つからない場合**: ソースから `perl Configure` → `nmake` でビルドする。軽量代替として [LibreSSL](https://www.libressl.org/) の利用も可能。

これらのパスは `cpp/CMakeLists.txt` でデフォルト値を設定しており、必要に応じて上書きできる。

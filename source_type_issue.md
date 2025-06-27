# sourceフィールド型不一致問題

## 1. 問題概要
パケット処理におけるsourceフィールドの型不一致

## 2. 原因分析
`ExtendedField`クラスの型制限

## 3. 影響ファイル
- `common/packet/format_base.py`
- `common/packet/format_extended.py`
- `common/packet/request.py`
- サーバー実装ファイル：
  - [`WIP_Server/servers/query_server/query_server.py`](WIP_Server/servers/query_server/query_server.py)
  - [`WIP_Server/servers/location_server/location_server.py`](WIP_Server/servers/location_server/location_server.py)
- クライアント実装ファイル：
  - [`WIP_Client/client.py`](WIP_Client/client.py)
  - `common/clients/`ディレクトリ配下の関連ファイル

## 5. サーバー/クライアント側の対応

型統一の実装後、以下の対応が必要です：

- **サーバー側**:
  - 取得したsource値の使用箇所でタプル型を想定した処理に変更
  - デバッグ出力のフォーマット修正
  - レスポンス生成時のsource設定処理変更不要（内部で自動変換）

- **クライアント側**:
  - パケット生成時にsourceをタプル型で設定
  - 受信したsource値をタプル型として扱う
  - 既存の文字列ベースの処理を移行

- **移行手順**:
  1. 共通パケットライブラリの型統一を実装
  2. 全サーバー/クライアントの依存ライブラリを更新
  3. サーバー/クライアントコードを段階的に移行

## 4. 改善提案
- セッターの修正：タプル型`(ip, port)`を受け入れる
- `to_bytes`処理：タプル→文字列変換の自動化
- `from_bytes`処理：文字列→タプル変換の追加
- サーバー/クライアント実装の移行ガイドライン作成
- 段階的なロールアウト計画の策定

## 6. 実装例（疑似コード）

```python
# タプル型を受け入れるセッターの修正
@source.setter
def source(self, value):
    if isinstance(value, tuple):
        self._source = f"{value[0]}:{value[1]}"
    else:
        self._source = value

# デシリアライズ時の変換処理追加
def from_bytes(data):
    # ...既存処理...
    if key == "source":
        ip, port = value.split(":")
        return (ip, int(port))
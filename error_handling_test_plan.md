# エラーハンドリング機能 テスト計画書

## 1. テストの目的
コミット `d52c58b` で実装されたエラーハンドリング機能が仕様通り動作することを検証する

## 2. テスト対象機能
- エラーパケット生成・送信機能 (`BaseServer._handle_error()`)
- エラーパケット転送機能 (`WeatherServer._handle_error_packet()`)
- エラーレスポンスクラスの実装 (`ErrorResponse`)

## 3. テスト環境
- OS: Windows 11 / Linux
- Python: 3.10+
- テストフレームワーク: pytest
- ネットワーク環境: ローカルループバックアドレス (127.0.0.1)

## 4. テストケース

### 4.1 単体テスト

#### `common/packet/error_response.py`
```python
def test_error_response_serialization():
    # エラーパケットのシリアライズ/デシリアライズテスト
    packet = ErrorResponse()
    packet.packet_id = 123
    packet.error_code = 0x0001
    packet.ex_field.set('source_ip', '192.168.1.1')
    
    serialized = packet.serialize()
    new_packet = ErrorResponse()
    new_packet.deserialize(serialized)
    
    assert new_packet.packet_id == 123
    assert new_packet.error_code == 0x0001
    assert new_packet.ex_field.get('source_ip') == '192.168.1.1'
```

#### `WIP_Server/servers/base_server.py`
```python
def test_handle_error_packet_creation():
    # エラーパケット生成ロジックテスト
    server = BaseServer()
    mock_packet = MagicMock(packet_id=456)
    addr = ('192.168.1.100', 5000)
    
    server._handle_error(0x0003, mock_packet, addr)
    
    # 送信されたパケットの内容を検証
    assert sent_packet.type == 7
    assert sent_packet.error_code == 0x0003
    assert sent_packet.ex_field.get('source_ip') == '192.168.1.100'
```

### 4.2 統合テスト

#### エラーパケット送信フロー
```gherkin
シナリオ: 無効なパケットを受信した場合のエラーハンドリング
  前提 BaseServerが起動している
  かつ WeatherServerが起動している
  もし クライアントが不正なパケットをBaseServerに送信した場合
  ならば BaseServerがErrorResponse(タイプ7)を送信する
  かつ パケット内のerror_codeが0x0001(無効なパケット形式)である
```

#### エラーパケット転送フロー
```gherkin
シナリオ: 天気サーバー経由のエラーパケット転送
  前提 WeatherServerがエラーパケットを受信している
  かつ パケットにsource_ipフィールドが含まれている
  ならば WeatherServerが指定されたsource_ipにエラーパケットを転送する
```

### 4.3 例外ケーステスト

1. **ソースIP不明ケース**:
   - アドレス情報がない場合に"0.0.0.0"が設定されることの検証
   - テスト手法: `addr` パラメータに非タプル値を渡してテスト

2. **パケットID欠如ケース**:
   - 元パケットにpacket_idがない場合の挙動検証
   - テスト手法: packet_id=Noneのモックパケットを使用

3. **拡張フィールド異常ケース**:
   - source_ipが15文字を超える場合の挙動検証
   - テスト手法: 長いIPアドレス(IPv6など)を渡してテスト

### 4.4 パフォーマンステスト

1. **高負荷時のエラーハンドリング**:
   - 1秒あたり100リクエストの負荷をかけてもエラーパケットが正しく生成・送信されること
   - メトリクス: エラーレスポンス遅延時間(99パーセンタイル)

## 5. テスト自動化計画

### 5.1 自動化対象
- 単体テスト (pytest)
- 統合テスト (Behave + pytest)
- パフォーマンステスト (Locust)

### 5.2 テストデータ管理
- 正規/不正規パケットデータをJSONファイルで管理
- エラーケースシナリオをYAMLで定義

### 5.3 継続的テスト
- CIパイプライン(GitHub Actions)への組み込み
- コミットごとにテストを自動実行

## 6. テスト進捗管理
| テスト種別     | 実施状況 | 合格基準                     |
|---------------|----------|------------------------------|
| 単体テスト     | 未実施   | カバレッジ80%以上            |
| 統合テスト     | 未実施   | 全シナリオ成功               |
| 例外ケーステスト| 未実施   | エラーログ出力確認          |
| パフォーマンス | 未実施   | 99%リクエストが100ms以下    |
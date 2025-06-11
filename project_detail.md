# プロジェクト詳細
### 使用言語・ツール
- PostgreSQL
- PostGIS
- Python

### サーバ構成
- WTPサーバ
  - クエリ生成
  - redis
- 座標

### 情報取得
#### 使用するデータ
- area.json
- Niigata_format.json

#### データの処理方法
1. 緯度・経度を座標解決サーバで地域コードに変換
    - 地域コードはarea.jsonの「`class10s`」内の各コードに対応
    - この地域コードの範囲に応じて気象サーバに振り分け

2. 

#### サーバ内でのデータの保存
- 地方 ( 関東・関西 )
    - データ取得時刻
        - 地域コード
            - 地方名
            - 天気
                - 7日間分
            - 気温
                - 7日間分
            - 降水確率
                - 7日間分
            - 注意報・警報
            - 災害情報

```
{
  "weather_pulldatetime": "2025-05-18T05:00:00+09:00",
  "disaster_pulldatetime":"",
  "alert_pulldatetime":"",
  "150010": {
    "parent_code": "150000",
    "area_name": "下越",
    "weather": ["101", "202"],
    "temperature": ["25, 26", "27"],
    "precipitation_prob": ["10%", "20%"],
    "warnings": [],
    "disaster_info": []
  }
}
```
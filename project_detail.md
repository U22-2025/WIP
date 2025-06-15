# プロジェクト詳細
### 使用言語・ツール
- 言語
  - Python
- DB
  - PostgreSQL
  - PostGIS
  - Redis
-  ツール
   - Cursor
   - ChatGPT
   - Claude
   - Gemini

### サーバ構成
- WTPサーバ
  - クエリ生成
  - redis
- 座標

### 情報取得
#### 使用するデータ
- [地域コード構成](https://www.jma.go.jp/bosai/common/const/area.json)
- [地方ごと気象情報](https://www.jma.go.jp/bosai/forecast/data/forecast/150000.json)
- [高頻度更新気象注意報・警報](https://www.data.jma.go.jp/developer/xml/feed/extra.xml)
- [随時更新災害情報](https://www.data.jma.go.jp/developer/xml/feed/eqvol.xml)
- [一次細分区域等の地域コードと座標の対応GISデータ](https://www.data.jma.go.jp/developer/gis.html) 
- 
#### データの処理方法
1. 緯度・経度を座標解決サーバで地域コードに変換
    - 地域コードはarea.jsonの「`class10s`」内の各コードに対応
      - 地域コード構造（area.json）
        - centers 地方
        - offices 都道府県
        - class10 都道府県内地方
        - class15 地域
        - class20 市町村

#### サーバ内でのデータの保存
- 災害情報取得時刻
- 気象注意報・警報取得時刻
- 地域コード
  - 気象情報報告時刻
  - 親コード
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
  "disaster_pulldatetime":"2025-05-18T05:00:00+09:00",
  "alert_pulldatetime":"2025-05-18T05:00:00+09:00",
  "150010": {
    "weather_reportdatetime": "2025-05-18T05:00:00+09:00",
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
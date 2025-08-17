``` mermaid

%%{ init : {
  "theme": "base",
  "themeVariables": {
    "fontSize": "24px",
    "fontWeight": "bold",
    "lineWidth": "3px",
    "primaryColor": "#cce6ff",
    "primaryBorderColor": "#3399ff",
    "edgeLabelBackground": "#ffffff",
    "textColor": "#003366"
  },
  "flowchart": {
    "nodeSpacing": 20,
    "rankSpacing": 20
  }
} }%%
flowchart TD

  subgraph Locations
    地方コード(地方コード) --> 都道府県コード(都道府県コード)
    都道府県コード --> 都道府県内地方コード(都道府県内地方コード)
    座標(座標) --> 都道府県内地方コード
    都道府県内地方コード --> 地域コード(地域コード)
    地域コード --> 市町村コード(市町村コード)
  end

  subgraph WeatherInformation
    都道府県コード --> 天気{天気}
    都道府県コード --> 降水確率{降水確率}
    都道府県内地方コード --> 天気
    都道府県内地方コード --> 降水確率
    市町村コード --> 気温{気温}
    都市コード(都市コード) --> 気温
  end

  subgraph DisasterInformation
    都道府県内地方コード --> 注意報{注意報}
    都道府県内地方コード --> 警報{警報}
    都道府県内地方コード --> 災害情報{災害情報}
    市町村コード --> 災害情報
    災害情報 --> 火山コード(火山コード)
    火山コード --> 座標
  end

  classDef commonStyle fill:#cce6ff,stroke:#3399ff,color:#003366;
  classDef infoStyle fill:#b3d9ff,stroke:#3399ff,color:#003366;
  classDef disasterStyle fill:#99ccff,stroke:#3399ff,color:#003366;

  class 地方コード,都道府県コード,都道府県内地方コード,座標,地域コード,市町村コード,都市コード commonStyle;
  class 天気,降水確率,気温 infoStyle;
  class 注意報,警報,災害情報,火山コード disasterStyle;
```

``` mermaid
flowchart TD
    subgraph Locations
        地方コード(地方コード) --> 都道府県コード(都道府県コード)
        都道府県コード --> 都道府県内地方コード(都道府県内地方コード)
        座標(座標) --> 都道府県内地方コード
        都道府県内地方コード --> 地域コード(地域コード)
        地域コード --> 市町村コード(市町村コード)
    end

    subgraph WeatherInformation
        都道府県コード --> 天気{天気}
        都道府県コード --> 降水確率{降水確率}
        都道府県内地方コード --> 天気
        都道府県内地方コード --> 降水確率
        市町村コード --> 気温{気温}
        都市コード(都市コード) --> 気温
    end

    subgraph DisasterInformation
        都道府県内地方コード --> 注意報{注意報}
        都道府県内地方コード --> 警報{警報}
        都道府県内地方コード --> 災害情報{災害情報}
        市町村コード --> 災害情報
        災害情報 --> 火山コード(火山コード)
        火山コード --> 座標
    end

    style 地方コード fill:#f9f,stroke:#333,stroke-width:2px
    style 都道府県コード fill:#f9f,stroke:#333,stroke-width:2px
    style 都道府県内地方コード fill:#f9f,stroke:#333,stroke-width:2px
    style 座標 fill:#f9f,stroke:#333,stroke-width:2px
    style 地域コード fill:#f9f,stroke:#333,stroke-width:2px
    style 市町村コード fill:#f9f,stroke:#333,stroke-width:2px
    style 都市コード fill:#f9f,stroke:#333,stroke-width:2px

    style 天気 fill:#ccf,stroke:#333,stroke-width:2px
    style 降水確率 fill:#ccf,stroke:#333,stroke-width:2px
    style 気温 fill:#ccf,stroke:#333,stroke-width:2px

    style 注意報 fill:#fcc,stroke:#333,stroke-width:2px
    style 警報 fill:#fcc,stroke:#333,stroke-width:2px
    style 災害情報 fill:#fcc,stroke:#333,stroke-width:2px
    style 火山コード fill:#fcc,stroke:#333,stroke-width:2px
```

``` mermaid
flowchart TD
    地方コード --> 都道府県コード
    都道府県コード --> 都道府県内地方コード
    都道府県コード --> 天気
    都道府県コード --> 降水確率
    座標 --> 都道府県内地方コード
    都道府県内地方コード --> 地域コード
    都道府県内地方コード --> 天気
    都道府県内地方コード --> 降水確率
    都道府県内地方コード --> 注意報,警報
    都道府県内地方コード --> 災害情報
    地域コード --> 市町村コード
    市町村コード --> 気温
    市町村コード --> 災害情報
    災害情報 --> 火山コード
    火山コード --> 座標

    都市コード -->気温

```
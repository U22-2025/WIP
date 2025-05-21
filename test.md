```mermaid
graph TD
    A[クライアント] <--> B[座標->地域コード変換サーバ（UDP）]
    A <--> C[気象情報サーバ（分散型）（UDP）]
    C <--> D[Redisサーバ（TCP）]
    D <--> E[気象データ更新サーバ（UDP）]
```
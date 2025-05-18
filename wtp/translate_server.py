import psycopg2

# 仮の接続情報（必要に応じて書き換えてください）
DB_NAME = "weather_map"
DB_USER = "username"
DB_PASSWORD = "password"
DB_HOST = "localhost"
DB_PORT = "5432"

# 取得したい座標（例：経度 139.6917, 緯度 35.6895）
longitude = 139.6917
latitude = 35.6895

# 接続して地方名を取得する関数
def get_district_name(longitude, latitude):
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        cursor = conn.cursor()
        
        query = f"""
        SELECT name
        FROM districts
        WHERE ST_Within(
            ST_GeomFromText('POINT({longitude} {latitude})', 6668),
            geom
        );
        """
        cursor.execute(query)
        result = cursor.fetchone()

        if result:
            return result[0]
        else:
            return "該当する地方が見つかりませんでした。"

    except Exception as e:
        return f"エラーが発生しました: {e}"

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# 使用例
district_name = get_district_name(139.6917, 35.6895)
print("地方名:", district_name)

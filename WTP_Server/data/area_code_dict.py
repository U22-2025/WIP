import requests
import psycopg2
from psycopg2.extensions import connection, cursor
from dotenv import load_dotenv
import os

def fetch_area_json() -> dict:
    """
    気象庁のエリアコードJSONを取得する
    
    Returns:
        dict: エリアコードの辞書データ
    """
    try:
        url = "https://www.jma.go.jp/bosai/common/const/area.json"
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"エリアコードJSONの取得に失敗しました: {e}")
        return None
    
def postgre_conn():
    """
    PostgreSQLデータベースに接続する
    
    Returns:
        tuple: (connection, cursor)のタプル。エラー時はNone, None
    """
    try:
        load_dotenv()
        # データベース接続情報
        conn_info = {
            'dbname': 'weather_forecast_map',  # データベース名
            'user': os.getenv('DB_USERNAME'),
            'password': os.getenv('DB_PASSWORD'),
            'host': 'localhost',   # ホスト
            'port': '5432'         # ポート
        }
        
        print("PostgreSQLに接続しています...")
        conn = psycopg2.connect(**conn_info)
        cur = conn.cursor()
        print("接続に成功しました")
        
        return conn, cur
        
    except psycopg2.Error as e:
        print(f"データベース接続エラー: {e}")
        return None, None
    except Exception as e:
        print(f"予期せぬエラーが発生しました: {e}")
        return None, None

def close_postgre_conn(conn: 'connection', cur: 'cursor') -> None:
    """
    PostgreSQL接続を閉じる
    
    Args:
        conn: データベース接続オブジェクト
        cur: カーソルオブジェクト
    """
    try:
        if cur:
            cur.close()
        if conn:
            conn.close()
            print("データベース接続を閉じました")
    except Exception as e:
        print(f"接続を閉じる際にエラーが発生しました: {e}")


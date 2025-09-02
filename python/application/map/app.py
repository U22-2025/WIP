from flask import Flask, render_template, request, jsonify, send_from_directory
import sys, os
from pathlib import Path
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
from WIPClientPy import Client

app = Flask(__name__)
client = Client(host="localhost", port=4110, debug=True)


@app.route("/")
def index():
    return render_template("map.html")  # 上のHTMLを templates/map.html に保存


# JSONファイル配置ディレクトリ
JSON_DIR = Path(__file__).resolve().parent / "static" / "json"


# 天気コードJSONを提供するルート
@app.route("/weather_code.json")
def weather_code():
    import json

    try:
        with open(JSON_DIR / "weather_code.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        # codesプロパティのみを返す
        return jsonify(data.get("codes", {}))
    except Exception as e:
        print(f"天気コードJSONの読み込みエラー: {e}")
        # フォールバック: 基本的な天気コード
        return jsonify({"100": "晴れ", "200": "くもり", "300": "雨", "400": "雪"})


# エラーコードJSONを提供するルート
@app.route("/error_code.json")
def error_code_json():
    return send_from_directory(JSON_DIR, "error_code.json")


def _add_date_info(weather_data, day_offset=0):
    """天気データに日付情報を追加するヘルパー関数
    Args:
        weather_data: 天気データの辞書
        day_offset: 今日からのオフセット日数 (0=今日)
    """
    base_date = datetime.now()
    target_date = base_date + timedelta(days=day_offset)

    # 日付と曜日を日本語で設定
    weekdays_ja = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    ]
    weekday_en = target_date.strftime("%A")

    weather_data["date"] = target_date.strftime("%Y-%m-%d")
    weather_data["day_of_week"] = weekday_en
    weather_data["day"] = day_offset  # day値を明示的に設定

    return weather_data


def _create_fallback_weather_data(area_code, days_offset=0):
    """エラー時のダミーデータを作成するヘルパー関数"""
    date = datetime.now() + timedelta(days=days_offset)
    return {
        "date": date.strftime("%Y-%m-%d"),
        "day_of_week": date.strftime("%A"),
        "weather_code": "100",
        "temperature": "--",
        "precipitation_prob": "--",
        "area_code": area_code,
    }


def _get_today_weather(lat, lng):
    """今日の天気データを取得するヘルパー関数"""
    client.set_coordinates(lat, lng)
    today_weather = client.get_weather(day=0, alert=True, disaster=True)

    if (
        not today_weather
        or isinstance(today_weather, dict)
        and "error_code" in today_weather
    ):
        raise ValueError("今日の天気データの取得に失敗しました")

    if "area_code" not in today_weather:
        raise ValueError("エリアコードが見つかりませんでした")

    return today_weather


def _get_weekly_weather_parallel(area_code):
    """並列で週間天気予報を取得するヘルパー関数"""
    weekly_data = {}

    with ThreadPoolExecutor(max_workers=6) as executor:
        # dayとfutureのマップを作成（警報・災害情報も含める）
        future_to_day = {
            executor.submit(
                client.get_weather_by_area_code, area_code=area_code, day=day, alert=True, disaster=True
            ): day
            for day in range(1, 7)
        }

        # 結果をday順にソートして処理
        for day in sorted(future_to_day.values()):
            future = next(f for f, d in future_to_day.items() if d == day)
            try:
                result = future.result()
                if result and not ("error_code" in result):
                    weekly_data[day] = _add_date_info(result, day)
                else:
                    weekly_data[day] = _create_fallback_weather_data(area_code, day)
            except Exception:
                weekly_data[day] = _create_fallback_weather_data(area_code, day)

    # day順にソートしてリストとして返す
    return [weekly_data[day] for day in sorted(weekly_data.keys())]


# 週間予報を取得するエンドポイント
@app.route("/weekly_forecast", methods=["POST"])
def weekly_forecast():
    """週間天気予報を取得し、日付順で並び替えて返す"""
    from datetime import datetime, timedelta

    data = request.get_json()
    lat = data.get("lat")
    lng = data.get("lng")

    if lat is None or lng is None:
        return jsonify({"status": "error", "message": "緯度と経度が必要です"}), 400

    try:
        # 座標を設定
        client.set_coordinates(lat, lng)

        # 今日の天気データを取得してarea_codeを取得（警報・災害情報も含める）
        today_weather = client.get_weather(day=0, alert=True, disaster=True)
        if (
            not today_weather
            or isinstance(today_weather, dict)
            and "error_code" in today_weather
        ):
            return (
                jsonify(
                    {
                        "status": "error",
                        "message": "今日の天気データの取得に失敗しました",
                    }
                ),
                500,
            )

        if "area_code" not in today_weather:
            return (
                jsonify(
                    {"status": "error", "message": "エリアコードが見つかりませんでした"}
                ),
                500,
            )

        area_code = today_weather["area_code"]

        # 7日分の天気予報データを順次取得（0日後から6日後まで）
        weekly_forecast_list = []

        for day in range(7):  # 0日後（今日）から6日後まで
            try:
                # 日付情報を計算
                base_date = datetime.now()
                target_date = base_date + timedelta(days=day)
                date_str = target_date.strftime("%Y-%m-%d")
                day_of_week = target_date.strftime("%A")

                # 天気データを取得
                if day == 0:
                    # 今日のデータは既に取得済み（警報・災害情報も含む）
                    weather_data = today_weather.copy()
                else:
                    # 1日後以降はarea_codeで取得（警報・災害情報も含める）
                    weather_data = client.get_weather_by_area_code(
                        area_code=area_code, day=day, alert=True, disaster=True
                    )

                    if (
                        not weather_data
                        or isinstance(weather_data, dict)
                        and "error_code" in weather_data
                    ):
                        # エラーの場合はダミーデータを作成
                        weather_data = {
                            "weather_code": "100",  # 晴れをデフォルト
                            "temperature": "--",
                            "precipitation_prob": "--",
                            "area_code": area_code,
                        }

                # 日付情報を追加
                weather_data["date"] = date_str
                weather_data["day_of_week"] = day_of_week
                weather_data["day"] = day

                # リストに追加
                weekly_forecast_list.append(weather_data)

            except Exception as e:
                print(f"Error getting weather for day {day}: {e}")
                # エラーの場合はダミーデータを作成
                base_date = datetime.now()
                target_date = base_date + timedelta(days=day)
                dummy_data = {
                    "date": target_date.strftime("%Y-%m-%d"),
                    "day_of_week": target_date.strftime("%A"),
                    "weather_code": "100",
                    "temperature": "--",
                    "precipitation_prob": "--",
                    "area_code": area_code,
                    "day": day,
                }
                weekly_forecast_list.append(dummy_data)

        # 念のため日付順でソート（day の値で）
        weekly_forecast_list.sort(key=lambda x: x["day"])

        return jsonify(
            {
                "status": "ok",
                "coordinates": {"lat": lat, "lng": lng},
                "area_code": area_code,
                "weekly_forecast": weekly_forecast_list,
            }
        )

    except Exception as e:
        print(f"Error in weekly_forecast: {e}")
        return (
            jsonify({"status": "error", "message": "週間予報の取得に失敗しました"}),
            500,
        )


if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True)

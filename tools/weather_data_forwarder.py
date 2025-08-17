#!/usr/bin/env python3
"""
気象データ転送クライアント (Weather Data Forwarder)

Weather APIから気象データを取得し、WIPレポートサーバーに転送する専用ツール
JSON形式のデータをWIPプロトコルパケットに変換してRedisに格納

主な機能:
- Weather API → WIP Report Server への気象データ転送
- 142地域コード × 7日分の予報データを一括処理
- 並列処理による高速転送
- タイムスタンプ自動更新 (source_type: "report_client")

使用例:
    # 全地域処理（デフォルト）: 142地域×7日分 = 最大994件の転送
    python tools/weather_data_forwarder.py
    
    # 特定地域指定処理: 指定地域×7日分
    python tools/weather_data_forwarder.py 130010 140010
    
    # デバッグモードで詳細表示
    python tools/weather_data_forwarder.py --debug
    
    # 利用可能地域コード一覧表示
    python tools/weather_data_forwarder.py --list-areas
"""

import sys
import os
import json
import time
import argparse
import requests
from pathlib import Path
from typing import Optional, List
from concurrent.futures import ThreadPoolExecutor, as_completed

# パスを追加
sys.path.insert(0, os.path.abspath('src'))


def get_area_codes() -> List[str]:
    """地域コード一覧を取得（レポート送信用）"""
    area_codes_file = Path('docs/area_codes.json')
    if area_codes_file.exists():
        with open(area_codes_file, 'r', encoding='utf-8') as f:
            area_data = json.load(f)
        area_codes = []
        for prefecture_code, areas in area_data.items():
            area_codes.extend(areas.keys())  # 142個の地域コード
        return area_codes
    return []


def send_weather_reports_all_days(area_code: str, weather_api_url: str = "http://localhost:80", report_server_host: str = "localhost", report_server_port: int = 4112, debug: bool = False) -> int:
    """指定地域の7日分の気象データを全て取得してレポート送信"""
    success_count = 0
    
    try:
        from WIPCommonPy.clients.report_client import ReportClient
        client = ReportClient(host=report_server_host, port=report_server_port, debug=debug)
        
        # day0からday6まで順次処理
        for day in range(7):
            try:
                # 各日のデータを取得
                response = requests.get(f"{weather_api_url}/weather", params={
                    'area_code': area_code,
                    'day': day,
                    'weather_flag': 1,
                    'temperature_flag': 1,
                    'pop_flag': 1,
                    'alert_flag': 1,
                    'disaster_flag': 1
                }, timeout=10)
                
                if response.status_code != 200:
                    if debug:
                        print(f"    day{day}: HTTP {response.status_code}")
                    continue
                    
                weather_data = response.json()
                
                # 気象データを解析
                weather_code = None
                temperature = None
                precipitation_prob = None
                alert = None
                disaster = None
                
                if 'weather' in weather_data:
                    try:
                        weather_code = int(weather_data['weather'])
                    except (ValueError, TypeError):
                        pass
                        
                if 'temperature' in weather_data:
                    try:
                        temperature = float(weather_data['temperature'])
                    except (ValueError, TypeError):
                        pass
                        
                if 'precipitation_prob' in weather_data:
                    try:
                        precipitation_prob = int(weather_data['precipitation_prob'])
                    except (ValueError, TypeError):
                        pass
                        
                if 'warnings' in weather_data and weather_data['warnings']:
                    alert = weather_data['warnings']
                    
                if 'disaster' in weather_data and weather_data['disaster']:
                    disaster = weather_data['disaster']
                
                # クライアントにデータを設定
                client.set_sensor_data(
                    area_code=area_code,
                    weather_code=weather_code,
                    temperature=temperature,
                    precipitation_prob=precipitation_prob,
                    alert=alert,
                    disaster=disaster
                )
                
                # レポート送信
                result = client.send_report()
                
                if result:
                    success_count += 1
                    if debug:
                        print(f"    day{day}: 送信成功 (天気={weather_code}, 気温={temperature}℃, 降水確率={precipitation_prob}%)")
                else:
                    if debug:
                        print(f"    day{day}: 送信失敗")
                        
            except Exception as e:
                if debug:
                    print(f"    day{day}: エラー {e}")
                continue
        
        return success_count
        
    except Exception as e:
        print(f"レポート送信エラー ({area_code}): {e}")
        return 0

def main():
    parser = argparse.ArgumentParser(description='気象データ転送クライアント - Weather API から WIP Report Server へのデータ転送')
    parser.add_argument('area_codes', nargs='*', help='転送対象の地域コード（指定なしで全142地域を処理）')
    parser.add_argument('--weather-api-url', default='http://localhost:80', help='Weather API サーバーのURL')
    parser.add_argument('--report-host', default='localhost', help='WIP Report Server のホスト')
    parser.add_argument('--report-port', type=int, default=4112, help='WIP Report Server のポート')
    parser.add_argument('--debug', action='store_true', help='デバッグモードを有効にする（転送詳細を表示）')
    parser.add_argument('--list-areas', action='store_true', help='利用可能な地域コード一覧を表示')
    
    args = parser.parse_args()
    
    if args.list_areas:
        # 地域コード一覧を表示
        area_codes = get_area_codes()
        if area_codes:
            print(f"利用可能な地域コード ({len(area_codes)}個):")
            for code in sorted(area_codes):
                print(f"  {code}")
        else:
            print("エリアコードファイルが見つかりません: docs/area_codes.json")
        return
    
    # 処理対象地域コードの決定
    if args.area_codes:
        # 特定地域指定
        report_area_codes = args.area_codes
        print(f"処理対象地域（特定指定）: {report_area_codes}")
    else:
        # 全地域処理（デフォルト）
        report_area_codes = get_area_codes()
        if report_area_codes:
            print(f"処理対象地域（全地域）: {len(report_area_codes)}個")
            if args.debug:
                print(f"地域一覧: {report_area_codes[:10]}..." if len(report_area_codes) > 10 else f"地域一覧: {report_area_codes}")
        else:
            print("警告: area_codes.jsonが見つかりません。東京地方のみ処理します。")
            report_area_codes = ['130010']
            print(f"処理対象地域（フォールバック）: {report_area_codes}")
    
    # 各地域コードについてデータ転送
    print("気象データ転送を開始します...")
    print(f"転送元 Weather API: {args.weather_api_url}")
    print(f"転送先 Report Server: {args.report_host}:{args.report_port}")
    
    def process_area(area_code: str) -> tuple[str, bool, str]:
        """単一地域の処理（並列実行用）"""
        try:
            # 7日分の気象データを取得してレポート送信
            success_count = send_weather_reports_all_days(
                area_code, 
                args.weather_api_url, 
                args.report_host, 
                args.report_port, 
                args.debug
            )
            
            if success_count > 0:
                return area_code, True, f"7日分データ転送完了 ({success_count}/7日)"
            else:
                return area_code, False, "全日程で転送失敗"
        except Exception as e:
            return area_code, False, f"処理エラー: {e}"
    
    success_count = 0
    
    # 地域数に応じて並列処理の判断
    if len(report_area_codes) > 5:
        # 多数の地域の場合は並列処理
        print(f"   {len(report_area_codes)}地域を並列処理で実行中...")
        max_workers = min(10, len(report_area_codes))  # 最大10スレッド
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 全地域を並列実行
            future_to_area = {executor.submit(process_area, area_code): area_code for area_code in report_area_codes}
            
            for future in as_completed(future_to_area):
                area_code, success, message = future.result()
                if success:
                    print(f"   ✓ {area_code}: {message}")
                    success_count += 1
                else:
                    print(f"   ✗ {area_code}: {message}")
    else:
        # 少数の地域の場合は順次処理
        for area_code in report_area_codes:
            print(f"   処理中: {area_code}")
            area_code, success, message = process_area(area_code)
            if success:
                print(f"   ✓ {area_code}: {message}")
                success_count += 1
            else:
                print(f"   ✗ {area_code}: {message}")
    
    total_transfers = success_count * 7  # 各地域で7日分転送
    print(f"\n転送完了: {success_count}/{len(report_area_codes)}地域の処理が成功しました")
    print(f"総転送データ数: 最大{total_transfers}件（各地域7日分の予報データ）")

if __name__ == "__main__":
    main()
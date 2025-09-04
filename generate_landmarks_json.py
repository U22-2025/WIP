#!/usr/bin/env python3
"""
ランドマークデータをRedis補完用JSONファイルに変換するスクリプト

docs/landmark.xmlの座標データを解析し、エリアコード別にグループ化して
Redis補完用のJSONファイルを生成します。
"""

import xml.etree.ElementTree as ET
import json
import os
import sys
import time
from typing import Dict, List, Tuple, Optional
from pathlib import Path

# WIPCommonPyへのパスを追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from WIPCommonPy.clients.location_client import LocationClient


class LandmarkToJsonConverter:
    """ランドマークデータをJSON変換するクラス"""
    
    def __init__(self, debug: bool = False):
        self.debug = debug
        # タイムアウト時間を延長してLocationClientを初期化
        self.location_client = LocationClient(debug=debug)
        # リクエスト間隔制御用
        self.request_delay = 2.0  # 2秒待機
        self.last_request_time = 0
        
    def parse_landmark_xml(self, xml_path: str) -> List[Tuple[float, float, str]]:
        """
        landmark.xmlをパースして座標とランドマーク情報を抽出
        
        Args:
            xml_path: XMLファイルのパス
            
        Returns:
            List[(緯度, 経度, ランドマーク名)] のリスト
        """
        landmarks = []
        
        try:
            # XMLファイルを読み込み、1行目がXMLでない場合はスキップ
            with open(xml_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 1行目がXML宣言やルート要素でない場合はスキップ
            lines = content.split('\n')
            if lines and not lines[0].strip().startswith(('<', '<?xml')):
                if self.debug:
                    print(f"1行目をスキップ: {lines[0][:50]}...")
                content = '\n'.join(lines[1:])
            
            # XML文字列から直接パース
            root = ET.fromstring(content)
            
            # 名前空間を定義
            namespaces = {
                'gml': 'http://www.opengis.net/gml/3.2',
                'ksj': 'http://nlftp.mlit.go.jp/ksj/schemas/ksj-app',
                'xlink': 'http://www.w3.org/1999/xlink'
            }
            
            # 座標とランドマーク名のマッピングを作成
            point_coords = {}
            
            # gml:Pointから座標を取得
            for point in root.findall('.//gml:Point', namespaces):
                pos_element = point.find('gml:pos', namespaces)
                if pos_element is not None:
                    pos_text = pos_element.text.strip()
                    coords = pos_text.split()
                    if len(coords) == 2:
                        try:
                            lat = float(coords[0])
                            lon = float(coords[1])
                            point_id = point.get('{http://www.opengis.net/gml/3.2}id', 'unknown')
                            point_coords[point_id] = (lat, lon)
                        except ValueError:
                            if self.debug:
                                print(f"座標解析エラー: {pos_text}")
                            continue
            
            # ksj:AttractCustomersFacilityからランドマーク名を取得
            for facility in root.findall('.//ksj:AttractCustomersFacility', namespaces):
                position_elem = facility.find('ksj:position', namespaces)
                facility_name_elem = facility.find('ksj:facilityName', namespaces)
                
                if position_elem is not None and facility_name_elem is not None:
                    # xlink:hrefから参照されるpoint IDを取得
                    href = position_elem.get('{http://www.w3.org/1999/xlink}href', '')
                    point_id = href.lstrip('#')
                    facility_name = facility_name_elem.text.strip() if facility_name_elem.text else 'unknown'
                    
                    # point IDに対応する座標を取得
                    if point_id in point_coords:
                        lat, lon = point_coords[point_id]
                        landmarks.append((lat, lon, facility_name))
                        if self.debug:
                            print(f"ランドマーク: {facility_name} ({lat}, {lon})")
            
            if self.debug:
                print(f"ランドマーク解析完了: {len(landmarks)}件")
                
        except Exception as e:
            print(f"XML解析エラー: {e}")
            return []
            
        return landmarks
    
    def coordinate_to_area_code(self, lat: float, lon: float) -> Optional[str]:
        """
        座標からエリアコードを取得（レート制限付き）
        
        Args:
            lat: 緯度
            lon: 経度
            
        Returns:
            エリアコード（6桁）、取得失敗時はNone
        """
        try:
            # リクエスト間隔制御
            current_time = time.time()
            elapsed = current_time - self.last_request_time
            if elapsed < self.request_delay:
                sleep_time = self.request_delay - elapsed
                time.sleep(sleep_time)
            
            # 最大3回リトライ
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    area_code = self.location_client.get_area_code_from_coordinates(lat, lon)
                    self.last_request_time = time.time()
                    return area_code
                except Exception as retry_e:
                    if attempt < max_retries - 1:
                        if self.debug:
                            print(f"エリアコード取得リトライ {attempt + 1}/{max_retries} ({lat}, {lon}): {retry_e}")
                        time.sleep(3.0)  # リトライ前に3秒待機
                    else:
                        raise retry_e
                        
        except Exception as e:
            if self.debug:
                print(f"エリアコード取得エラー ({lat}, {lon}): {e}")
            return None
    
    def convert_to_redis_json(self, landmarks: List[Tuple[float, float, str]], output_file: str):
        """
        ランドマークデータをRedis補完用JSONに変換
        
        Args:
            landmarks: ランドマーク情報のリスト
            output_file: 出力JSONファイルのパス
        """
        print(f"Redis補完用JSON生成開始: {len(landmarks)}件のランドマーク")
        
        # エリアコード別にランドマーク名をグループ化
        area_landmarks = {}
        processed = 0
        errors = 0
        
        for i, (lat, lon, landmark_name) in enumerate(landmarks, 1):
            processed += 1
            
            if self.debug or i % 25 == 0:
                print(f"  進捗: {i}/{len(landmarks)} ({i/len(landmarks)*100:.1f}%)")
            
            # エリアコードを取得
            area_code = self.coordinate_to_area_code(lat, lon)
            if area_code is None:
                errors += 1
                if self.debug:
                    print(f"  スキップ: {landmark_name} (エリアコード取得失敗)")
                continue
            
            # Redis補完用の形式でエリアコード別にランドマーク情報を蓄積（座標含む）
            redis_key = f"weather:{area_code}"
            if redis_key not in area_landmarks:
                area_landmarks[redis_key] = {
                    "landmarks": []
                }
            
            landmark_data = {
                "name": landmark_name,
                "latitude": lat,
                "longitude": lon
            }
            area_landmarks[redis_key]["landmarks"].append(landmark_data)
            
            if self.debug:
                print(f"  追加: {landmark_name} -> {redis_key}")
        
        # JSONファイルに出力
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(area_landmarks, f, ensure_ascii=False, indent=2)
            
            print(f"\nJSON生成完了:")
            print(f"  出力ファイル: {output_file}")
            print(f"  処理済みランドマーク数: {processed}")
            print(f"  対象エリアコード数: {len(area_landmarks)}")
            print(f"  エラー数: {errors}")
            
            # サンプル出力
            print("\n=== サンプル出力 ===")
            sample_count = 0
            for redis_key, data in area_landmarks.items():
                if sample_count < 2:
                    landmarks_preview = []
                    # 最初の2件のみ詳細表示
                    for i, landmark in enumerate(data["landmarks"][:2]):
                        landmarks_preview.append(f'{{"name": "{landmark["name"]}", "lat": {landmark["latitude"]}, "lon": {landmark["longitude"]}}}')
                    if len(data["landmarks"]) > 2:
                        landmarks_preview.append(f"... 他{len(data['landmarks'])-2}件")
                    print(f'{redis_key}: {{"landmarks": [{", ".join(landmarks_preview)}]}}')
                    sample_count += 1
                else:
                    break
            
            if len(area_landmarks) > 2:
                print(f"... 他{len(area_landmarks)-2}エリア")
                
        except Exception as e:
            print(f"JSON出力エラー: {e}")
    
    def process_landmarks_to_json(self, xml_path: str, output_file: str):
        """
        ランドマークデータの処理を実行してJSONファイルを生成
        
        Args:
            xml_path: XMLファイルのパス
            output_file: 出力JSONファイルのパス
        """
        print(f"ランドマークXMLを解析中: {xml_path}")
        
        # XMLファイルの存在確認
        if not os.path.exists(xml_path):
            print(f"エラー: ファイルが見つかりません: {xml_path}")
            return
        
        # XMLを解析してランドマーク情報を取得
        landmarks = self.parse_landmark_xml(xml_path)
        if not landmarks:
            print("ランドマークデータが見つかりませんでした")
            return
        
        print(f"ランドマーク数: {len(landmarks)}")
        
        # テスト用に最初の10件のみ処理（座標フォーマットテスト）
        if len(landmarks) > 10 and output_file.endswith("_test.json"):
            print(f"テストのため最初の10件のランドマークのみを処理します（全{len(landmarks)}件中）")
            landmarks = landmarks[:10]
        
        # Redis補完用JSONに変換
        self.convert_to_redis_json(landmarks, output_file)


def main():
    """メイン処理"""
    import argparse
    
    parser = argparse.ArgumentParser(description='ランドマークデータをRedis補完用JSONファイルに変換')
    parser.add_argument('--xml-path', 
                       default='docs/landmark.xml',
                       help='landmark.xmlファイルのパス (デフォルト: docs/landmark.xml)')
    parser.add_argument('--output', 
                       default='landmarks_redis.json',
                       help='出力JSONファイルのパス (デフォルト: landmarks_redis.json)')
    parser.add_argument('--debug', 
                       action='store_true',
                       help='デバッグモードを有効にする')
    
    args = parser.parse_args()
    
    # コンバーターを初期化
    converter = LandmarkToJsonConverter(debug=args.debug)
    
    try:
        # ランドマーク処理を実行
        start_time = time.time()
        converter.process_landmarks_to_json(args.xml_path, args.output)
        end_time = time.time()
        
        print(f"\n処理時間: {end_time - start_time:.1f}秒")
        print("✅ JSON生成が正常に完了しました")
            
    except Exception as e:
        print(f"処理中にエラーが発生しました: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
#!/usr/bin/env python3
"""
ランドマークJSONファイルをRedisに安全にインポートするスクリプト

既存の気象データを保持したまま、ランドマーク情報のみを追加または更新します。
"""

import json
import os
import sys
from typing import Dict, List, Any, Optional

# WIPCommonPyへのパスを追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from WIPServerPy.data.redis_manager import WeatherRedisManager


class LandmarkImporter:
    """ランドマークデータをRedisにインポートするクラス"""
    
    def __init__(self, debug: bool = False):
        self.debug = debug
        self.redis_manager = WeatherRedisManager(debug=debug)
        
    def load_landmarks_json(self, json_path: str) -> Dict[str, Dict[str, List[Dict[str, Any]]]]:
        """
        ランドマークJSONファイルを読み込み
        
        Args:
            json_path: JSONファイルのパス
            
        Returns:
            ランドマークデータ辞書
        """
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                landmarks_data = json.load(f)
            
            if self.debug:
                print(f"JSONファイル読み込み完了: {len(landmarks_data)}エリア")
                total_landmarks = sum(len(data.get('landmarks', [])) for data in landmarks_data.values())
                print(f"総ランドマーク数: {total_landmarks}")
                
            return landmarks_data
            
        except Exception as e:
            print(f"JSONファイル読み込みエラー: {e}")
            return {}
    
    def import_landmarks_safely(self, landmarks_data: Dict[str, Dict[str, List[Dict[str, Any]]]], merge_mode: bool = True) -> Dict[str, int]:
        """
        ランドマークデータを既存データに安全に追加
        
        Args:
            landmarks_data: ランドマークデータ辞書
            merge_mode: Trueの場合既存ランドマークと結合、Falseの場合置換
            
        Returns:
            処理結果統計
        """
        stats = {
            "updated": 0,
            "created": 0,
            "errors": 0,
            "skipped": 0,
            "total_landmarks": 0
        }
        
        print(f"Redis更新開始: {len(landmarks_data)}エリア")
        
        for redis_key, landmark_info in landmarks_data.items():
            try:
                # weather:エリアコード からエリアコードを抽出
                if not redis_key.startswith("weather:"):
                    if self.debug:
                        print(f"  スキップ: 無効なキー形式 {redis_key}")
                    stats["skipped"] += 1
                    continue
                
                area_code = redis_key.replace("weather:", "")
                landmarks_list = landmark_info.get("landmarks", [])
                
                if not landmarks_list:
                    if self.debug:
                        print(f"  スキップ: ランドマークデータなし {area_code}")
                    stats["skipped"] += 1
                    continue
                
                stats["total_landmarks"] += len(landmarks_list)
                
                # 既存データを取得
                existing_data = self.redis_manager.get_weather_data(area_code)
                
                if existing_data:
                    # 既存データにランドマーク情報を追加/更新
                    if merge_mode and "landmarks" in existing_data:
                        # 既存ランドマークと結合（重複排除）
                        existing_landmarks = existing_data["landmarks"]
                        existing_names = {lm.get("name", "") for lm in existing_landmarks if isinstance(lm, dict)}
                        
                        # 新しいランドマークのうち、既存にないものだけを追加
                        new_landmarks = [lm for lm in landmarks_list if lm.get("name", "") not in existing_names]
                        combined_landmarks = existing_landmarks + new_landmarks
                        
                        existing_data["landmarks"] = combined_landmarks
                        merged_count = len(new_landmarks)
                        total_count = len(combined_landmarks)
                        
                        if self.debug:
                            print(f"  結合モード: {area_code} - 新規{merged_count}件、合計{total_count}件のランドマーク")
                    else:
                        # 置換モード
                        existing_data["landmarks"] = landmarks_list
                        if self.debug:
                            print(f"  置換モード: {area_code} - {len(landmarks_list)}件のランドマーク")
                    
                    if self.redis_manager.update_weather_data(area_code, existing_data):
                        stats["updated"] += 1
                    else:
                        stats["errors"] += 1
                        if self.debug:
                            print(f"  エラー: 更新失敗 {area_code}")
                else:
                    # 既存データがない場合はデフォルト構造を作成してランドマークを追加
                    new_data = self.redis_manager._create_default_weather_data()
                    new_data["landmarks"] = landmarks_list
                    
                    if self.redis_manager.update_weather_data(area_code, new_data):
                        stats["created"] += 1
                        if self.debug:
                            print(f"  新規作成: {area_code} - {len(landmarks_list)}件のランドマーク")
                    else:
                        stats["errors"] += 1
                        if self.debug:
                            print(f"  エラー: 新規作成失敗 {area_code}")
                            
            except Exception as e:
                stats["errors"] += 1
                if self.debug:
                    print(f"  処理エラー ({redis_key}): {e}")
        
        return stats
    
    def preview_import(self, landmarks_data: Dict[str, Dict[str, List[Dict[str, Any]]]]) -> None:
        """
        インポート予定データのプレビュー表示
        
        Args:
            landmarks_data: ランドマークデータ辞書
        """
        print("\n=== インポートプレビュー ===")
        total_landmarks = 0
        existing_areas = 0
        new_areas = 0
        
        for redis_key, landmark_info in landmarks_data.items():
            if not redis_key.startswith("weather:"):
                continue
                
            area_code = redis_key.replace("weather:", "")
            landmarks_list = landmark_info.get("landmarks", [])
            total_landmarks += len(landmarks_list)
            
            # 既存データの確認
            existing_data = self.redis_manager.get_weather_data(area_code)
            if existing_data:
                existing_areas += 1
                status = "更新"
                has_existing_landmarks = "landmarks" in existing_data
                landmark_status = f"(既存ランドマーク: {'あり' if has_existing_landmarks else 'なし'})"
            else:
                new_areas += 1
                status = "新規作成"
                landmark_status = ""
            
            if self.debug:
                print(f"  {area_code}: {status} - {len(landmarks_list)}件のランドマーク {landmark_status}")
        
        print(f"\n対象エリア数: {len(landmarks_data)}")
        print(f"  既存エリアへの追加: {existing_areas}")
        print(f"  新規エリアの作成: {new_areas}")
        print(f"総ランドマーク数: {total_landmarks}")
    
    def import_from_json(self, json_path: str, dry_run: bool = False, merge_mode: bool = True) -> Dict[str, int]:
        """
        JSONファイルからランドマークデータをインポート
        
        Args:
            json_path: JSONファイルのパス
            dry_run: True の場合はプレビューのみ実行
            merge_mode: Trueの場合既存ランドマークと結合、Falseの場合置換
            
        Returns:
            処理結果統計
        """
        print(f"ランドマークJSONファイル: {json_path}")
        
        # JSONファイルの存在確認
        if not os.path.exists(json_path):
            print(f"エラー: ファイルが見つかりません: {json_path}")
            return {"updated": 0, "created": 0, "errors": 1, "skipped": 0, "total_landmarks": 0}
        
        # JSONデータを読み込み
        landmarks_data = self.load_landmarks_json(json_path)
        if not landmarks_data:
            print("ランドマークデータが見つかりませんでした")
            return {"updated": 0, "created": 0, "errors": 1, "skipped": 0, "total_landmarks": 0}
        
        # プレビュー表示
        self.preview_import(landmarks_data)
        
        if dry_run:
            print("\n📋 ドライランモード: 実際のRedis更新は行いません")
            return {"updated": 0, "created": 0, "errors": 0, "skipped": 0, "total_landmarks": 0}
        
        # 確認メッセージ
        if not self.debug:
            response = input("\n続行しますか？ [y/N]: ")
            if response.lower() not in ['y', 'yes']:
                print("処理をキャンセルしました")
                return {"updated": 0, "created": 0, "errors": 0, "skipped": 0, "total_landmarks": 0}
        
        # Redisにインポート
        mode_text = "結合モード（既存ランドマークを保持）" if merge_mode else "置換モード（既存ランドマークを上書き）"
        print(f"\nRedisへのインポート開始... ({mode_text})")
        results = self.import_landmarks_safely(landmarks_data, merge_mode)
        
        return results
    
    def close(self):
        """リソースのクリーンアップ"""
        if hasattr(self, 'redis_manager'):
            self.redis_manager.close()


def main():
    """メイン処理"""
    import argparse
    
    parser = argparse.ArgumentParser(description='ランドマークJSONファイルをRedisに安全にインポート')
    parser.add_argument('--json-path', 
                       required=True,
                       help='ランドマークJSONファイルのパス')
    parser.add_argument('--dry-run', 
                       action='store_true',
                       help='ドライランモード（プレビューのみ、実際の更新は行わない）')
    parser.add_argument('--replace', 
                       action='store_true',
                       help='置換モード（既存ランドマークを上書き、デフォルトは結合モード）')
    parser.add_argument('--debug', 
                       action='store_true',
                       help='デバッグモードを有効にする')
    
    args = parser.parse_args()
    
    # インポーターを初期化
    importer = LandmarkImporter(debug=args.debug)
    
    try:
        # インポート処理を実行
        results = importer.import_from_json(args.json_path, dry_run=args.dry_run, merge_mode=not args.replace)
        
        if not args.dry_run:
            # 結果を出力
            print("\n=== インポート結果 ===")
            print(f"更新したエリア数: {results['updated']}")
            print(f"新規作成したエリア数: {results['created']}")
            print(f"スキップしたエリア数: {results['skipped']}")
            print(f"インポートしたランドマーク総数: {results['total_landmarks']}")
            print(f"エラー数: {results['errors']}")
            
            if results['errors'] == 0:
                print("\n✅ ランドマークインポートが正常に完了しました")
            else:
                print(f"\n⚠️  {results['errors']}件のエラーが発生しました")
        else:
            print("\n📋 ドライラン完了")
            
    except Exception as e:
        print(f"処理中にエラーが発生しました: {e}")
        return 1
    finally:
        importer.close()
    
    return 0


if __name__ == "__main__":
    exit(main())
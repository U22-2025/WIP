"""
レポートソフトウェア - IoT機器データ収集処理
レポートリクエスト受信時にJSONファイルへのデータ保存処理を提供
"""
import json
import os
import threading
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path
from .report_packet import ReportRequest


class ReportDataManager:
    """
    レポートデータ管理クラス
    
    IoT機器からのReportRequestを受信し、JSONファイルにデータを保存します。
    エリアコード別にファイルを分割し、スレッドセーフな操作を保証します。
    """
    
    def __init__(self, data_dir: str = "sensor_data"):
        """
        初期化
        
        Args:
            data_dir: データ保存ディレクトリ
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        self._locks = {}  # エリアコード別のファイルロック
        self._locks_lock = threading.Lock()  # ロック辞書用のロック
    
    def _get_file_lock(self, area_code: str) -> threading.Lock:
        """
        エリアコード別のファイルロックを取得
        
        Args:
            area_code: エリアコード
            
        Returns:
            ファイルロック
        """
        with self._locks_lock:
            if area_code not in self._locks:
                self._locks[area_code] = threading.Lock()
            return self._locks[area_code]
    
    def _get_data_file_path(self, area_code: str) -> Path:
        """
        エリアコード別のデータファイルパスを取得
        
        Args:
            area_code: エリアコード
            
        Returns:
            データファイルのパス
        """
        return self.data_dir / f"sensor_data_{area_code}.json"
    
    def _extract_sensor_data(self, report_request: ReportRequest) -> Dict[str, Any]:
        """
        ReportRequestからセンサーデータを抽出
        
        Args:
            report_request: レポートリクエスト
            
        Returns:
            センサーデータの辞書
        """
        # 基本情報
        data = {
            "packet_id": report_request.packet_id,
            "timestamp": report_request.timestamp,
            "received_at": datetime.now().isoformat(),
            "day": report_request.day,
            "version": report_request.version,
            "type": report_request.type
        }
        
        # センサーデータ（フラグが立っている場合のみ含める）
        sensor_values = {}
        
        # 注意: ReportRequestは送信パケットなので、実際の値は拡張フィールドや
        # 別の場所に格納される可能性があります。ここではフラグのみを記録します。
        if report_request.weather_flag:
            sensor_values["weather"] = {"flag": True}
        
        if report_request.temperature_flag:
            sensor_values["temperature"] = {"flag": True}
        
        if report_request.pop_flag:
            sensor_values["precipitation_prob"] = {"flag": True}
        
        if report_request.alert_flag:
            sensor_values["alert"] = {"flag": True}
        
        if report_request.disaster_flag:
            sensor_values["disaster"] = {"flag": True}
        
        if sensor_values:
            data["sensor_data"] = sensor_values
        
        # 拡張フィールドの情報
        if hasattr(report_request, 'ex_field') and report_request.ex_field:
            ex_dict = report_request.ex_field.to_dict()
            if ex_dict:
                data["extended_data"] = {}
                
                # 送信元情報
                if 'source' in ex_dict:
                    ip, port = ex_dict['source']
                    data["extended_data"]["source"] = {
                        "ip": ip,
                        "port": port
                    }
                
                # 警報情報
                if 'alert' in ex_dict:
                    data["extended_data"]["alert"] = ex_dict['alert']
                
                # 災害情報  
                if 'disaster' in ex_dict:
                    data["extended_data"]["disaster"] = ex_dict['disaster']
        
        return data
    
    def _load_existing_data(self, file_path: Path) -> Dict[str, Any]:
        """
        既存のJSONデータを読み込み
        
        Args:
            file_path: ファイルパス
            
        Returns:
            既存データの辞書
        """
        if not file_path.exists():
            return {
                "area_code": "",
                "created_at": datetime.now().isoformat(),
                "last_updated": datetime.now().isoformat(),
                "total_reports": 0,
                "reports": []
            }
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Warning: Failed to load existing data from {file_path}: {e}")
            # 破損したファイルの場合は新しい構造で初期化
            return {
                "area_code": "",
                "created_at": datetime.now().isoformat(),
                "last_updated": datetime.now().isoformat(),
                "total_reports": 0,
                "reports": []
            }
    
    def _save_data(self, file_path: Path, data: Dict[str, Any]) -> None:
        """
        データをJSONファイルに保存
        
        Args:
            file_path: ファイルパス
            data: 保存するデータ
        """
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except IOError as e:
            print(f"Error: Failed to save data to {file_path}: {e}")
            raise
    
    def save_report_data(self, report_request: ReportRequest) -> bool:
        """
        レポートリクエストのデータをJSONファイルに保存
        
        Args:
            report_request: 受信したレポートリクエスト
            
        Returns:
            保存成功の場合True
        """
        try:
            area_code = report_request.area_code
            file_lock = self._get_file_lock(area_code)
            file_path = self._get_data_file_path(area_code)
            
            # エリアコード別にファイルロックを取得
            with file_lock:
                # 既存データを読み込み
                existing_data = self._load_existing_data(file_path)
                
                # エリアコードを設定（初回時）
                if not existing_data.get("area_code"):
                    existing_data["area_code"] = area_code
                
                # センサーデータを抽出
                sensor_data = self._extract_sensor_data(report_request)
                
                # データを追加
                existing_data["reports"].append(sensor_data)
                existing_data["total_reports"] = len(existing_data["reports"])
                existing_data["last_updated"] = datetime.now().isoformat()
                
                # ファイルに保存
                self._save_data(file_path, existing_data)
                
                print(f"Saved report data for area {area_code}, packet_id {report_request.packet_id}")
                return True
                
        except Exception as e:
            print(f"Error saving report data: {e}")
            return False
    
    def get_area_data(self, area_code: str) -> Optional[Dict[str, Any]]:
        """
        指定エリアのデータを取得
        
        Args:
            area_code: エリアコード
            
        Returns:
            エリアのデータまたはNone
        """
        try:
            file_path = self._get_data_file_path(area_code)
            if not file_path.exists():
                return None
            
            file_lock = self._get_file_lock(area_code)
            with file_lock:
                return self._load_existing_data(file_path)
                
        except Exception as e:
            print(f"Error loading area data for {area_code}: {e}")
            return None
    
    def get_latest_reports(self, area_code: str, count: int = 10) -> List[Dict[str, Any]]:
        """
        指定エリアの最新レポートを取得
        
        Args:
            area_code: エリアコード
            count: 取得件数
            
        Returns:
            最新レポートのリスト
        """
        area_data = self.get_area_data(area_code)
        if not area_data:
            return []
        
        reports = area_data.get("reports", [])
        # 最新順（timestampでソート）
        sorted_reports = sorted(reports, key=lambda x: x.get("timestamp", 0), reverse=True)
        return sorted_reports[:count]
    
    def cleanup_old_data(self, area_code: str, max_reports: int = 1000) -> bool:
        """
        古いデータをクリーンアップ（最大件数を超えた場合）
        
        Args:
            area_code: エリアコード
            max_reports: 保持する最大レポート数
            
        Returns:
            クリーンアップ成功の場合True
        """
        try:
            file_path = self._get_data_file_path(area_code)
            if not file_path.exists():
                return True
            
            file_lock = self._get_file_lock(area_code)
            with file_lock:
                existing_data = self._load_existing_data(file_path)
                reports = existing_data.get("reports", [])
                
                if len(reports) <= max_reports:
                    return True
                
                # 最新のレポートのみを保持
                sorted_reports = sorted(reports, key=lambda x: x.get("timestamp", 0), reverse=True)
                existing_data["reports"] = sorted_reports[:max_reports]
                existing_data["total_reports"] = len(existing_data["reports"])
                existing_data["last_updated"] = datetime.now().isoformat()
                
                self._save_data(file_path, existing_data)
                print(f"Cleaned up old data for area {area_code}, kept {max_reports} reports")
                return True
                
        except Exception as e:
            print(f"Error cleaning up data for {area_code}: {e}")
            return False


# グローバルインスタンス（シングルトンパターン）
_report_data_manager = None
_manager_lock = threading.Lock()


def get_report_data_manager(data_dir: str = "sensor_data") -> ReportDataManager:
    """
    レポートデータマネージャーのシングルトンインスタンスを取得
    
    Args:
        data_dir: データ保存ディレクトリ
        
    Returns:
        ReportDataManagerインスタンス
    """
    global _report_data_manager
    
    with _manager_lock:
        if _report_data_manager is None:
            _report_data_manager = ReportDataManager(data_dir)
        return _report_data_manager


def process_report_request(report_request: ReportRequest, data_dir: str = "sensor_data") -> bool:
    """
    レポートリクエストを処理してJSONファイルに保存
    
    Args:
        report_request: 受信したレポートリクエスト
        data_dir: データ保存ディレクトリ
        
    Returns:
        処理成功の場合True
        
    Examples:
        >>> # レポートリクエスト受信時の処理
        >>> success = process_report_request(report_request)
        >>> if success:
        ...     print("Data saved successfully")
    """
    manager = get_report_data_manager(data_dir)
    return manager.save_report_data(report_request)
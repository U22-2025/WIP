"""Time processing utilities."""

import re
from datetime import datetime
from collections import defaultdict
from typing import Optional, List, Dict, Tuple

class TimeProcessor:
    """
    時間処理専用クラス
    
    役割:
    - 災害種別名からの時間情報抽出
    - 複数時間の範囲統合
    - 時間フォーマットの変換
    - 時間ベースのデータ統合
    """
    
    @staticmethod
    def parse_time_from_kind_name(kind_name: str) -> Tuple[Optional[str], Optional[str]]:
        """
        災害種別名から基本名と時間情報を分離
        
        Args:
            kind_name: 災害種別名（時間付きの可能性あり）
            
        Returns:
            (基本災害名, 時間情報)のタプル、時間なしの場合は(None, None)
        """
        time_pattern = r'^(.+)_(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+\d{2}:\d{2})$'
        time_match = re.match(time_pattern, kind_name)
        if time_match:
            return time_match.group(1), time_match.group(2)
        return None, None
    
    @staticmethod
    def create_time_range(times: List[str]) -> str:
        """
        時間リストから統合された時間範囲文字列を作成
        
        Args:
            times: ISO形式の時間文字列リスト
            
        Returns:
            統合された時間範囲文字列
        """
        if len(times) == 1:
            return times[0]
        
        try:
            parsed_times = [datetime.fromisoformat(time_str) for time_str in times]
            parsed_times.sort()
            
            earliest_str = parsed_times[0].strftime("%Y/%m/%d-%H:%M")
            latest_str = parsed_times[-1].strftime("%Y/%m/%d-%H:%M")
            
            return f"{earliest_str}から{latest_str}まで"
        except Exception:
            return times[0]  # エラー時は最初の時間を返す
    
    @staticmethod
    def consolidate_time_ranges(area_kind_mapping: Dict[str, List[str]]) -> Dict[str, List[str]]:
        """
        エリア別災害種別データの時間範囲統合
        
        Args:
            area_kind_mapping: {エリアコード: [災害種別名リスト]}
            
        Returns:
            時間統合済みの{エリアコード: [統合災害種別名リスト]}
        """
        consolidated_mapping = {}
        
        for area_code, kind_names in area_kind_mapping.items():
            kind_groups = defaultdict(list)  # 災害種別ごとの時間グループ
            non_time_kinds = []  # 時間情報なしの災害種別
            
            # 災害種別を時間付きと時間なしに分類
            for kind_name in kind_names:
                base_name, time_info = TimeProcessor.parse_time_from_kind_name(kind_name)
                
                if base_name and time_info:
                    kind_groups[base_name].append(time_info)
                else:
                    non_time_kinds.append(kind_name)
            
            consolidated_kinds = []
            time_based_kinds = set(kind_groups.keys())
            
            # 時間なしの災害種別を追加（重複回避）
            for non_time_kind in non_time_kinds:
                if non_time_kind not in time_based_kinds:
                    consolidated_kinds.append(non_time_kind)
            
            # 時間付きの災害種別を統合処理
            for base_name, time_list in kind_groups.items():
                unique_times = list(set(time_list))  # 重複時間を除去
                time_range = TimeProcessor.create_time_range(unique_times)
                consolidated_kinds.append(f"{base_name}_{time_range}")
            
            consolidated_mapping[area_code] = consolidated_kinds
        
        return consolidated_mapping




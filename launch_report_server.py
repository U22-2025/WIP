"""
Report Server 起動スクリプト
IoT機器からのセンサーデータレポートを受信・処理するサーバー
"""

import os
import sys
from pathlib import Path

# 手動で環境変数を設定
def load_env_file(env_file_path):
    """環境変数ファイルを手動で読み込み"""
    if not env_file_path.exists():
        print(f"警告: 環境変数ファイルが見つかりません: {env_file_path}")
        return
    
    try:
        with open(env_file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    # ${VAR}形式の変数は展開しない（シンプルに処理）
                    if not value.startswith('${'):
                        os.environ[key] = value
        print(f"環境変数を読み込みました: {env_file_path}")
    except Exception as e:
        print(f"環境変数ファイルの読み込みに失敗: {e}")

# 環境変数を読み込み
env_file = Path(__file__).parent / ".env"
load_env_file(env_file)

# パスを追加
sys.path.insert(0, str(Path(__file__).parent))

try:
    from WIP_Server.servers.report_server import ReportServer
    
    def main():
        """メイン関数"""
        print("=" * 60)
        print("Report Server - IoT センサーデータ収集サーバー")
        print("=" * 60)
        
        # 環境変数から設定を取得
        host = os.getenv('REPORT_SERVER_HOST', '0.0.0.0')
        port = int(os.getenv('REPORT_SERVER_PORT', '4112'))
        debug = os.getenv('WIP_DEBUG', 'false').lower() == 'true'
        
        print(f"サーバー設定:")
        print(f"  ホスト: {host}")
        print(f"  ポート: {port}")
        print(f"  デバッグ: {debug}")
        print()
        
        # サーバーを初期化
        try:
            server = ReportServer(host=host, port=port, debug=debug)
            server.start_time = __import__('time').time()
        except Exception as e:
            print(f"サーバーの初期化に失敗しました: {e}")
            return 1
        
        try:
            print(f"Report Server を {host}:{port} で開始します...")
            print("Type 4（レポートリクエスト）を受信してType 5（ACK）を返します")
            print("Ctrl+C で停止")
            print("-" * 60)
            
            # サーバーを起動
            server.run()
            
        except KeyboardInterrupt:
            print(f"\nReport Server を停止しています...")
            
            # 統計情報を表示
            try:
                stats = server.get_statistics()
                print("\n統計情報:")
                print(f"  総リクエスト数: {stats['total_requests']}")
                print(f"  レポート数: {stats['total_reports']}")
                print(f"  成功数: {stats['successful_reports']}")
                print(f"  エラー数: {stats['errors']}")
                print(f"  成功率: {stats['success_rate']:.1f}%")
                print(f"  稼働時間: {stats['uptime']:.1f}秒")
            except Exception as e:
                print(f"統計情報の取得に失敗: {e}")
                
        except Exception as e:
            print(f"サーバー実行中にエラーが発生しました: {e}")
            return 1
            
        finally:
            try:
                server.stop()
                print("Report Server を正常に停止しました")
            except Exception as e:
                print(f"サーバー停止中にエラーが発生しました: {e}")
        
        return 0

    if __name__ == "__main__":
        sys.exit(main())
        
except ImportError as e:
    print(f"モジュールのインポートに失敗しました: {e}")
    print("必要な依存関係がインストールされているか確認してください")
    sys.exit(1)
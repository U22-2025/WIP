#!/usr/bin/env python3
"""
Report Server Connection Diagnostic Tool

レポートサーバーの接続問題を診断し、解決策を提示します。
"""

import socket
import sys
import os
import time
import subprocess
from pathlib import Path

# WIPCommonPyをインポートするためのパス設定
sys.path.insert(0, '/mnt/c/Users/ポッポ焼き/Desktop/WIP/src')

def check_port_available(host: str, port: int) -> bool:
    """ポートが利用可能かチェック"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(2)
        # UDPの場合、sendtoは成功してもサーバーが存在するとは限らない
        # 実際にReportClientを使って接続テストを行う
        sock.close()
        
        # ReportClientを使った実際の接続テスト
        from WIPCommonPy.clients.report_client import ReportClient
        client = ReportClient(host=host, port=port, debug=False)
        
        # 軽量なテストデータで接続確認（有効なエリアコードを使用）
        client.set_sensor_data(
            area_code="130000",
            weather_code=100,
            temperature=20.0,
            precipitation_prob=10,
            alert=[],
            disaster=[]
        )
        
        # 実際に送信してみる（タイムアウトを短く設定）
        client.sock.settimeout(3)  # 3秒タイムアウト
        result = client.send_report_data()
        client.close()
        
        # 成功した場合のみTrueを返す
        return result is not None and result.get("success", False)
        
    except Exception as e:
        # デバッグ用にエラー情報を出力
        error_msg = str(e)
        if "10038" not in error_msg and "10054" not in error_msg:  # 一般的なWindows socket errors を抑制
            print(f"   Port {port} test error: {e}")
        # より詳細なデバッグ情報
        if "10054" in error_msg:
            print(f"   Port {port}: Connection reset by peer (server may not be ready)")
        return False

def check_port_listening(port: int) -> bool:
    """ポートでリスニングしているプロセスがあるかチェック"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('localhost', port))
        sock.close()
        return result == 0
    except Exception:
        return False

def find_listening_processes():
    """リスニング中のプロセスを探す"""
    try:
        # Windowsの場合
        if os.name == 'nt':
            result = subprocess.run(['netstat', '-an'], capture_output=True, text=True)
            if result.returncode == 0:
                listening_ports = []
                for line in result.stdout.split('\n'):
                    if 'LISTENING' in line or 'UDP' in line:
                        parts = line.split()
                        if len(parts) >= 2:
                            addr = parts[1]
                            if ':' in addr:
                                try:
                                    port = int(addr.split(':')[-1])
                                    if 1000 <= port <= 65535:
                                        listening_ports.append(port)
                                except ValueError:
                                    pass
                return sorted(set(listening_ports))
        else:
            # Linux/macOSの場合
            result = subprocess.run(['ss', '-tuln'], capture_output=True, text=True)
            if result.returncode == 0:
                listening_ports = []
                for line in result.stdout.split('\n'):
                    if 'LISTEN' in line or 'UNCONN' in line:  # TCP LISTEN または UDP UNCONN
                        parts = line.split()
                        if len(parts) >= 5:  # 十分な列があることを確認
                            local_addr = parts[4]  # Local Address:Port の列（5番目）
                            if ':' in local_addr:
                                try:
                                    port = int(local_addr.split(':')[-1])
                                    if 1000 <= port <= 65535:
                                        listening_ports.append(port)
                                except ValueError:
                                    pass
                return sorted(set(listening_ports))
    except Exception as e:
        print(f"プロセス検索エラー: {e}")
    return []

def test_report_client_basic_connection():
    """実運用Report Serverとの基本接続テスト"""
    try:
        from WIPCommonPy.clients.report_client import ReportClient
        
        print("   Creating ReportClient...")
        client = ReportClient(host="localhost", port=4112, debug=True)
        
        # テストデータ設定
        print("   Setting test data...")
        client.set_sensor_data(
            area_code="130000",
            weather_code=100,
            temperature=25.0,
            precipitation_prob=30,
            alert=["診断テスト"],
            disaster=[]
        )
        
        # タイムアウト設定
        client.sock.settimeout(5)  # 5秒タイムアウト
        
        # 送信テスト
        print("   Sending report data...")
        result = client.send_report_data()
        
        print("   Closing client...")
        client.close()
        
        if result:
            print(f"   Result: {result}")
            success = result.get("success", False)
            if success:
                print(f"   Area Code: {result.get('area_code', 'N/A')}")
                print(f"   Weather Code: {result.get('weather_code', 'N/A')}")
                print(f"   Temperature: {result.get('temperature', 'N/A')}")
            return success
        else:
            print("   No result returned")
            return False
        
    except Exception as e:
        error_msg = str(e)
        if "10038" not in error_msg and "10054" not in error_msg:  # 一般的なWindows socket errors を抑制
            print(f"   接続テストエラー: {e}")
            import traceback
            traceback.print_exc()
        elif "10054" in error_msg:
            print(f"   Connection reset by peer - server may have rejected the request")
        return False

def test_report_client_basic():
    """基本的なReportClientのテスト"""
    try:
        from WIPCommonPy.clients.report_client import ReportClient
        
        # とりあえずインスタンス作成だけテスト
        client = ReportClient(host="localhost", port=4112, debug=True)
        print("✅ ReportClient クラスのインポートと初期化成功")
        client.close()
        return True
    except Exception as e:
        print(f"❌ ReportClient エラー: {e}")
        return False

def start_test_report_server():
    """テスト用レポートサーバーを起動"""
    try:
        from WIPServerPy.servers.report_server.report_server import ReportServer
        import threading
        
        print("🚀 テスト用レポートサーバーを起動中...")
        
        # テスト用サーバー（本番環境と同じポート4112を使用）
        server = ReportServer(
            host="localhost",
            port=4112,
            debug=True,
            max_workers=2
        )
        
        # バックグラウンドで起動
        def run_server():
            try:
                import sys
                import io
                # 標準エラー出力をキャプチャしてWinError 10038を抑制
                original_stderr = sys.stderr
                sys.stderr = io.StringIO()
                try:
                    server.run()
                finally:
                    # 元の標準エラー出力を復元
                    captured_stderr = sys.stderr.getvalue()
                    sys.stderr = original_stderr
                    # WinError 10038以外のエラーのみ表示
                    if captured_stderr and "WinError 10038" not in captured_stderr:
                        print(captured_stderr)
            except Exception as e:
                if "WinError 10038" not in str(e):
                    print(f"サーバー起動エラー: {e}")
        
        server_thread = threading.Thread(target=run_server, daemon=True)
        server_thread.start()
        
        # 起動まで少し待機
        time.sleep(3)
        
        # 接続テスト
        if check_port_available("localhost", 4112):
            print("✅ テスト用レポートサーバー起動成功")
            return server, server_thread
        else:
            print("❌ テスト用レポートサーバー起動失敗")
            return None, None
            
    except Exception as e:
        print(f"❌ テスト用サーバー起動エラー: {e}")
        return None, None

def test_report_client_with_server(server):
    """サーバーありでのReportClientテスト"""
    try:
        from WIPCommonPy.clients.report_client import ReportClient
        
        print("📤 ReportClient接続テスト中...")
        
        client = ReportClient(host="localhost", port=4112, debug=True)
        
        # テストデータ設定
        client.set_sensor_data(
            area_code="130000",
            weather_code=100,
            temperature=25.0,
            precipitation_prob=30,
            alert=["テスト警報"],
            disaster=[]
        )
        
        # 送信テスト
        result = client.send_report_data()
        client.close()
        
        if result and result.get("success"):
            print("✅ ReportClient 送信テスト成功")
            print(f"   パケットID: {result.get('packet_id')}")
            print(f"   応答時間: {result.get('response_time_ms', 0):.1f}ms")
            return True
        else:
            print("❌ ReportClient 送信テスト失敗")
            return False
            
    except Exception as e:
        print(f"❌ ReportClient接続テストエラー: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """メイン診断関数"""
    print("Report Server Connection Diagnostic Tool")
    print("=" * 50)
    
    # 1. 基本的な環境確認
    print("\n1. 環境確認")
    print("-" * 20)
    
    # Python path確認
    python_path = os.environ.get('PYTHONPATH', '')
    print(f"PYTHONPATH: {python_path}")
    
    # WIPCommonPyインポート確認
    try:
        sys.path.insert(0, '/mnt/c/Users/ポッポ焼き/Desktop/WIP/src')
        import WIPCommonPy
        print("✅ WIPCommonPy インポート成功")
    except Exception as e:
        print(f"❌ WIPCommonPy インポートエラー: {e}")
        return False
    
    # 2. ポート確認
    print("\n2. ポート確認")
    print("-" * 20)
    
    test_ports = [4112]  # Report Serverの標準ポートのみテスト
    available_ports = []
    
    for port in test_ports:
        if check_port_available("localhost", port):
            print(f"✅ Port {port}: 応答あり")
            available_ports.append(port)
        else:
            print(f"❌ Port {port}: 応答なし")
    
    # 3. リスニングプロセス確認
    print("\n3. リスニングプロセス確認")
    print("-" * 30)
    
    listening_ports = find_listening_processes()
    relevant_ports = [p for p in listening_ports if 4000 <= p <= 20000]
    
    print(f"関連ポート範囲(4000-20000)でリスニング中: {relevant_ports}")
    
    # Report Server候補ポートの確認（4112のみ）
    candidate_ports = [p for p in relevant_ports if p == 4112]
    if candidate_ports:
        print(f"Report Server候補ポート: {candidate_ports}")
    else:
        print("Report Serverらしきポートが見つかりません")
    
    # 4. ReportClient基本テスト
    print("\n4. ReportClient基本テスト")
    print("-" * 30)
    
    if not test_report_client_basic():
        return False
    
    # 5. テスト用サーバー起動と接続テスト
    print("\n5. テスト用サーバー起動テスト")
    print("-" * 35)
    
    # 4112ポートをテスト
    print("📤 4112ポートでの接続テスト中...")
    port_test_result = check_port_available("localhost", 4112)
    
    if port_test_result:
        print("✅ 4112ポートで Report Server が応答しています")
        
        # より詳細な接続テスト
        print("📤 詳細な通信テスト中...")
        success = test_report_client_basic_connection()
        
        if success:
            print("✅ 実運用Report Serverとの通信成功")
            print("\n✅ 診断完了: Report Serverは正常に動作しています")
            print("\n💡 結果:")
            print("   Report Serverは4112ポートで正常に動作中です。")
            print("   完全なデータフローが確認されました:")
            print("   Area Code: 130000, Weather Code: 100, Temperature: 25.0°C")
            print("\n   JMAテストを実行できます:")
            print("   python tests/test_jma_api_simple.py --report-port 4112")
        else:
            print("❌ 詳細な通信テストで問題が発生しました")
            print("   ポートは開いているがサーバーの処理に問題がある可能性があります")
        
        return success
    else:
        print("❌ 4112ポートでReport Serverが見つかりません")
    
    # 4112ポートが使用されていない場合のみテストサーバーを起動
    server, thread = start_test_report_server()
    
    if server:
        # 接続テスト実行
        success = test_report_client_with_server(server)
        
        # サーバー停止（エラーを抑制）
        try:
            print("Shutting down test server...")
            server.shutdown()
            # 少し待機してサーバーが完全に停止するまで待つ
            time.sleep(1)
        except Exception as e:
            if "WinError 10038" not in str(e):
                print(f"Shutdown warning: {e}")
            # WinError 10038は無視（既に閉じられたソケットへのアクセス）
        
        if success:
            print("\n✅ 診断完了: ReportClientとサーバー間の通信は正常です")
            print("\n💡 解決策:")
            print("   Report Serverが起動していない可能性があります。")
            print("   以下のコマンドでReport Serverを起動してください:")
            print("   python -m WIPServerPy.servers.report_server.report_server")
            print("   または")
            print("   cd python/application && python -m WIPServerPy.servers.report_server.report_server")
        else:
            print("\n❌ 診断結果: ReportClientまたはサーバーに問題があります")
    else:
        print("\n❌ 診断結果: テスト用サーバーの起動に失敗")
        print("\n💡 考えられる原因:")
        print("   - WIPServerPyモジュールの問題")
        print("   - ポート4112が他のプロセスに使用されている")
        print("   - Pythonパスの設定問題")
    
    # 6. 推奨解決手順
    print("\n6. 推奨解決手順")
    print("-" * 20)
    print("1. Redis サーバーを起動:")
    print("   redis-server")
    print()
    print("2. Report Server を起動:")
    print("   cd /mnt/c/Users/ポッポ焼き/Desktop/WIP")
    print("   python -m WIPServerPy.servers.report_server.report_server")
    print()
    print("3. 環境変数設定 (必要に応じて):")
    print("   export PYTHONPATH='/mnt/c/Users/ポッポ焼き/Desktop/WIP/src:$PYTHONPATH'")
    print()
    print("4. テスト再実行:")
    print("   python tests/test_jma_api_simple.py")
    
    return True

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n診断が中断されました")
    except Exception as e:
        print(f"\n診断エラー: {e}")
        import traceback
        traceback.print_exc()
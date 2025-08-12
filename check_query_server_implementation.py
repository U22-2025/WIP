#!/usr/bin/env python3
"""
QueryServer Implementation Checker
現在のQueryServerの実装を確認し、XML自動取得処理が含まれているかチェックします。
"""

import sys
import os
import inspect
from pathlib import Path

# WIPプロジェクトのsrcディレクトリをPythonパスに追加
current_dir = Path(__file__).resolve().parent
src_dir = current_dir / "src"
sys.path.insert(0, str(src_dir))

def check_query_server_implementation():
    """QueryServerの実装をチェック"""
    print("🔍 QueryServer Implementation Checker")
    print("=" * 60)
    
    try:
        from WIPServerPy.servers.query_server.query_server import QueryServer
        
        print(f"✅ QueryServer インポート成功")
        print(f"📁 モジュールパス: {inspect.getfile(QueryServer)}")
        
        # QueryServerクラスのメソッドを確認
        methods = [method for method in dir(QueryServer) if not method.startswith('_')]
        print(f"\n📋 QueryServerの公開メソッド ({len(methods)}個):")
        for method in sorted(methods):
            print(f"   - {method}")
        
        # XML関連やupdate関連のメソッドがあるかチェック
        suspicious_methods = []
        xml_keywords = ['xml', 'update', 'schedule', 'thread', 'weather_data', 'disaster', 'alert']
        
        for method in dir(QueryServer):
            method_lower = method.lower()
            if any(keyword in method_lower for keyword in xml_keywords):
                suspicious_methods.append(method)
        
        if suspicious_methods:
            print(f"\n⚠️  XML/Update関連の可能性があるメソッド:")
            for method in suspicious_methods:
                print(f"   - {method}")
        else:
            print(f"\n✅ XML/Update関連のメソッドは見つかりませんでした")
        
        # __init__メソッドのシグネチャを確認
        init_signature = inspect.signature(QueryServer.__init__)
        print(f"\n🔧 __init__メソッドのシグネチャ:")
        print(f"   QueryServer{init_signature}")
        
        # noupdateパラメータがあるかチェック
        if 'noupdate' in str(init_signature):
            print("✅ 'noupdate'パラメータが存在します（新しい実装）")
        else:
            print("❌ 'noupdate'パラメータがありません（古い実装の可能性）")
        
        # runメソッドをチェック
        if hasattr(QueryServer, 'run'):
            try:
                run_source = inspect.getsource(QueryServer.run)
                if 'thread' in run_source.lower() or 'update' in run_source.lower():
                    print("\n⚠️  runメソッドにthread/update関連のコードが含まれています")
                    print("   この実装は古いバージョンの可能性があります")
                else:
                    print("\n✅ runメソッドにthread/update関連のコードはありません")
            except Exception as e:
                print(f"\n⚠️  runメソッドのソースコード確認失敗: {e}")
        
        # インスタンス作成テスト
        print(f"\n🧪 インスタンス作成テスト")
        try:
            # noupdate=Trueでインスタンス作成をテスト
            test_server = QueryServer(host="localhost", port=14111, debug=True, noupdate=True)
            print("✅ noupdate=Trueでのインスタンス作成成功")
            
            # 危険なメソッドがないかチェック
            dangerous_attrs = []
            for attr_name in dir(test_server):
                if any(keyword in attr_name.lower() for keyword in ['update', 'schedule', 'xml', 'thread']):
                    if not attr_name.startswith('_'):
                        dangerous_attrs.append(attr_name)
            
            if dangerous_attrs:
                print(f"⚠️  以下の属性が見つかりました:")
                for attr in dangerous_attrs:
                    print(f"   - {attr}")
            else:
                print("✅ XML/Update関連の属性はありません")
                
        except Exception as e:
            print(f"❌ インスタンス作成失敗: {e}")
            import traceback
            traceback.print_exc()
        
        return True
        
    except Exception as e:
        print(f"❌ QueryServerのチェックに失敗: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_git_status():
    """Gitの状態を確認"""
    print(f"\n📊 Git状態確認")
    print("-" * 30)
    
    try:
        import subprocess
        
        # 現在のブランチ確認
        result = subprocess.run(['git', 'branch', '--show-current'], 
                              capture_output=True, text=True, cwd=current_dir)
        if result.returncode == 0:
            current_branch = result.stdout.strip()
            print(f"📍 現在のブランチ: {current_branch}")
        
        # 最新コミット確認
        result = subprocess.run(['git', 'log', '--oneline', '-1'], 
                              capture_output=True, text=True, cwd=current_dir)
        if result.returncode == 0:
            latest_commit = result.stdout.strip()
            print(f"📝 最新コミット: {latest_commit}")
        
        # 変更状態確認
        result = subprocess.run(['git', 'status', '--porcelain'], 
                              capture_output=True, text=True, cwd=current_dir)
        if result.returncode == 0:
            changes = result.stdout.strip()
            if changes:
                print(f"⚠️  未コミットの変更があります:")
                for line in changes.split('\n'):
                    if line.strip():
                        print(f"   {line}")
            else:
                print("✅ 作業ディレクトリはクリーンです")
        
    except Exception as e:
        print(f"Git状態確認エラー: {e}")

def main():
    """メイン実行関数"""
    success = check_query_server_implementation()
    check_git_status()
    
    print(f"\n" + "=" * 60)
    if success:
        print("✅ QueryServer実装チェック完了")
        print("\n💡 Ubuntuサーバーでの問題解決方法:")
        print("1. 同じブランチ(get-data-from-api)にいることを確認")
        print("2. 最新のコードでQueryServerファイルを更新")
        print("3. QueryServerを再起動して新しい実装を反映")
        print("4. noupdate=Trueパラメータを使用してサーバー起動")
    else:
        print("❌ QueryServer実装に問題があります")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
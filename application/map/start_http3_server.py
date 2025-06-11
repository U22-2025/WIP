#!/usr/bin/env python3
"""
HTTP/3対応WTPサーバーの起動スクリプト
"""

import os
import sys
import subprocess
import asyncio

def check_dependencies():
    """必要なパッケージがインストールされているかチェック"""
    required_packages = {
        'quart': 'quart',
        'hypercorn': 'hypercorn[h3]',
        'geopy': 'geopy',
        'aioquic': 'aioquic'
    }
    
    missing_packages = []
    
    for package, install_name in required_packages.items():
        try:
            __import__(package)
            print(f"✓ {package} がインストールされています")
        except ImportError:
            print(f"✗ {package} がインストールされていません")
            missing_packages.append(install_name)
    
    if missing_packages:
        print("\n以下のパッケージをインストールしてください:")
        print("pip install " + " ".join(missing_packages))
        print("\nまたは、requirements_http3.txtを使用:")
        print("pip install -r requirements_http3.txt")
        return False
    
    return True

def check_ssl_certificates():
    """SSL証明書が存在するかチェック"""
    cert_file = "cert.pem"
    key_file = "key.pem"
    
    if os.path.exists(cert_file) and os.path.exists(key_file):
        print(f"✓ SSL証明書が見つかりました: {cert_file}, {key_file}")
        return True
    else:
        print("✗ SSL証明書が見つかりません")
        print("generate_cert.py を実行して証明書を生成してください:")
        print("  python generate_cert.py")
        return False

def install_dependencies():
    """依存関係を自動インストール"""
    print("依存関係をインストールしています...")
    try:
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", 
            "-r", "requirements_http3.txt"
        ])
        print("✓ 依存関係のインストールが完了しました")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ 依存関係のインストールに失敗しました: {e}")
        return False

def generate_certificates():
    """SSL証明書を自動生成"""
    print("SSL証明書を生成しています...")
    try:
        subprocess.check_call([sys.executable, "generate_cert.py"])
        print("✓ SSL証明書の生成が完了しました")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ SSL証明書の生成に失敗しました: {e}")
        return False

def main():
    """メイン関数"""
    print("HTTP/3 WTPサーバー起動準備")
    print("=" * 40)
    
    # カレントディレクトリを確認
    if not os.path.exists("app_http3.py"):
        print("✗ app_http3.py が見つかりません")
        print("application/map/ ディレクトリで実行してください")
        return False
    
    # 依存関係のチェック
    print("\n1. 依存関係のチェック...")
    if not check_dependencies():
        auto_install = input("\n依存関係を自動インストールしますか？ (y/n): ").lower().strip()
        if auto_install == 'y':
            if not install_dependencies():
                return False
        else:
            print("依存関係を手動でインストールしてから再実行してください")
            return False
    
    # SSL証明書のチェック
    print("\n2. SSL証明書のチェック...")
    if not check_ssl_certificates():
        auto_generate = input("\nSSL証明書を自動生成しますか？ (y/n): ").lower().strip()
        if auto_generate == 'y':
            if not generate_certificates():
                return False
        else:
            print("SSL証明書を手動で生成してから再実行してください")
            return False
    
    # サーバー起動
    print("\n3. HTTP/3サーバーを起動しています...")
    print("サーバーを停止するには Ctrl+C を押してください")
    print("-" * 40)
    
    try:
        subprocess.run([sys.executable, "app_http3.py"])
    except KeyboardInterrupt:
        print("\n\nサーバーを停止しました")
    except Exception as e:
        print(f"\nサーバーの起動に失敗しました: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = main()
    if not success:
        sys.exit(1)
    print("\nHTTP/3サーバーのセットアップと起動が完了しました！")

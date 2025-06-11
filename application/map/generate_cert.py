#!/usr/bin/env python3
"""
開発用の自己署名SSL証明書を生成するスクリプト
HTTP/3にはHTTPSが必要なため使用します
"""

import os
import subprocess
import sys

def generate_self_signed_cert():
    """自己署名証明書を生成"""
    cert_file = "cert.pem"
    key_file = "key.pem"
    
    # 既存の証明書ファイルがあるかチェック
    if os.path.exists(cert_file) and os.path.exists(key_file):
        print("SSL証明書が既に存在します。")
        return cert_file, key_file
    
    try:
        # OpenSSLを使用して自己署名証明書を生成
        cmd = [
            "openssl", "req", "-x509", "-newkey", "rsa:4096", 
            "-keyout", key_file, "-out", cert_file, 
            "-days", "365", "-nodes",
            "-subj", "/C=JP/ST=Tokyo/L=Tokyo/O=WTP/OU=Development/CN=localhost"
        ]
        
        print("SSL証明書を生成中...")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"SSL証明書が正常に生成されました:")
            print(f"  証明書ファイル: {cert_file}")
            print(f"  秘密鍵ファイル: {key_file}")
            return cert_file, key_file
        else:
            print("SSL証明書の生成に失敗しました:")
            print(f"エラー: {result.stderr}")
            return None, None
            
    except FileNotFoundError:
        print("OpenSSLが見つかりません。")
        print("WindowsでOpenSSLをインストールしてください:")
        print("1. Git for Windowsをインストール（OpenSSLが含まれています）")
        print("2. または、Win32/Win64 OpenSSL https://slproweb.com/products/Win32OpenSSL.html")
        print("3. Chocolateyを使用: choco install openssl")
        return None, None
    except Exception as e:
        print(f"予期しないエラーが発生しました: {e}")
        return None, None

def check_openssl():
    """OpenSSLが利用可能かチェック"""
    try:
        result = subprocess.run(["openssl", "version"], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"OpenSSL バージョン: {result.stdout.strip()}")
            return True
        else:
            return False
    except FileNotFoundError:
        return False

if __name__ == "__main__":
    print("HTTP/3 WTPサーバー用SSL証明書生成ツール")
    print("=" * 50)
    
    # OpenSSLの確認
    if not check_openssl():
        print("OpenSSLが見つかりません。インストールしてから再実行してください。")
        sys.exit(1)
    
    # 証明書の生成
    cert_file, key_file = generate_self_signed_cert()
    
    if cert_file and key_file:
        print("\n証明書の生成が完了しました！")
        print("警告: これは開発用の自己署名証明書です。")
        print("ブラウザで「証明書が信頼できません」という警告が表示されますが、")
        print("開発用途では「詳細設定」→「localhost にアクセスする（安全ではありません）」")
        print("をクリックしてアクセスしてください。")
    else:
        print("証明書の生成に失敗しました。")
        sys.exit(1)

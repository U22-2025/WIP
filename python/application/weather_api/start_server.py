#!/usr/bin/env python3
"""
Weather API Server Startup Script

WindowsとLinux両対応のサーバー起動スクリプト
"""

import os
import sys
import subprocess
from pathlib import Path

def setup_environment():
    """環境変数とパスの設定"""
    # 現在のディレクトリ設定
    current_dir = Path(__file__).resolve().parent
    root_dir = current_dir.parents[2]  # WIPディレクトリ
    src_dir = root_dir / "src"
    
    # 作業ディレクトリ変更
    os.chdir(current_dir)
    
    # PYTHONPATHに追加
    python_paths = [str(src_dir), str(current_dir)]
    current_pythonpath = os.environ.get('PYTHONPATH', '')
    if current_pythonpath:
        python_paths.append(current_pythonpath)
    os.environ['PYTHONPATH'] = os.pathsep.join(python_paths)
    
    # Weather API環境変数設定
    env_defaults = {
        'WEATHER_API_PORT': '8001',
        'WEATHER_API_HOST': '0.0.0.0', 
        'WEATHER_API_RELOAD': 'false',
        'WEATHER_API_TARGET_OFFICES': '130000,270000,011000,400000,230000',
        'WEATHER_API_SCHEDULE_ENABLED': 'true',
        'WEATHER_API_WEATHER_INTERVAL_MIN': '180',
        'WEATHER_API_DISASTER_INTERVAL_MIN': '10'
    }
    
    for key, default_value in env_defaults.items():
        if key not in os.environ:
            os.environ[key] = default_value
    
    return current_dir, src_dir

def check_dependencies():
    """依存関係の確認"""
    print("🔍 Checking dependencies...")
    
    required_packages = ['fastapi', 'uvicorn', 'requests', 'pydantic']
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"✅ {package}")
        except ImportError:
            print(f"❌ {package}")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n💡 Install missing packages:")
        print(f"   pip install {' '.join(missing_packages)}")
        return False
    
    return True

def start_server_direct():
    """サーバーを直接起動"""
    print("🚀 Starting Weather API Server (Direct Mode)...")
    
    try:
        # 直接インポートして起動
        import uvicorn
        from app import app
        
        port = int(os.environ.get('WEATHER_API_PORT', '8001'))
        host = os.environ.get('WEATHER_API_HOST', '0.0.0.0')
        reload = os.environ.get('WEATHER_API_RELOAD', 'false').lower() == 'true'
        
        print(f"Server starting on {host}:{port}")
        
        uvicorn.run(
            app,
            host=host,
            port=port,
            reload=reload,
            workers=1,
            log_level="info"
        )
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Server startup failed: {e}")
        return False
    
    return True

def start_server_subprocess():
    """uvicornコマンドでサーバー起動"""
    print("🚀 Starting Weather API Server (Subprocess Mode)...")
    
    port = os.environ.get('WEATHER_API_PORT', '8001')
    host = os.environ.get('WEATHER_API_HOST', '0.0.0.0')
    reload = '--reload' if os.environ.get('WEATHER_API_RELOAD', 'false').lower() == 'true' else ''
    
    cmd = [
        sys.executable, '-m', 'uvicorn',
        'app:app',
        '--host', host,
        '--port', port,
    ]
    
    if reload:
        cmd.append('--reload')
    
    print(f"Executing: {' '.join(cmd)}")
    
    try:
        subprocess.run(cmd, check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Server startup failed: {e}")
        return False
    except KeyboardInterrupt:
        print("\n⚠️ Server stopped by user")
        return True

def main():
    """メイン関数"""
    print("Weather API Server Startup")
    print("=" * 40)
    
    # 環境設定
    current_dir, src_dir = setup_environment()
    print(f"📁 Working directory: {current_dir}")
    print(f"📁 Source directory: {src_dir}")
    print(f"🌍 Python path: {os.environ.get('PYTHONPATH', '')}")
    
    # 環境変数表示
    print("\n🔧 Environment Variables:")
    for key in ['WEATHER_API_PORT', 'WEATHER_API_HOST', 'WEATHER_API_TARGET_OFFICES']:
        value = os.environ.get(key, 'Not set')
        print(f"   {key}: {value}")
    
    print()
    
    # 依存関係確認
    if not check_dependencies():
        print("\n❌ Dependency check failed")
        return 1
    
    print("\n" + "=" * 40)
    
    # サーバー起動方法選択
    start_mode = os.environ.get('WEATHER_API_START_MODE', 'direct').lower()
    
    if start_mode == 'subprocess':
        success = start_server_subprocess()
    else:
        success = start_server_direct()
    
    return 0 if success else 1

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n⚠️ Interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
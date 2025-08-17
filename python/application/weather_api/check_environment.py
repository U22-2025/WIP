#!/usr/bin/env python3
"""
Weather API Server Environment Checker

サーバー起動前の環境確認スクリプト
"""

import os
import sys
from pathlib import Path
import importlib.util

def check_python_version():
    """Python バージョン確認"""
    print("🐍 Python Version Check")
    print("-" * 30)
    print(f"Python version: {sys.version}")
    
    version_info = sys.version_info
    if version_info.major >= 3 and version_info.minor >= 8:
        print("✅ Python version is compatible (3.8+)")
        return True
    else:
        print("❌ Python version is too old (requires 3.8+)")
        return False

def check_required_packages():
    """必要なパッケージの確認"""
    print("\n📦 Required Packages Check")
    print("-" * 30)
    
    required_packages = [
        "fastapi",
        "uvicorn", 
        "requests",
        "pydantic"
    ]
    
    all_installed = True
    
    for package in required_packages:
        try:
            spec = importlib.util.find_spec(package)
            if spec is not None:
                print(f"✅ {package}: installed")
            else:
                print(f"❌ {package}: not found")
                all_installed = False
        except ImportError:
            print(f"❌ {package}: not found")
            all_installed = False
    
    if not all_installed:
        print("\n💡 Install missing packages:")
        print("   pip install fastapi uvicorn requests pydantic")
    
    return all_installed

def check_paths():
    """パスとディレクトリ構造確認"""
    print("\n📁 Path Structure Check")
    print("-" * 30)
    
    current_dir = Path(__file__).resolve().parent
    root_dir = current_dir.parents[2]
    src_dir = root_dir / "src"
    
    print(f"Current directory: {current_dir}")
    print(f"Root directory: {root_dir}")
    print(f"Source directory: {src_dir}")
    
    paths_ok = True
    
    # 重要なファイル・ディレクトリの確認
    important_paths = [
        (current_dir / "app.py", "FastAPI app file"),
        (src_dir, "Source directory"),
        (src_dir / "WIPServerPy", "WIPServerPy module"),
        (src_dir / "WIPCommonPy", "WIPCommonPy module")
    ]
    
    for path, description in important_paths:
        if path.exists():
            print(f"✅ {description}: {path}")
        else:
            print(f"❌ {description}: {path} (not found)")
            paths_ok = False
    
    return paths_ok

def check_wip_modules():
    """WIPモジュールのインポート確認"""
    print("\n🔗 WIP Modules Import Check")
    print("-" * 30)
    
    # パスを追加
    current_dir = Path(__file__).resolve().parent
    root_dir = current_dir.parents[2]
    src_dir = root_dir / "src"
    
    sys.path.insert(0, str(src_dir))
    sys.path.insert(0, str(current_dir))
    
    modules_to_check = [
        ("WIPServerPy.data.alert_processor", "AlertDataProcessor"),
        ("WIPServerPy.data.controllers.unified_data_processor", "UnifiedDataProcessor"),
        ("WIPCommonPy.clients.report_client", "ReportClient")
    ]
    
    all_imports_ok = True
    
    for module_name, class_name in modules_to_check:
        try:
            module = importlib.import_module(module_name)
            if hasattr(module, class_name):
                print(f"✅ {module_name}.{class_name}: OK")
            else:
                print(f"❌ {module_name}.{class_name}: Class not found")
                all_imports_ok = False
        except ImportError as e:
            print(f"❌ {module_name}: Import failed - {e}")
            all_imports_ok = False
    
    return all_imports_ok

def check_app_import():
    """FastAPI app のインポート確認"""
    print("\n🚀 FastAPI App Import Check")
    print("-" * 30)
    
    current_dir = Path(__file__).resolve().parent
    os.chdir(current_dir)
    
    try:
        from app import app
        print("✅ FastAPI app imported successfully")
        print(f"   App title: {app.title}")
        print(f"   App version: {app.version}")
        return True
    except ImportError as e:
        print(f"❌ Failed to import FastAPI app: {e}")
        return False
    except Exception as e:
        print(f"❌ Error importing FastAPI app: {e}")
        return False

def check_environment_variables():
    """環境変数確認"""
    print("\n🌍 Environment Variables Check")
    print("-" * 30)
    
    env_vars = [
        ("WEATHER_API_PORT", "8001", "API server port"),
        ("WEATHER_API_HOST", "0.0.0.0", "API server host"),
        ("WEATHER_API_TARGET_OFFICES", "130000", "Target office codes"),
        ("WEATHER_API_RELOAD", "false", "Auto-reload mode"),
    ]
    
    for var_name, default_value, description in env_vars:
        value = os.getenv(var_name, default_value)
        print(f"🔧 {var_name}: {value} ({description})")
    
    return True

def main():
    """メイン診断関数"""
    print("Weather API Server Environment Checker")
    print("=" * 50)
    
    checks = [
        ("Python Version", check_python_version),
        ("Required Packages", check_required_packages), 
        ("Path Structure", check_paths),
        ("WIP Modules", check_wip_modules),
        ("FastAPI App", check_app_import),
        ("Environment Variables", check_environment_variables)
    ]
    
    results = []
    for check_name, check_func in checks:
        try:
            result = check_func()
            results.append((check_name, result))
        except Exception as e:
            print(f"❌ {check_name}: Check failed - {e}")
            results.append((check_name, False))
    
    # 結果サマリー
    print("\n" + "=" * 50)
    print("🏁 Environment Check Summary")
    print("=" * 50)
    
    passed = 0
    for check_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{check_name}: {status}")
        if result:
            passed += 1
    
    total = len(results)
    success_rate = (passed / total) * 100 if total > 0 else 0
    
    print(f"\nOverall: {passed}/{total} checks passed ({success_rate:.1f}%)")
    
    if passed == total:
        print("\n🎉 Environment is ready! You can start the Weather API server.")
        print("\nTo start the server:")
        print("  python run_server.py")
        print("  or")
        print("  start_weather_api.bat")
    else:
        print("\n💥 Some checks failed. Please fix the issues above before starting the server.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
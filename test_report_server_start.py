#!/usr/bin/env python3
import os
import sys
from pathlib import Path

# 環境設定
script_dir = Path(__file__).resolve().parent
src_dir = script_dir / "src"
sys.path.insert(0, str(src_dir))

# 環境変数設定
os.environ['REPORT_SERVER_PORT'] = '4112'
os.environ['REPORT_SERVER_AUTH_ENABLED'] = 'false'
os.environ['REPORT_SERVER_ENABLE_DATABASE'] = 'true'
os.environ['REDIS_KEY_PREFIX'] = ''
os.environ['REPORT_DB_KEY_PREFIX'] = ''

print("Starting Report Server test...")

try:
    from WIPServerPy.servers.report_server.report_server import ReportServer
    
    print("Creating server instance...")
    server = ReportServer(
        host="0.0.0.0",
        port=4112,
        debug=True,
        max_workers=2
    )
    
    print("Starting server...")
    server.run()
    
except KeyboardInterrupt:
    print("\nServer stopped by user")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
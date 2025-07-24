import sys
import os
import time
from WIPCommonPy.clients.utils.packet_id_generator import PacketIDGenerator12Bit

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 環境変数を.envファイルから読み込み
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    print(
        "Warning: python-dotenv not installed. Using system environment variables only."
    )

# コマンドライン引数解析
use_coordinates = "--coord" in sys.argv
use_proxy = "--proxy" in sys.argv
debug_enabled = "--debug" in sys.argv
use_report = "--report" in sys.argv


"""
    --report時のオプション

        --area: エリアコード指定
        --weather: 天気コード指定
        --pops: 降水確率指定
        --temp: 温度指定
        --alert: 警報情報指定（カンマ区切り）
        --disaster: 災害情報指定（カンマ区切り）
        --lat: 緯度指定
        --lon: 経度指定

"""

# 追加オプション引数の解析
area_code = 460010  # デフォルト値: 名古屋
weather_code = 100  # デフォルト値: 晴れ
pops = 30  # デフォルト値: 30%
temperature = 25.0  # デフォルト値: 25℃
alerts = []  # デフォルト値: 空リスト
disasters = []  # デフォルト値: 空リスト
latitude = 35.6895  # デフォルト値: 東京
longitude = 139.6917  # デフォルト値: 東京

# エリアコード指定 (例: --area 010010)
if "--area" in sys.argv:
    idx = sys.argv.index("--area") + 1
    if idx < len(sys.argv):
        try:
            area_code = int(sys.argv[idx])
        except ValueError:
            print(f"無効なエリアコード: {sys.argv[idx]}, デフォルト値を使用します")
            area_code = 460010  # デフォルト値にリセット

# 天気コード指定 (例: --weather 010)
if "--weather" in sys.argv:
    idx = sys.argv.index("--weather") + 1
    if idx < len(sys.argv):
        try:
            weather_code = int(sys.argv[idx])
        except ValueError:
            print(f"無効な天気コード: {sys.argv[idx]}, デフォルト値を使用します")

# 降水確率指定 (例: --pops 50)
if "--pops" in sys.argv:
    idx = sys.argv.index("--pops") + 1
    if idx < len(sys.argv):
        try:
            pops = int(sys.argv[idx])
        except ValueError:
            print(f"無効な降水確率: {sys.argv[idx]}, デフォルト値を使用します")

# 座標指定 (例: --lat 35.6895 --lon 139.6917)
if "--lat" in sys.argv:
    idx = sys.argv.index("--lat") + 1
    if idx < len(sys.argv):
        try:
            latitude = float(sys.argv[idx])
        except ValueError:
            print(f"無効な緯度: {sys.argv[idx]}, デフォルト値を使用します")

if "--lon" in sys.argv:
    idx = sys.argv.index("--lon") + 1
    if idx < len(sys.argv):
        try:
            longitude = float(sys.argv[idx])
        except ValueError:
            print(f"無効な経度: {sys.argv[idx]}, デフォルト値を使用します")

# 引数解析結果を表示
print("\nコマンドライン引数解析結果:")
print(f"use_coordinates: {use_coordinates}")
print(f"use_proxy: {use_proxy}")
print(f"debug_enabled: {debug_enabled}")
print(f"use_report: {use_report}")
print(f"area_code: {area_code} (型: {type(area_code)})")
print(f"weather_code: {weather_code}")
print(f"pops: {pops}")
print(f"temperature: {temperature}")
print(f"alerts: {alerts}")
print(f"disasters: {disasters}")
print(f"latitude: {latitude}")
print(f"longitude: {longitude}")
print("=" * 60)

from WIPClientPy import Client
from WIPCommonPy.packet import LocationRequest

PIDG = PacketIDGenerator12Bit()

# レポート機能のインポート
if use_report:
    from WIPCommonPy.clients.report_client import ReportClient

    # 温度指定 (例: --temp 28.5)
    if "--temp" in sys.argv:
        idx = sys.argv.index("--temp") + 1
        if idx < len(sys.argv):
            try:
                temperature = float(sys.argv[idx])
            except ValueError:
                print(f"無効な温度値: {sys.argv[idx]}, デフォルト値を使用します")

    # 警報指定 (例: --alert "大雨注意報,洪水警報")
    if "--alert" in sys.argv:
        idx = sys.argv.index("--alert") + 1
        if idx < len(sys.argv):
            alerts = [a.strip() for a in sys.argv[idx].split(",") if a.strip()]

    # 災害情報指定 (例: --disaster "河川氾濫情報,土砂災害警戒")
    if "--disaster" in sys.argv:
        idx = sys.argv.index("--disaster") + 1
        if idx < len(sys.argv):
            disasters = [d.strip() for d in sys.argv[idx].split(",") if d.strip()]

    # レポートモードの場合は専用処理
    print("Weather Client Example - Report Mode")
    print("Report mode enabled - Data will be sent to Report Server")
    print("=" * 60)

    print("\n=== Report Mode: Sending dummy data to Report Server ===")
    print("-" * 55)

    # レポートデータ作成前に変数値を確認
    print("\nレポートデータ作成前の変数値:")
    print(f"area_code: {area_code} (型: {type(area_code)})")
    print(f"weather_code: {weather_code}")
    print(f"temperature: {temperature}")
    print(f"pops: {pops}")
    print(f"alerts: {alerts}")
    print(f"disasters: {disasters}")

    # 引数から取得したデータを使用
    report_data = {
        "area_code": area_code,
        "weather_code": weather_code,
        "temperature": temperature,
        "pops": pops,
        "alert": alerts,
        "disaster": disasters,
    }

    print("Using sensor data from command line:")
    for key, value in report_data.items():
        print(f"  {key}: {value}")

    print("\nSending report to Report Server...")
    # レポートモードでは常に直接レポートサーバへ送信
    report_host = os.getenv("REPORT_SERVER_HOST", "localhost")
    report_port = int(os.getenv("REPORT_SERVER_PORT", "4112"))
    report_client = ReportClient(
        host=report_host, port=report_port, debug=debug_enabled
    )
    print(
        f"Using direct mode - sending directly to Report Server ({report_host}:{report_port})"
    )

    try:
        report_client.set_sensor_data(
            area_code=report_data.get("area_code"),
            weather_code=report_data.get("weather_code"),
            temperature=report_data.get("temperature"),
            precipitation_prob=report_data.get("pops"),
            alert=report_data.get("alert"),
            disaster=report_data.get("disaster"),
        )

        start_time = time.time()
        report_result = report_client.send_report_data()
        elapsed_time = time.time() - start_time

        if report_result:
            print(
                f"\nOK Report sent successfully! (Execution time: {elapsed_time:.3f}s)"
            )
            print("=== Report Response ===")
            for key, value in report_result.items():
                print(f"  {key}: {value}")
            print("=======================")
        else:
            print("\n✗ Failed to send report to Report Server")

    except Exception as e:
        print(f"\n✗ Error sending report: {e}")
        if debug_enabled:
            import traceback

            traceback.print_exc()
    finally:
        report_client.close()

    print("\n" + "=" * 60)
    print("Report mode completed")
    # レポートモードの場合は、他の処理を実行せずに終了
    exit(0)

"""通常モードの処理"""
if use_proxy:
    print("Weather Client Example - Via Weather Server (Proxy Mode)")
else:
    print("Weather Client Example - Direct Communication")
print("=" * 60)

# 温度指定 (例: --temp 28.5)
if "--temp" in sys.argv:
    idx = sys.argv.index("--temp") + 1
    if idx < len(sys.argv):
        try:
            temperature = float(sys.argv[idx])
        except ValueError:
            print(f"無効な温度値: {sys.argv[idx]}, デフォルト値を使用します")

# 警報指定 (例: --alert "大雨注意報,洪水警報")
if "--alert" in sys.argv:
    idx = sys.argv.index("--alert") + 1
    if idx < len(sys.argv):
        alerts = [a.strip() for a in sys.argv[idx].split(",") if a.strip()]

# 災害情報指定 (例: --disaster "河川氾濫情報,土砂災害警戒")
if "--disaster" in sys.argv:
    idx = sys.argv.index("--disaster") + 1
    if idx < len(sys.argv):
        disasters = [d.strip() for d in sys.argv[idx].split(",") if d.strip()]

    # レポートデータ作成前に変数値を確認
    print("\nレポートデータ作成前の変数値:")
    print(f"area_code: {area_code} (型: {type(area_code)})")
    print(f"weather_code: {weather_code}")
    print(f"temperature: {temperature}")
    print(f"pops: {pops}")
    print(f"alerts: {alerts}")
    print(f"disasters: {disasters}")

    # 引数から取得したデータを使用
    report_data = {
        "area_code": area_code,
        "weather_code": weather_code,
        "temperature": temperature,
        "pops": pops,
        "alert": alerts,
        "disaster": disasters,
    }

    print("Using sensor data from command line:")
    for key, value in report_data.items():
        print(f"  {key}: {value}")

    print("\nSending report to Report Server...")
    # --proxyがない場合は直接reportサーバへ送信
    if use_proxy:
        # プロキシ経由（weatherサーバ経由）
        weather_host = os.getenv("WEATHER_SERVER_HOST", "localhost")
        weather_port = int(os.getenv("WEATHER_SERVER_PORT", "4110"))
        report_client = ReportClient(
            host=weather_host, port=weather_port, debug=debug_enabled
        )
        print(
            f"Using proxy mode - sending via Weather Server ({weather_host}:{weather_port})"
        )
    else:
        # 直接reportサーバへ送信
        report_host = os.getenv("REPORT_SERVER_HOST", "localhost")
        report_port = int(os.getenv("REPORT_SERVER_PORT", "4112"))
        report_client = ReportClient(
            host=report_host, port=report_port, debug=debug_enabled
        )
        print(
            f"Using direct mode - sending directly to Report Server ({report_host}:{report_port})"
        )

    try:
        report_client.set_sensor_data(
            area_code=report_data.get("area_code"),
            weather_code=report_data.get("weather_code"),
            temperature=report_data.get("temperature"),
            precipitation_prob=report_data.get("pops"),
            alert=report_data.get("alert"),
            disaster=report_data.get("disaster"),
        )

        start_time = time.time()
        report_result = report_client.send_report_data()
        elapsed_time = time.time() - start_time

        if report_result:
            print(
                f"\nOK Report sent successfully! (Execution time: {elapsed_time:.3f}s)"
            )
            print("=== Report Response ===")
            for key, value in report_result.items():
                print(f"  {key}: {value}")
            print("=======================")
        else:
            print("\n✗ Failed to send report to Report Server")

    except Exception as e:
        print(f"\n✗ Error sending report: {e}")
        if debug_enabled:
            import traceback

            traceback.print_exc()
    finally:
        report_client.close()

    print("\n" + "=" * 60)
    print("Report mode completed")
    # レポートモードの場合は、他の処理を実行せずに終了
    exit(0)

client = Client(debug=debug_enabled)

if use_coordinates:
    print("\n1. Coordinate-based request using WIP_Client")
    print("-" * 50)
    client.set_coordinates(latitude, longitude)
    start_time = time.time()
    result = client.get_weather(
        weather=True,
        temperature=True,
        precipitation_prob=True,
        alert=True,
        disaster=True,
        proxy=use_proxy,
    )
else:
    print("\n1. Area code request using WIP_Client")
    print("-" * 40)
    start_time = time.time()
    result = client.get_weather_by_area_code(
        area_code=area_code,
        weather=True,
        temperature=True,
        precipitation_prob=True,
        alert=True,
        disaster=True,
        proxy=use_proxy,
    )

if result:
    elapsed_time = time.time() - start_time
    print(f"\nOK Request successful! (Execution time: {elapsed_time:.3f}s)")
    for key, value in result.items():
        print(f"  {key}: {value}")
    if use_report:
        print("\n--- Sending data to Report Server ---")
        report_host = os.getenv("REPORT_SERVER_HOST", "localhost")
        report_port = int(os.getenv("REPORT_SERVER_PORT", "4112"))
        report_client = ReportClient(
            host=report_host, port=report_port, debug=debug_enabled
        )
        try:
            report_client.set_sensor_data(
                area_code=result.get("area_code"),
                weather_code=result.get("weather_code"),
                temperature=result.get("temperature"),
                precipitation_prob=result.get("precipitation_prob"),
                alert=result.get("alert"),
                disaster=result.get("disaster"),
            )
            report_result = report_client.send_report_data()
            if report_result:
                print(f"OK Report sent successfully! Response: {report_result}")
            else:
                print("✗ Failed to send report to Report Server")
        finally:
            report_client.close()
else:
    print("\n✗ Failed to get weather data")

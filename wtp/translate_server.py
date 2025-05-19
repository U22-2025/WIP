import psycopg2
import struct

# 仮の接続情報（必要に応じて書き換えてください）
DB_NAME = "weather_forecast_map"
DB_USER = "username"
DB_PASSWORD = "password"
DB_HOST = "localhost"
DB_PORT = "5432"

# 取得したい座標（例：経度 139.6917, 緯度 35.6895）
longitude = 139.6917
latitude = 35.6895

# 接続して地方名を取得する関数
def get_district_name(longitude, latitude):
    conn = None
    cursor = None

    try:
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user="bababa",
            password="ncc",
            host=DB_HOST,
            port=DB_PORT
        )
        cursor = conn.cursor()
        
        query = f"""
        SELECT code
        FROM districts
        WHERE ST_Within(
            ST_GeomFromText('POINT({longitude} {latitude})', 6668),
            geom
        );
        """
        cursor.execute(query)
        result = cursor.fetchone()

        if result:
            return result[0]
        else:
            return "該当する地方が見つかりませんでした。"

    except Exception as e:
        return f"エラーが発生しました: {e}"

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def parse_response(self, data):
    """Parse incoming request data"""
    # Byte 0: version (3) + packet_id (5)
    first_byte = data[0]
    version = (first_byte >> 4) & 0x0F
    packet_id_high = first_byte & 0x0F

    # Byte 1: packet_id (8)
    second_byte = data[1]
    packet_id = (packet_id_high << 8) | second_byte

    # Byte 2: type (4) + flags (4)
    third_byte = data[2]
    req_type = (third_byte >> 4) & 0x0F
    flags_value = third_byte & 0x0F

    flags = {
        'flag1': (flags_value >> 3) & 0x01,
        'flag2': (flags_value >> 2) & 0x01,
        'flag3': (flags_value >> 1) & 0x01,
        'flag4': flags_value & 0x01,
    }

    # Byte 3: time_specified (1) + reserved (7)
    fourth_byte = data[3]
    flags += {
        'flag5': (fourth_byte >> 7) & 0x01
    }
    time_specified = (fourth_byte >> 4) & 0x07
    reserved = fourth_byte & 0x0F

    # Bytes 4-11: timestamp (8 bytes)
    timestamp = struct.unpack('!Q', data[4:12])[0]

    # Bytes 12-13: region code (2 bytes)
    fifth_byte = data[14]
    region_bit = data [12:14] + (fifth_byte >> 4) & 0x0F
    region_code = struct.unpack('!H', region_bit )[0]

    # Bytes 14-17: checksum (4 bytes)
    checksum_bit = fifth_byte & 0x0F + data[15:18]
    checksum = struct.unpack('!I', checksum_bit)[0]

    weather_code = struct.unpack('!H', data[18:20])[0]
    tempreature = struct.unpack('!H', data[20])[0]
    pops = struct.unpack('!H', data[21])[0]

    plus_field = struct.unpack('!H', data[22:])[0]

    return {
        'version': version,
        'packet_id': packet_id,
        'type': req_type,
        'flags': flags,
        'day' : time_specified,
        'reserved': reserved,
        'timestamp': timestamp,
        'area_code': region_code,
        'checksum': checksum,
        'weather_code': weather_code,
        'tempreature': tempreature,
        'pops': pops,
        'plus_field': plus_field
    }


# 使用例
district_name = get_district_name(139.6917, 35.6895)
print("地方名:", district_name)


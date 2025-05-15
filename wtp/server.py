import socket
import struct
import time

class WeatherServer:
    def __init__(self, host='localhost', port=12345, debug=False):
        self.host = host
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((self.host, self.port))
        self.debug = debug
        
        # Protocol constants
        self.VERSION = 1  # 4 bits
        self.REQUEST_TYPE = 0
        self.RESPONSE_TYPE = 1
        
    def _hex_dump(self, data):
        """Create a hex dump of binary data"""
        hex_str = ' '.join(f'{b:02x}' for b in data)
        ascii_str = ''.join(chr(b) if 32 <= b <= 126 else '.' for b in data)
        return f"Hex: {hex_str}\nASCII: {ascii_str}"
        
    def _debug_print_request(self, data, parsed):
        """Print debug information for request packet"""
        if not self.debug:
            return
            
        print("\n=== RECEIVED REQUEST PACKET ===")
        print(f"Total Length: {len(data)} bytes")
        print("\nHeader:")
        print(f"Version: {parsed['version']}")
        print(f"Type: REQUEST ({parsed['type']})")
        print(f"Region ID: {parsed['region_id']}")
        print(f"Timestamp: {time.ctime(parsed['timestamp'])}")
        print("\nFlags:")
        for flag, value in parsed['flags'].items():
            print(f"{flag}: {value}")
        print("\nRaw Packet:")
        print(self._hex_dump(data))
        print("===========================\n")
        
    def _debug_print_response(self, response, request):
        """Print debug information for response packet"""
        if not self.debug:
            return
            
        print("\n=== SENDING RESPONSE PACKET ===")
        print(f"Total Length: {len(response)} bytes")
        print("\nHeader:")
        print(f"Version: {self.VERSION}")
        print(f"Type: RESPONSE ({self.RESPONSE_TYPE})")
        print(f"Region ID: {request['region_id']}")
        print(f"Timestamp: {time.ctime(int(time.time()))}")
        print("\nRaw Packet:")
        print(self._hex_dump(response))
        print("============================\n")
        
    def parse_request(self, data):
        """Parse incoming request data"""
        # 1byte: version(4) + type(1) + time(3)
        first_byte = data[0]
        version = (first_byte >> 4) & 0x0F
        req_type = (first_byte >> 3) & 0x01
        time_field = first_byte & 0x07
        
        # 1byte: flags(5) + ip_version(3)
        second_byte = data[1]
        flags_value = (second_byte >> 3) & 0x1F
        ip_version = second_byte & 0x07

        # フラグをビットごとに分割
        flags = {
            'weather': (flags_value >> 4) & 0x01,
            'temperature': (flags_value >> 3) & 0x01,
            'precipitation': (flags_value >> 2) & 0x01,
            'alert': (flags_value >> 1) & 0x01,
            'disaster': flags_value & 0x01,
        }

        # 2byte: packet_id
        packet_id = struct.unpack('!H', data[2:4])[0]

        # 16byte: region (latitude 8byte + longitude 8byte)
        latitude = struct.unpack('!Q', data[4:12])[0]
        longitude = struct.unpack('!Q', data[12:20])[0]

        # 8byte: timestamp
        timestamp = struct.unpack('!Q', data[20:28])[0]

        # 2byte: weather code
        weather_code = struct.unpack('!H', data[28:30])[0]

        # 3byte: temperature (current, max, min)
        temp_bytes = data[30:33]
        temperature = {
            'current': struct.unpack('b', temp_bytes[0:1])[0],
            'max': struct.unpack('b', temp_bytes[1:2])[0],
            'min': struct.unpack('b', temp_bytes[2:3])[0]
        }

        # 1byte: precipitation(5bit) + reserved(3bit)
        prec_and_reserved = data[33]
        precipitation = (prec_and_reserved >> 3) & 0x1F
        reserved = prec_and_reserved & 0x07
        
        # 拡張フィールドはdata[34:]以降

        return {
            'version': version,
            'type': req_type,
            'time_field': time_field,
            'flags': flags,
            'ip_version': ip_version,
            'packet_id': packet_id,
            'latitude': latitude,
            'longitude': longitude,
            'timestamp': timestamp,
            'weather_code': weather_code,
            'temperature': temperature,
            'precipitation': precipitation,
            'reserved': reserved,
            'extension': data[34:]
        }

    def create_response(self, request):

        # flagsを5ビットにまとめる
        flags = request['flags']
            flags_value = (
            ((flags.get('weather', 0) & 0x01) << 4) |
            ((flags.get('temperature', 0) & 0x01) << 3) |
            ((flags.get('precipitation', 0) & 0x01) << 2) |
            ((flags.get('alert', 0) & 0x01) << 1) |
            (flags.get('disaster', 0) & 0x01)
        )

        # 1byte: version(4) + type(1) + time(3)
        first_byte = ((self.VERSION & 0x0F) << 4) | ((self.RESPONSE_TYPE & 0x01) << 3) | (request['time_field'] & 0x07)
        # 1byte: flags(5) + ip_version(3)
        second_byte = ((flags_value & 0x1F) << 3) | (request['ip_version'] & 0x07)
        # 2byte: packet_id
        packet_id = struct.pack('!H', request['packet_id'])
        # 8byte: latitude, 8byte: longitude
        latitude = struct.pack('!Q', request['latitude'])
        longitude = struct.pack('!Q', request['longitude'])
        # 8byte: current timestamp
        timestamp = struct.pack('!Q', int(time.time()))
        # 2byte: weather code (例: 晴れ=1)
        weather_code = struct.pack('!H', 1)
        # 3byte: temperature (例: 25, 30, 20)
        temp_bytes = struct.pack('bbb', 25, 30, 20)
        # 1byte: precipitation(5bit=6=30%) + reserved(3bit=0)
        precipitation = (6 << 3) | 0
        prec_byte = struct.pack('B', precipitation)
        # 拡張フィールドなし

        return bytes([first_byte, second_byte]) + packet_id + latitude + longitude + timestamp + weather_code + temp_bytes + prec_byte
        
    def run(self):
        """Start the weather server"""
        print(f"Weather server running on {self.host}:{self.port}")
        
        while True:
            try:
                start_time = time.time()
                data, addr = self.sock.recvfrom(1024)
                print(f"Received request from {addr}")
                
                # Measure request parsing time
                parse_start = time.time()
                request = self.parse_request(data)
                parse_time = time.time() - parse_start
                self._debug_print_request(data, request)
                
                # Measure response creation time
                response_start = time.time()
                response = self.create_response(request)
                response_time = time.time() - response_start
                self._debug_print_response(response, request)
                
                # Send response and calculate total time
                self.sock.sendto(response, addr)
                total_time = time.time() - start_time
                
                if self.debug:
                    print("\n=== TIMING INFORMATION ===")
                    print(f"Request parsing time: {parse_time*1000:.2f}ms")
                    print(f"Response creation time: {response_time*1000:.2f}ms")
                    print(f"Total processing time: {total_time*1000:.2f}ms")
                    print("========================\n")
                
                print(f"Sent response to {addr}")
                
            except Exception as e:
                print(f"Error processing request: {e}")
                continue

if __name__ == "__main__":
    server = WeatherServer(debug=True)
    server.run()

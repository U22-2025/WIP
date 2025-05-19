import socket
import struct
import ipaddress
import time
import random

class LocationResolverClient:
    def __init__(self, host='localhost', port=4109, debug=False):
        """Initialize the location resolver client"""
        self.server_host = host
        self.server_port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.debug = debug

    def _hex_dump(self, data):
        """Create a hex dump of binary data"""
        hex_str = ' '.join(f'{b:02x}' for b in data)
        ascii_str = ''.join(chr(b) if 32 <= b <= 126 else '.' for b in data)
        return f"Hex: {hex_str}\nASCII: {ascii_str}"

    def _debug_print_request(self, data, latitude, longitude):
        """Print debug information for request packet"""
        if not self.debug:
            return

        print("\n=== SENDING REQUEST PACKET ===")
        print(f"Total Length: {len(data)} bytes")
        print("\nCoordinates:")
        print(f"Latitude: {latitude}")
        print(f"Longitude: {longitude}")
        print("\nRaw Packet:")
        print(self._hex_dump(data))
        print("===========================\n")

    def _debug_print_response(self, data, region_code, weather_server_ip):
        """Print debug information for response packet"""
        if not self.debug:
            return

        print("\n=== RECEIVED RESPONSE PACKET ===")
        print(f"Total Length: {len(data)} bytes")
        print(f"Region Code: {region_code}")
        print(f"Weather Server IP: {weather_server_ip}")
        print("\nRaw Packet:")
        print(self._hex_dump(data))
        print("============================\n")

    def create_request(self, latitude, longitude):
        """Create binary request packet with coordinates"""
        # Pack latitude and longitude as 64-bit doubles
        return struct.pack('!dd', latitude, longitude)

    def parse_response(self, data):
        """Parse response packet containing region code and weather server IP"""
        if len(data) != 8:  # 64 bits = 8 bytes
            raise ValueError("Invalid response length")

        # Extract region code (4 bytes)
        region_code = struct.unpack('!I', data[0:4])[0]

        # Extract IP address (4 bytes)
        ip_bytes = data[4:8]
        weather_server_ip = str(ipaddress.IPv4Address(ip_bytes))

        return {
            'region_code': region_code,
            'weather_server_ip': weather_server_ip
        }

    def get_location_info(self, latitude, longitude):
        """Send coordinates and get location information"""
        try:
            start_time = time.time()

            # Create request packet
            request_start = time.time()
            request = self.create_request(latitude, longitude)
            request_time = time.time() - request_start
            self._debug_print_request(request, latitude, longitude)

            # Send request and receive response
            network_start = time.time()
            self.sock.sendto(request, (self.server_host, self.server_port))
            if self.debug:
                print(f"Sent request to {self.server_host}:{self.server_port}")

            data, addr = self.sock.recvfrom(1024)
            network_time = time.time() - network_start
            if self.debug:
                print(f"Received response from {addr}")

            # Parse response
            parse_start = time.time()
            response = self.parse_response(data)
            parse_time = time.time() - parse_start
            self._debug_print_response(
                data,
                response['region_code'],
                response['weather_server_ip']
            )

            total_time = time.time() - start_time

            if self.debug:
                print("\n=== TIMING INFORMATION ===")
                print(f"Request creation time: {request_time*1000:.2f}ms")
                print(f"Network round-trip time: {network_time*1000:.2f}ms")
                print(f"Response parsing time: {parse_time*1000:.2f}ms")
                print(f"Total processing time: {total_time*1000:.2f}ms")
                print("========================\n")

            return response, total_time

        except Exception as e:
            print(f"Error communicating with location resolver: {e}")
            return None, 0

    def close(self):
        """Close the socket"""
        self.sock.close()

def generate_random_japan_coordinates():
    """Generate random coordinates within Japan's main islands"""
    # Define regions for Japan's main islands
    regions = [
        # Honshu (本州) - divided into multiple parts for better coverage
        {'lat': (34.5, 37.5), 'lon': (134.0, 137.0)},  # 中部
        {'lat': (36.0, 38.5), 'lon': (137.0, 140.0)},  # 関東
        {'lat': (38.5, 40.5), 'lon': (140.0, 141.5)},  # 東北南部
        {'lat': (40.5, 41.5), 'lon': (141.0, 142.0)},  # 東北北部
        
        # Hokkaido (北海道)
        {'lat': (41.5, 45.0), 'lon': (141.5, 145.5)},
        
        # Kyushu (九州)
        {'lat': (31.5, 33.5), 'lon': (130.0, 132.0)},
        
        # Shikoku (四国)
        {'lat': (32.5, 34.5), 'lon': (132.5, 134.5)},
    ]
    
    # Randomly select a region
    region = random.choice(regions)
    
    # Generate coordinates within the selected region
    latitude = random.uniform(region['lat'][0], region['lat'][1])
    longitude = random.uniform(region['lon'][0], region['lon'][1])
    
    return latitude, longitude

def performance_test():
    """Performance test with random coordinates in Japan"""
    # テストパラメータ
    num_requests = 100  # リクエスト回数
    client = LocationResolverClient(debug=False)  # デバッグ出力は無効化
    processing_times = []

    try:
        print(f"Sending {num_requests} requests with random coordinates in Japan...")
        
        for i in range(num_requests):
            latitude, longitude = generate_random_japan_coordinates()
            result, total_time = client.get_location_info(latitude, longitude)
            
            if result:
                processing_times.append(total_time)
                print(f"Request {i+1}/{num_requests}: {total_time*1000:.2f}ms")
                print(result)
            else:
                print(f"Request {i+1}/{num_requests}: Failed")

        # 統計情報の計算と表示
        if processing_times:
            avg_time = sum(processing_times) / len(processing_times)
            min_time = min(processing_times)
            max_time = max(processing_times)
            
            print("\nPerformance Statistics:")
            print(f"Average processing time: {avg_time*1000:.2f}ms")
            print(f"Minimum processing time: {min_time*1000:.2f}ms")
            print(f"Maximum processing time: {max_time*1000:.2f}ms")
            print(f"Successful requests: {len(processing_times)}/{num_requests}")
        else:
            print("No successful requests to analyze")

    finally:
        client.close()

def main():
    """Send a single location request with coordinates"""
    # 東京の座標を使用
    latitude = 35.6895
    longitude = 139.6917
    
    client = LocationResolverClient(debug=False)  # デバッグ出力を有効化
    try:
        result, total_time = client.get_location_info(latitude, longitude)
        if result:
            print(f"\nLocation request completed in {total_time*1000:.2f}ms")
            print(f"Region Code: {result['region_code']}")
            print(f"Weather Server IP: {result['weather_server_ip']}")
        else:
            print("Location request failed")
    finally:
        client.close()

if __name__ == "__main__":
    main()

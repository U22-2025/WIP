import socket
import struct
import ipaddress
import time
import random
from packet import Request, Response
from packet_id_12bit import PacketIDGenerator12Bit
from datetime import datetime
PIDG = PacketIDGenerator12Bit()




class LocationResolverClient:
    def __init__(self, host='localhost', port=4109, debug=False):
        """Initialize the location resolver client"""
        self.server_host = host
        self.server_port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.debug = debug
        self.VERSION = 1

    def _hex_dump(self, data):
        """Create a hex dump of binary data"""
        hex_str = ' '.join(f'{b:02x}' for b in data)
        ascii_str = ''.join(chr(b) if 32 <= b <= 126 else '.' for b in data)
        return f"Hex: {hex_str}\nASCII: {ascii_str}"

    def _debug_print_request(self, data):
        """Print debug information for request packet"""
        if not self.debug:
            return

        print("\n=== SENDING REQUEST PACKET ===")
        print(f"Total Length: {len(data.to_bytes())} bytes")
        print("\nCoordinates:")
        print(f"Latitude: {data.ex_field['latitude']}")
        print(f"Longitude: {data.ex_field['longitude']}")
        print("\nRaw Packet:")
        print(self._hex_dump(data.to_bytes()))
        print("===========================\n")

    def _debug_print_response(self, data, region_code, weather_server_ip=None):
        """Print debug information for response packet"""
        if not self.debug:
            return

        print("\n=== RECEIVED RESPONSE PACKET ===")
        print(f"Total Length: {len(data)} bytes")
        print(f"Region Code: {region_code}")
        # print(f"Weather Server IP: {weather_server_ip}")
        print("\nRaw Packet:")
        print(self._hex_dump(data))
        print("============================\n")

    

    def get_location_info(self, latitude, longitude):
        # """Send coordinates and get location information"""
        # try:
            start_time = time.time()

            # Create request packet
            request_start = time.time()
            request = Request(
                version=self.VERSION, 
                packet_id=PIDG.next_id(), 
                type=0, 
                timestamp=int(datetime.now().timestamp()), 
                ex_field={
                    "latitude": latitude, 
                    "longitude": longitude
                }, 
                ex_flag=1)
            request_time = time.time() - request_start
            self._debug_print_request(request)

            # Send request and receive response
            network_start = time.time()
            self.sock.sendto(request.to_bytes(), (self.server_host, self.server_port))
            if self.debug:
                print(f"Sent request to {self.server_host}:{self.server_port}")

            data, addr = self.sock.recvfrom(1024)
            network_time = time.time() - network_start
            if self.debug:
                print(f"Received response from {addr}")

            # Parse response
            parse_start = time.time()
            response = Response.from_bytes(data)
            parse_time = time.time() - parse_start
            self._debug_print_response(
                data,
                response.area_code
            )

            total_time = time.time() - start_time

            if self.debug:
                print("\n=== TIMING INFORMATION ===")
                print(f"Request creation time: {request_time*1000:.2f}ms")
                print(f"Request send time: {(network_start - request_start)*1000:.2f}ms")
                print(f"Network round-trip time: {network_time*1000:.2f}ms")
                print(f"Response parsing time: {parse_time*1000:.2f}ms")
                print(f"Total processing time: {total_time*1000:.2f}ms")
                print("========================\n")

            return response, total_time

        # except Exception as e:
        #     print(f"Error communicating with location resolver: {e}")
        #     return None, 0

    def close(self):
        """Close the socket"""
        self.sock.close()



def main():
    """Send a single location request with coordinates"""
    # 東京の座標を使用
    latitude = 35.6895
    longitude = 139.6917
    
    client = LocationResolverClient(debug=True)  # デバッグ出力を有効化
    try:
        result, total_time = client.get_location_info(latitude, longitude)
        if result:
            print(f"\nLocation request completed in {total_time*1000:.2f}ms")
            print(f"Region Code: {result.area_code}")
            # print(f"Weather Server IP: {result['weather_server_ip']}")
        else:
            print("Location request failed")
    finally:
        client.close()

if __name__ == "__main__":
    main()
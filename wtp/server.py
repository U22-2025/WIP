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
        # First byte: Version (4 bits) + Type (1 bit) + Reserved (3 bits)
        version_type = data[0]
        version = (version_type >> 4) & 0x0F
        req_type = (version_type >> 3) & 0x01
        
        # Region ID (2 bytes)
        region_id = struct.unpack('!H', data[1:3])[0]
        
        # Timestamp (8 bytes)
        timestamp = struct.unpack('!Q', data[3:11])[0]
        
        # Flags (1 byte)
        flags = data[11]
        weather_flag = (flags >> 4) & 0x01
        temp_flag = (flags >> 3) & 0x01
        rain_prob_flag = (flags >> 2) & 0x01
        warning_flag = (flags >> 1) & 0x01
        disaster_flag = flags & 0x01
        
        return {
            'version': version,
            'type': req_type,
            'region_id': region_id,
            'timestamp': timestamp,
            'flags': {
                'weather': weather_flag,
                'temperature': temp_flag,
                'rain_probability': rain_prob_flag,
                'warning': warning_flag,
                'disaster': disaster_flag
            }
        }
        
    def create_response(self, request):
        """Create response packet with dummy data"""
        # Create response header
        header = bytearray()
        
        # Version and Type
        version_type = (self.VERSION << 4) | (self.RESPONSE_TYPE << 3)
        header.append(version_type)
        
        # Region ID
        header.extend(struct.pack('!H', request['region_id']))
        
        # Current timestamp
        current_time = int(time.time())
        header.extend(struct.pack('!Q', current_time))
        
        # Weather data based on flags (using dummy values)
        data = bytearray()
        if request['flags']['weather']:
            weather_code = 1  # 1 = sunny
            data.append(weather_code)
            
        if request['flags']['temperature']:
            temp = 25  # 25 degrees
            data.extend(struct.pack('!h', temp))
            
        if request['flags']['rain_probability']:
            prob = 30  # 30% chance of rain
            data.append(prob)
            
        if request['flags']['warning']:
            warning_code = 0  # 0 = no warning
            data.append(warning_code)
            
        if request['flags']['disaster']:
            disaster_code = 0  # 0 = no disaster
            data.append(disaster_code)
            
        return header + data
        
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

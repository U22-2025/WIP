import socket
import struct
import time

class WeatherClient:
    def __init__(self, host='localhost', port=12345, debug=False):
        self.host = host
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
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
        
    def _debug_print_request(self, request, region_id, flags):
        """Print debug information for request packet"""
        if not self.debug:
            return
            
        print("\n=== REQUEST PACKET ===")
        print(f"Total Length: {len(request)} bytes")
        print("\nHeader:")
        print(f"Version: {self.VERSION}")
        print(f"Type: REQUEST ({self.REQUEST_TYPE})")
        print(f"Region ID: {region_id}")
        print(f"\nFlags:")
        print(f"Weather: {flags['weather']}")
        print(f"Temperature: {flags['temperature']}")
        print(f"Rain Probability: {flags['rain_probability']}")
        print(f"Warning: {flags['warning']}")
        print(f"Disaster: {flags['disaster']}")
        print("\nRaw Packet:")
        print(self._hex_dump(request))
        print("===================\n")
        
    def _debug_print_response(self, response, result):
        """Print debug information for response packet"""
        if not self.debug:
            return
            
        print("\n=== RESPONSE PACKET ===")
        print(f"Total Length: {len(response)} bytes")
        print("\nHeader:")
        print(f"Version: {result['version']}")
        print(f"Type: RESPONSE ({result['type']})")
        print(f"Region ID: {result['region_id']}")
        print(f"Timestamp: {time.ctime(result['timestamp'])}")
        print("\nData:")
        for key, value in result.items():
            if key not in ['version', 'type', 'region_id', 'timestamp']:
                print(f"{key}: {value}")
        print("\nRaw Packet:")
        print(self._hex_dump(response))
        print("=====================\n")
        
    def create_request(self, region_id, weather=True, temperature=True, 
                      rain_probability=True, warning=True, disaster=True):
        """Create a request packet"""
        request = bytearray()
        
        # Version and Type (4 bits version + 1 bit type + 3 bits reserved)
        version_type = (self.VERSION << 4) | (self.REQUEST_TYPE << 3)
        request.append(version_type)
        
        # Region ID (2 bytes)
        request.extend(struct.pack('!H', region_id))
        
        # Current timestamp (8 bytes)
        current_time = int(time.time())
        request.extend(struct.pack('!Q', current_time))
        
        # Flags (1 byte)
        flags = (weather << 4) | (temperature << 3) | (rain_probability << 2) | \
                (warning << 1) | disaster
        request.append(flags)
        
        return request
        
    def parse_response(self, data, flags):
        """Parse response packet"""
        # Parse header
        version_type = data[0]
        version = (version_type >> 4) & 0x0F
        resp_type = (version_type >> 3) & 0x01
        
        region_id = struct.unpack('!H', data[1:3])[0]
        timestamp = struct.unpack('!Q', data[3:11])[0]
        
        # Parse weather data based on flags
        result = {
            'version': version,
            'type': resp_type,
            'region_id': region_id,
            'timestamp': timestamp
        }
        
        # Current position in data
        pos = 11
        
        if flags['weather']:
            result['weather_code'] = data[pos]
            pos += 1
            
        if flags['temperature']:
            result['temperature'] = struct.unpack('!h', data[pos:pos+2])[0]
            pos += 2
            
        if flags['rain_probability']:
            result['rain_probability'] = data[pos]
            pos += 1
            
        if flags['warning']:
            result['warning_code'] = data[pos]
            pos += 1
            
        if flags['disaster']:
            result['disaster_code'] = data[pos]
            pos += 1
            
        return result
        
    def get_weather(self, region_id, weather=True, temperature=True, 
                   rain_probability=True, warning=True, disaster=True, debug=None):
        """Get weather information for a specific region"""
        # Set debug mode for this request if specified
        original_debug = self.debug
        if debug is not None:
            self.debug = debug
            
        try:
            start_time = time.time()
            
            # Create request and measure time
            flags = {
                'weather': weather,
                'temperature': temperature,
                'rain_probability': rain_probability,
                'warning': warning,
                'disaster': disaster
            }
            
            request_start = time.time()
            request = self.create_request(
                region_id, weather, temperature, rain_probability, warning, disaster
            )
            request_time = time.time() - request_start
            
            self._debug_print_request(request, region_id, flags)
            
            # Send request and start measuring network time
            network_start = time.time()
            self.sock.sendto(request, (self.host, self.port))
            
            # Receive response
            response, _ = self.sock.recvfrom(1024)
            network_time = time.time() - network_start
            
            # Parse response and measure time
            parse_start = time.time()
            result = self.parse_response(response, flags)
            parse_time = time.time() - parse_start
            
            self._debug_print_response(response, result)
            
            # Calculate total time
            total_time = time.time() - start_time
            
            if self.debug:
                print("\n=== TIMING INFORMATION ===")
                print(f"Request creation time: {request_time*1000:.2f}ms")
                print(f"Network round-trip time: {network_time*1000:.2f}ms")
                print(f"Response parsing time: {parse_time*1000:.2f}ms")
                print(f"Total operation time: {total_time*1000:.2f}ms")
                print("========================\n")
            
            return result
            
        finally:
            # Restore original debug setting
            if debug is not None:
                self.debug = original_debug
        
    def close(self):
        """Close the client socket"""
        self.sock.close()

def main():
    """Example usage of the WeatherClient"""
    client = WeatherClient(debug=True)
    try:
        # Get weather for region 1
        result = client.get_weather(1)
        print("\nWeather information for region 1:")
        print(f"Timestamp: {time.ctime(result['timestamp'])}")
        if 'weather_code' in result:
            print(f"Weather Code: {result['weather_code']}")
        if 'temperature' in result:
            print(f"Temperature: {result['temperature']}°C")
        if 'rain_probability' in result:
            print(f"Rain Probability: {result['rain_probability']}%")
        if 'warning_code' in result:
            print(f"Warning Code: {result['warning_code']}")
        if 'disaster_code' in result:
            print(f"Disaster Code: {result['disaster_code']}")
            
    finally:
        client.close()

if __name__ == "__main__":
    main()

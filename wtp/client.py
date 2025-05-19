import socket
import struct
import time

class WeatherClient:
    def __init__(self, host='localhost', port=4110, debug=False):
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
        
    def parse_location_resolver_response(self, data):
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
        req_type = (third_byte >> 5) & 0x07
        flags_value = third_byte & 0x0F

        flags = {
            'weather': (flags_value >> 4) & 0x01,
            'tempreature': (flags_value >> 3) & 0x01,
            'pops': (flags_value >> 2) & 0x01,
            'alert': (flags_value >> 1) & 0x01,
            'disaster': flags_value & 0x01,
        }

        # Byte 3: time_specified (1) + reserved (7)
        fourth_byte = data[3]
        flags += {
            'plus_field': (fourth_byte >> 7) & 0x01
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

        longitude = struct.unpack('!H', data[18:26])[0]
        latitude = struct.unpack('!H', data[26:34])[0]

        ex_field = struct.unpack('!H', data[34:])[0]

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
            'longitude': longitude,
            'latitude': latitude,
            'ex_field': ex_field
        }
        
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

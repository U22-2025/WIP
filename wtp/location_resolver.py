import socket
import struct
import psycopg2
from psycopg2 import pool
import time
from collections import OrderedDict
import config
from wtp import packet_format

class LRUCache:
    def __init__(self, maxsize=1000):
        self.cache = OrderedDict()
        self.maxsize = maxsize

    def __getitem__(self, key):
        value = self.cache.pop(key)
        self.cache[key] = value  # Move to end (most recently used)
        return value

    def __setitem__(self, key, value):
        if key in self.cache:
            self.cache.pop(key)
        elif len(self.cache) >= self.maxsize:
            self.cache.popitem(last=False)  # Remove least recently used
        self.cache[key] = value

    def __contains__(self, key):
        return key in self.cache

class LocationResolver:
    def __init__(self, host='localhost', port=4109, debug=False, max_cache_size=1000):
        # Database configuration
        self.DB_NAME = "weather_forecast_map"
        self.DB_USER = config.DB_USERNAME
        self.DB_PASSWORD = config.DB_PASSWORD
        self.DB_HOST = "localhost"
        self.DB_PORT = "5432"
        
        resolver_response = packet_format.resolver_request()
        

        try:
            # Initialize connection pool
            self.connection_pool = psycopg2.pool.SimpleConnectionPool(
                1,  # minimum number of connections
                10, # maximum number of connections
                dbname=self.DB_NAME,
                user=self.DB_USER,
                password=self.DB_PASSWORD,
                host=self.DB_HOST,
                port=self.DB_PORT
            )
            
            # Test database connection
            conn = self.connection_pool.getconn()
            cursor = conn.cursor()
            cursor.execute('SELECT 1')
            cursor.close()
            self.connection_pool.putconn(conn)
            
        except (Exception, psycopg2.Error) as error:
            print(f"Error connecting to PostgreSQL database: {error}")
            if hasattr(self, 'connection_pool'):
                self.connection_pool.closeall()
            raise SystemExit(1)
            
        # Initialize cache
        self.cache = LRUCache(maxsize=max_cache_size)
        
        # Server configuration
        self.host = host
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((self.host, self.port))
        self.debug = debug
        
        # Weather server configuration
        self.weather_server_ip = "127.0.0.1"  # Default to localhost
        
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
        print("\nCoordinates:")
        print(f"Latitude: {parsed['latitude']}")
        print(f"Longitude: {parsed['longitude']}")
        print("\nRaw Packet:")
        print(self._hex_dump(data))
        print("===========================\n")
        
    def _debug_print_response(self, response, region_code):
        """Print debug information for response packet"""
        if not self.debug:
            return
            
        print("\n=== SENDING RESPONSE PACKET ===")
        print(f"Total Length: {len(response)} bytes")
        print(f"Region Code: {region_code}")
        print(f"Weather Server IP: {self.weather_server_ip}")
        print("\nRaw Packet:")
        print(self._hex_dump(response))
        print("============================\n")

    def parse_request(self, data):
        """Parse incoming coordinate data"""
        if len(data) != 16:  # 128 bits = 16 bytes
            raise ValueError("Invalid request length")
            
        # Parse latitude and longitude (64 bits each)
        latitude = struct.unpack('!d', data[0:8])[0]
        longitude = struct.unpack('!d', data[8:16])[0]
        
        return {
            'latitude': latitude,
            'longitude': longitude
        }
        
    def get_district_code(self, longitude, latitude):
        """Query database for district code with caching"""
        # Create cache key
        cache_key = f"{longitude},{latitude}"
        
        # Check cache first
        if cache_key in self.cache:
            if self.debug:
                print("Cache hit!")
            return self.cache[cache_key]
            
        conn = None
        try:
            # Get connection from pool
            conn = self.connection_pool.getconn()
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

            district_code = result[0] if result else None
            
            # Store in cache
            self.cache[cache_key] = district_code
            
            return district_code

        except Exception as e:
            print(f"Database error: {e}")
            return None

        finally:
            if conn:
                # Return connection to pool
                cursor.close()
                self.connection_pool.putconn(conn)

    def create_response(self, region_code):
        """Create binary response packet"""
        if region_code is None:
            region_code = 0  # Default value for unknown regions
            
        # Convert region code to 4-byte integer
        region_bytes = struct.pack('!I', region_code)
        
        # Convert IP address to bytes (4 bytes)
        ip_parts = [int(part) for part in self.weather_server_ip.split('.')]
        ip_bytes = bytes(ip_parts)
        
        # Combine region code and IP address
        return region_bytes + ip_bytes
    
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
            'latitude': latitude
        }

    def run(self):
        """Start the location resolver server"""
        print(f"Location resolver running on {self.host}:{self.port}")
        
        while True:
            try:
                # Receive request
                data, addr = self.sock.recvfrom(1024)
                if self.debug:
                    print(f"Received request from {addr}")
                
                # Start measuring processing time
                start_time = time.time()
                
                # Parse request
                parse_start = time.time()
                request = self.parse_request(data)
                parse_time = time.time() - parse_start
                self._debug_print_request(data, request)
                
                # Get region code from database
                db_start = time.time()
                region_code = self.get_district_code(
                    request['longitude'],
                    request['latitude']
                )
                db_time = time.time() - db_start
                
                # Create response
                response_start = time.time()
                try:
                    response = self.create_response(int(region_code))
                except:
                    response = self.create_response(0)
                response_time = time.time() - response_start
                self._debug_print_response(response, region_code)
                
                # Send response and calculate total processing time
                send_start = time.time()
                self.sock.sendto(response, addr)
                send_time = time.time() - send_start
                
                total_processing_time = time.time() - start_time
                
                if self.debug:
                    print("\n=== TIMING INFORMATION ===")
                    print(f"Request parsing time: {parse_time*1000:.2f}ms")
                    print(f"Database query time: {db_time*1000:.2f}ms")
                    print(f"Response creation time: {response_time*1000:.2f}ms")
                    print(f"Response send time: {send_time*1000:.2f}ms")
                    print(f"Total processing time: {total_processing_time*1000:.2f}ms")
                    print("========================\n")
                    print(f"Sent response to {addr}")
                
            except Exception as e:
                print(f"Error processing request: {e}")
                continue

    def __del__(self):
        """Cleanup connection pool on deletion"""
        if hasattr(self, 'connection_pool'):
            self.connection_pool.closeall()

if __name__ == "__main__":
    server = LocationResolver(debug=False, max_cache_size=1000)
    server.run()

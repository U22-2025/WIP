#!/usr/bin/env python3
"""
Test if Python client can communicate with the query server
"""

import sys
import os
import socket

# Add the Python WIP library to the path
sys.path.insert(0, '/mnt/c/Users/pijon/Desktop/WIP/src')

from WIPCommonPy.packet.types.query_packet import QueryRequest

def test_python_client():
    """Test if Python client can communicate with query server"""
    try:
        # Create a QueryRequest identical to our Rust implementation
        request = QueryRequest.create_query_request(
            area_code=11000,
            packet_id=1,
            weather=True,
            temperature=False,
            precipitation_prob=False,
            alert=False,
            disaster=False,
            day=0,
            version=1
        )
        
        print("=== Testing Python client communication ===")
        packet_bytes = request.to_bytes()
        print(f"Sending packet: {packet_bytes.hex()}")
        
        # Create UDP socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(10)
        
        try:
            # Send to query server
            sock.sendto(packet_bytes, ('127.0.0.1', 4111))
            print("✅ Packet sent successfully")
            
            # Receive response
            response, addr = sock.recvfrom(1024)
            print(f"✅ Received response from {addr}: {response.hex()}")
            
            # Analyze response
            if len(response) >= 3:
                packet_type = response[2] & 0x07
                print(f"Response type: {packet_type} (3=QueryResponse, 7=Error)")
                
                if packet_type == 7 and len(response) >= 4:
                    error_code = response[3]
                    error_messages = {
                        1: "Invalid packet format",
                        2: "Checksum error", 
                        3: "Unsupported version",
                        4: "Unknown packet type",
                        5: "Missing required data",
                        6: "Server error",
                        7: "Timeout",
                    }
                    error_message = error_messages.get(error_code, "Unknown error")
                    print(f"❌ Error code: {error_code} = {error_message}")
                elif packet_type == 3:
                    print("✅ Received valid QueryResponse!")
                    if len(response) > 16:
                        extended_data = response[16:]
                        print(f"Extended data: {extended_data.hex()}")
            
        finally:
            sock.close()
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_python_client()
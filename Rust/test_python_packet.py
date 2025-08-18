#!/usr/bin/env python3
"""
Python script to generate the exact packet format that the server expects
"""

import sys
import os

# Add the Python WIP library to the path
sys.path.insert(0, '/mnt/c/Users/pijon/Desktop/WIP/src')

from WIPCommonPy.packet.types.query_packet import QueryRequest

def main():
    """Generate and analyze a QueryRequest packet"""
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
        
        print("=== Python QueryRequest packet analysis ===")
        print(f"Area code: {request.area_code}")
        print(f"Packet ID: {request.packet_id}")
        print(f"Version: {request.version}")
        print(f"Type: {request.type}")
        print(f"Weather flag: {request.weather_flag}")
        print(f"Temperature flag: {request.temperature_flag}")
        print(f"POP flag: {request.pop_flag}")
        print(f"Alert flag: {request.alert_flag}")
        print(f"Disaster flag: {request.disaster_flag}")
        print(f"Ex flag: {request.ex_flag}")
        print(f"Day: {request.day}")
        print(f"Timestamp: {request.timestamp}")
        
        # Convert to bytes
        packet_bytes = request.to_bytes()
        print(f"\nPacket bytes ({len(packet_bytes)} bytes): {[hex(b) for b in packet_bytes]}")
        print(f"Raw bytes: {packet_bytes.hex()}")
        
        # Analyze bit structure
        import struct
        if len(packet_bytes) >= 16:
            # First 16 bytes as little-endian analysis
            data = struct.unpack('<4I', packet_bytes[:16])
            print(f"\nAs 4 little-endian 32-bit integers: {[hex(x) for x in data]}")
            
            # Bit analysis
            full_bits = int.from_bytes(packet_bytes[:16], byteorder='little')
            print(f"\nFull 128-bit value: 0x{full_bits:032X}")
            
            # Extract fields manually
            version = full_bits & 0x0F
            packet_id = (full_bits >> 4) & 0x0FFF
            type_field = (full_bits >> 16) & 0x07
            weather_flag = (full_bits >> 19) & 0x01
            temperature_flag = (full_bits >> 20) & 0x01
            pop_flag = (full_bits >> 21) & 0x01
            alert_flag = (full_bits >> 22) & 0x01
            disaster_flag = (full_bits >> 23) & 0x01
            ex_flag = (full_bits >> 24) & 0x01
            day = (full_bits >> 27) & 0x07
            timestamp = (full_bits >> 32) & 0xFFFFFFFFFFFFFFFF
            area_code = (full_bits >> 96) & 0xFFFFF
            checksum = (full_bits >> 116) & 0x0FFF
            
            print(f"\nBit field extraction:")
            print(f"  version (bit 0-3): {version}")
            print(f"  packet_id (bit 4-15): {packet_id}")
            print(f"  type (bit 16-18): {type_field}")
            print(f"  weather_flag (bit 19): {weather_flag}")
            print(f"  temperature_flag (bit 20): {temperature_flag}")
            print(f"  pop_flag (bit 21): {pop_flag}")
            print(f"  alert_flag (bit 22): {alert_flag}")
            print(f"  disaster_flag (bit 23): {disaster_flag}")
            print(f"  ex_flag (bit 24): {ex_flag}")
            print(f"  day (bit 27-29): {day}")
            print(f"  timestamp (bit 32-95): {timestamp}")
            print(f"  area_code (bit 96-115): {area_code}")
            print(f"  checksum (bit 116-127): {checksum}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
import json
import requests
from datetime import datetime, timedelta

def get_data(area_code, debug=True):
    """Simplified version of the wind extraction logic"""
    url = f"https://www.jma.go.jp/bosai/forecast/data/forecast/{area_code}.json"
    response = requests.get(url)
    data = response.json()
    
    weather_areas = data[0]["timeSeries"][0]["areas"]
    time_defines = data[0]["timeSeries"][0]["timeDefines"]
    
    if debug:
        print(f"=== Processing area code {area_code} ===")
        print(f"Time defines: {time_defines}")
        print(f"Number of areas: {len(weather_areas)}")
    
    # Process each area
    for area in weather_areas:
        area_name = area.get("area", {}).get("name", "Unknown")
        code = area.get("area", {}).get("code", "Unknown")
        
        # Extract wind data (this is the key part)
        winds = area.get("winds", [])
        
        if debug:
            print(f"\nArea: {area_name} ({code})")
            print(f"Raw winds data: {winds}")
            print(f"Winds length: {len(winds)}")
        
        # Simulate the padding to 7 days (week_days = 7)
        week_days = 7
        if len(winds) < week_days:
            winds += [None] * (week_days - len(winds))
        
        winds = winds[:week_days]  # Ensure exactly 7 elements
        
        if debug:
            print(f"Final winds (padded to 7): {winds}")
        
        area_data = {
            "area_name": area_name,
            "wind": winds
        }
        
        print(f"✓ Area {area_name} wind data: {area_data['wind']}")

if __name__ == "__main__":
    # Test with Niigata (150000)
    get_data("150000", debug=True)
    
    print("\n" + "="*50)
    print("Testing other prefectures...")
    
    # Test a few other prefectures
    for code in ["130000", "270000"]:  # Tokyo, Osaka
        try:
            print(f"\n--- Testing {code} ---")
            get_data(code, debug=False)
        except Exception as e:
            print(f"Error processing {code}: {e}")
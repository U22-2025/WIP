#!/usr/bin/env python3
import json
import requests

# Fetch JMA data
url = "https://www.jma.go.jp/bosai/forecast/data/forecast/150000.json"
response = requests.get(url)
data = response.json()

print("=== JMA JSON Structure Analysis ===")
print(f"Total timeSeries entries: {len(data[0]['timeSeries'])}")

# Check first timeSeries (should contain winds)
first_ts = data[0]["timeSeries"][0]
print(f"\nFirst timeSeries keys: {first_ts.keys()}")
print(f"Number of areas in first timeSeries: {len(first_ts['areas'])}")

# Check each area for winds
for i, area in enumerate(first_ts["areas"]):
    area_code = area.get("area", {}).get("code", "unknown")
    area_name = area.get("area", {}).get("name", "unknown")
    winds = area.get("winds", [])
    print(f"\nArea {i}: {area_name} ({area_code})")
    print(f"  Winds: {winds}")
    print(f"  Area keys: {area.keys()}")

print(f"\nTime defines: {first_ts['timeDefines'][:3]}...")
# WIP フォーマット仕様

## Request Fields

| Name | Length/ID | Type |
|---|---:|---|
| version | 4 | int |
| packet_id | 12 | int |
| type | 3 | int |
| weather_flag | 1 | int |
| temperature_flag | 1 | int |
| pop_flag | 1 | int |
| alert_flag | 1 | int |
| disaster_flag | 1 | int |
| ex_flag | 1 | int |
| request_auth | 1 | int |
| response_auth | 1 | int |
| day | 3 | int |
| reserved | 2 | int |
| timestamp | 64 | int |
| area_code | 20 | str |
| checksum | 12 | int |

## Response Fields

| Name | Length/ID | Type |
|---|---:|---|
| version | 4 | int |
| packet_id | 12 | int |
| type | 3 | int |
| weather_flag | 1 | int |
| temperature_flag | 1 | int |
| pop_flag | 1 | int |
| alert_flag | 1 | int |
| disaster_flag | 1 | int |
| ex_flag | 1 | int |
| request_auth | 1 | int |
| response_auth | 1 | int |
| day | 3 | int |
| reserved | 2 | int |
| timestamp | 64 | int |
| area_code | 20 | str |
| checksum | 12 | int |
| weather_code | 16 | int |
| temperature | 8 | int |
| pop | 8 | int |

## Extended Fields

| Field | Length/ID | Type |
|---|---:|---|
| alert | 1 | str |
| disaster | 2 | str |
| latitude | 33 | float |
| longitude | 34 | float |
| source | 40 | str |
| auth_hash | 4 | str |

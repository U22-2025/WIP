```mermaid
graph TD
subgraph application_map_app_py["application/map/app.py"]
  application_map_app_py:get_address_from_coordinates["get_address_from_coordinates"]
  application_map_app_py:index["index"]
  application_map_app_py:weather_code["weather_code"]
  application_map_app_py:error_code_json["error_code_json"]
  application_map_app_py:click["click"]
  application_map_app_py:get_address["get_address"]
  application_map_app_py:weekly_forecast["weekly_forecast"]
  application_map_app_py:weekly_forecast_get_daily_weather_by_area_code["weekly_forecast.get_daily_weather_by_area_code"]
end
subgraph application_map_app_http3_py["application/map/app_http3.py"]
  application_map_app_http3_py:get_address_from_coordinates_cached["get_address_from_coordinates_cached"]
  application_map_app_http3_py:get_daily_weather["get_daily_weather"]
end
subgraph application_map_generate_cert_py["application/map/generate_cert.py"]
  application_map_generate_cert_py:generate_self_signed_cert["generate_self_signed_cert"]
  application_map_generate_cert_py:check_openssl["check_openssl"]
end
subgraph application_map_start_http3_server_py["application/map/start_http3_server.py"]
  application_map_start_http3_server_py:check_dependencies["check_dependencies"]
  application_map_start_http3_server_py:check_ssl_certificates["check_ssl_certificates"]
  application_map_start_http3_server_py:install_dependencies["install_dependencies"]
  application_map_start_http3_server_py:generate_certificates["generate_certificates"]
  application_map_start_http3_server_py:main["main"]
end
application_map_app_py:get_address --> application_map_app_py:get_address_from_coordinates
application_map_generate_cert_py:<module> --> application_map_generate_cert_py:check_openssl
application_map_generate_cert_py:<module> --> application_map_generate_cert_py:generate_self_signed_cert
application_map_start_http3_server_py:main --> application_map_start_http3_server_py:check_dependencies
application_map_start_http3_server_py:main --> application_map_start_http3_server_py:install_dependencies
application_map_start_http3_server_py:main --> application_map_start_http3_server_py:check_ssl_certificates
application_map_start_http3_server_py:main --> application_map_start_http3_server_py:generate_certificates
application_map_start_http3_server_py:<module> --> application_map_start_http3_server_py:main
```

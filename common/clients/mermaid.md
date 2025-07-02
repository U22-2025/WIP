```mermaid
graph TD
subgraph common_clients_utils["common/clients/utils"]
  subgraph common_clients_utils_packet_id_generator_py["common/clients/utils/packet_id_generator.py"]
    common_clients_utils_packet_id_generator_py:PacketIDGenerator12Bit___init__["PacketIDGenerator12Bit.__init__"]
    common_clients_utils_packet_id_generator_py:PacketIDGenerator12Bit_next_id["PacketIDGenerator12Bit.next_id"]
    common_clients_utils_packet_id_generator_py:PacketIDGenerator12Bit_next_id_bytes["PacketIDGenerator12Bit.next_id_bytes"]
  end
end
subgraph common_clients_location_client_py["common/clients/location_client.py"]
  common_clients_location_client_py:LocationClient___init__["LocationClient.__init__"]
  common_clients_location_client_py:LocationClient__hex_dump["LocationClient._hex_dump"]
  common_clients_location_client_py:LocationClient__debug_print_request["LocationClient._debug_print_request"]
  common_clients_location_client_py:LocationClient__debug_print_response["LocationClient._debug_print_response"]
  common_clients_location_client_py:LocationClient_get_location_info["LocationClient.get_location_info"]
  common_clients_location_client_py:LocationClient_get_area_code_from_coordinates["LocationClient.get_area_code_from_coordinates"]
  common_clients_location_client_py:LocationClient_close["LocationClient.close"]
  common_clients_location_client_py:main["main"]
end
subgraph common_clients_query_client_py["common/clients/query_client.py"]
  common_clients_query_client_py:QueryClient_close["QueryClient.close"]
  common_clients_query_client_py:QueryClient___init__["QueryClient.__init__"]
  common_clients_query_client_py:QueryClient__hex_dump["QueryClient._hex_dump"]
  common_clients_query_client_py:QueryClient__debug_print_request["QueryClient._debug_print_request"]
  common_clients_query_client_py:QueryClient__debug_print_response["QueryClient._debug_print_response"]
  common_clients_query_client_py:QueryClient_get_weather_data["QueryClient.get_weather_data"]
  common_clients_query_client_py:QueryClient_get_weather_data_simple["QueryClient.get_weather_data_simple"]
  common_clients_query_client_py:QueryClient_test_concurrent_requests["QueryClient.test_concurrent_requests"]
  common_clients_query_client_py:QueryClient_test_concurrent_requests_worker_thread["QueryClient.test_concurrent_requests.worker_thread"]
  common_clients_query_client_py:main["main"]
end
subgraph common_clients_weather_client_py["common/clients/weather_client.py"]
  common_clients_weather_client_py:WeatherClient___init__["WeatherClient.__init__"]
  common_clients_weather_client_py:WeatherClient__hex_dump["WeatherClient._hex_dump"]
  common_clients_weather_client_py:WeatherClient__debug_print_request["WeatherClient._debug_print_request"]
  common_clients_weather_client_py:WeatherClient__debug_print_response["WeatherClient._debug_print_response"]
  common_clients_weather_client_py:WeatherClient_get_weather_by_coordinates["WeatherClient.get_weather_by_coordinates"]
  common_clients_weather_client_py:WeatherClient_get_weather_by_area_code["WeatherClient.get_weather_by_area_code"]
  common_clients_weather_client_py:WeatherClient_close["WeatherClient.close"]
  common_clients_weather_client_py:main["main"]
end
common_clients_location_client_py:<module> --> common_clients_weather_client_py:main
common_clients_query_client_py:<module> --> common_clients_weather_client_py:main
common_clients_weather_client_py:<module> --> common_clients_weather_client_py:main
```

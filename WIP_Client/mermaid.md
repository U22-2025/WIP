```mermaid
graph TD
subgraph WIP_Client_client_py["WIP_Client/client.py"]
  WIP_Client_client_py:Client___init__["Client.__init__"]
  WIP_Client_client_py:Client_latitude["Client.latitude"]
  WIP_Client_client_py:Client_longitude["Client.longitude"]
  WIP_Client_client_py:Client_area_code["Client.area_code"]
  WIP_Client_client_py:Client_set_coordinates["Client.set_coordinates"]
  WIP_Client_client_py:Client_get_weather["Client.get_weather"]
  WIP_Client_client_py:Client_get_weather_by_coordinates["Client.get_weather_by_coordinates"]
  WIP_Client_client_py:Client_get_weather_by_area_code["Client.get_weather_by_area_code"]
  WIP_Client_client_py:Client_get_state["Client.get_state"]
  WIP_Client_client_py:Client_set_server["Client.set_server"]
  WIP_Client_client_py:Client_close["Client.close"]
  WIP_Client_client_py:main["main"]
end
WIP_Client_client_py:<module> --> WIP_Client_client_py:main
```

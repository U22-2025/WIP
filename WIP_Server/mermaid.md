```mermaid
graph TD
subgraph WIP_Server_data["WIP_Server/data"]
  subgraph WIP_Server_data_create_area_codes_json_py["WIP_Server/data/create_area_codes_json.py"]
    WIP_Server_data_create_area_codes_json_py:fetch_json_from_url["fetch_json_from_url"]
    WIP_Server_data_create_area_codes_json_py:_map_office_code["_map_office_code"]
    WIP_Server_data_create_area_codes_json_py:_process_area_code["_process_area_code"]
    WIP_Server_data_create_area_codes_json_py:map_area_code_to_children["map_area_code_to_children"]
    WIP_Server_data_create_area_codes_json_py:generate_area_codes_file["generate_area_codes_file"]
    WIP_Server_data_create_area_codes_json_py:main["main"]
  end
  subgraph WIP_Server_data_get_disaster_py["WIP_Server/data/get_disaster.py"]
    WIP_Server_data_get_disaster_py:main["main"]
  end
  subgraph WIP_Server_data_xml_base_py["WIP_Server/data/xml_base.py"]
    WIP_Server_data_xml_base_py:XMLBaseProcessor___init__["XMLBaseProcessor.__init__"]
    WIP_Server_data_xml_base_py:XMLBaseProcessor_fetch_xml["XMLBaseProcessor.fetch_xml"]
    WIP_Server_data_xml_base_py:XMLBaseProcessor_parse_xml["XMLBaseProcessor.parse_xml"]
    WIP_Server_data_xml_base_py:XMLBaseProcessor_get_report_time["XMLBaseProcessor.get_report_time"]
    WIP_Server_data_xml_base_py:XMLBaseProcessor_save_json["XMLBaseProcessor.save_json"]
    WIP_Server_data_xml_base_py:XMLBaseProcessor_get_feed_entry_urls["XMLBaseProcessor.get_feed_entry_urls"]
    WIP_Server_data_xml_base_py:XMLBaseProcessor_process_xml_data["XMLBaseProcessor.process_xml_data"]
    WIP_Server_data_xml_base_py:XMLBaseProcessor_process_multiple_urls["XMLBaseProcessor.process_multiple_urls"]
    WIP_Server_data_xml_base_py:XMLBaseProcessor__process_single_url_base["XMLBaseProcessor._process_single_url_base"]
  end
  subgraph WIP_Server_data_redis_manager_py["WIP_Server/data/redis_manager.py"]
    WIP_Server_data_redis_manager_py:RedisConfig_from_env["RedisConfig.from_env"]
    WIP_Server_data_redis_manager_py:WeatherRedisManager___init__["WeatherRedisManager.__init__"]
    WIP_Server_data_redis_manager_py:WeatherRedisManager__connect["WeatherRedisManager._connect"]
    WIP_Server_data_redis_manager_py:WeatherRedisManager__get_weather_key["WeatherRedisManager._get_weather_key"]
    WIP_Server_data_redis_manager_py:WeatherRedisManager__create_default_weather_data["WeatherRedisManager._create_default_weather_data"]
    WIP_Server_data_redis_manager_py:WeatherRedisManager_get_weather_data["WeatherRedisManager.get_weather_data"]
    WIP_Server_data_redis_manager_py:WeatherRedisManager_update_weather_data["WeatherRedisManager.update_weather_data"]
    WIP_Server_data_redis_manager_py:WeatherRedisManager_update_alerts["WeatherRedisManager.update_alerts"]
    WIP_Server_data_redis_manager_py:WeatherRedisManager_update_disasters["WeatherRedisManager.update_disasters"]
    WIP_Server_data_redis_manager_py:WeatherRedisManager_bulk_update_weather_data["WeatherRedisManager.bulk_update_weather_data"]
    WIP_Server_data_redis_manager_py:WeatherRedisManager_close["WeatherRedisManager.close"]
    WIP_Server_data_redis_manager_py:create_redis_manager["create_redis_manager"]
  end
  subgraph WIP_Server_data_disaster_processor_py["WIP_Server/data/disaster_processor.py"]
    WIP_Server_data_disaster_processor_py:DisasterProcessor_process_xml_data["DisasterProcessor.process_xml_data"]
    WIP_Server_data_disaster_processor_py:DisasterProcessor_extract_kind_and_code["DisasterProcessor.extract_kind_and_code"]
    WIP_Server_data_disaster_processor_py:DisasterProcessor_extract_volcano_coordinates["DisasterProcessor.extract_volcano_coordinates"]
    WIP_Server_data_disaster_processor_py:DisasterProcessor__process_information_items["DisasterProcessor._process_information_items"]
    WIP_Server_data_disaster_processor_py:DisasterProcessor__process_volcano_info_items["DisasterProcessor._process_volcano_info_items"]
    WIP_Server_data_disaster_processor_py:DisasterProcessor__process_ash_info_items["DisasterProcessor._process_ash_info_items"]
    WIP_Server_data_disaster_processor_py:DisasterProcessor__process_single_url["DisasterProcessor._process_single_url"]
    WIP_Server_data_disaster_processor_py:DisasterProcessor_process_multiple_urls["DisasterProcessor.process_multiple_urls"]
    WIP_Server_data_disaster_processor_py:DisasterDataProcessor___init__["DisasterDataProcessor.__init__"]
    WIP_Server_data_disaster_processor_py:DisasterDataProcessor_get_disaster_xml_list["DisasterDataProcessor.get_disaster_xml_list"]
    WIP_Server_data_disaster_processor_py:DisasterDataProcessor_get_disaster_info["DisasterDataProcessor.get_disaster_info"]
    WIP_Server_data_disaster_processor_py:DisasterDataProcessor_convert_disaster_keys_to_area_codes["DisasterDataProcessor.convert_disaster_keys_to_area_codes"]
    WIP_Server_data_disaster_processor_py:DisasterDataProcessor_format_to_alert_style["DisasterDataProcessor.format_to_alert_style"]
    WIP_Server_data_disaster_processor_py:DisasterDataProcessor_resolve_volcano_coordinates["DisasterDataProcessor.resolve_volcano_coordinates"]
    WIP_Server_data_disaster_processor_py:TimeProcessor_parse_time_from_kind_name["TimeProcessor.parse_time_from_kind_name"]
    WIP_Server_data_disaster_processor_py:TimeProcessor_create_time_range["TimeProcessor.create_time_range"]
    WIP_Server_data_disaster_processor_py:TimeProcessor_consolidate_time_ranges["TimeProcessor.consolidate_time_ranges"]
    WIP_Server_data_disaster_processor_py:AreaCodeValidator_is_valid_area_code["AreaCodeValidator.is_valid_area_code"]
    WIP_Server_data_disaster_processor_py:AreaCodeValidator_find_area_code_mapping["AreaCodeValidator.find_area_code_mapping"]
    WIP_Server_data_disaster_processor_py:VolcanoCoordinateProcessor_parse_volcano_coordinates["VolcanoCoordinateProcessor.parse_volcano_coordinates"]
    WIP_Server_data_disaster_processor_py:main["main"]
  end
  subgraph WIP_Server_data_get_alert_py["WIP_Server/data/get_alert.py"]
    WIP_Server_data_get_alert_py:main["main"]
  end
  subgraph WIP_Server_data_alert_processor_py["WIP_Server/data/alert_processor.py"]
    WIP_Server_data_alert_processor_py:AlertProcessor___init__["AlertProcessor.__init__"]
    WIP_Server_data_alert_processor_py:AlertProcessor_process_xml_data["AlertProcessor.process_xml_data"]
    WIP_Server_data_alert_processor_py:AlertProcessor__extract_alert_kinds["AlertProcessor._extract_alert_kinds"]
    WIP_Server_data_alert_processor_py:AlertProcessor__extract_area_codes["AlertProcessor._extract_area_codes"]
    WIP_Server_data_alert_processor_py:AlertProcessor__process_single_url["AlertProcessor._process_single_url"]
    WIP_Server_data_alert_processor_py:AlertProcessor_process_multiple_urls["AlertProcessor.process_multiple_urls"]
    WIP_Server_data_alert_processor_py:AlertProcessor_get_alert_xml_list["AlertProcessor.get_alert_xml_list"]
    WIP_Server_data_alert_processor_py:AlertDataProcessor___init__["AlertDataProcessor.__init__"]
    WIP_Server_data_alert_processor_py:AlertDataProcessor_get_alert_info["AlertDataProcessor.get_alert_info"]
    WIP_Server_data_alert_processor_py:main["main"]
  end
  subgraph WIP_Server_data_get_codes_py["WIP_Server/data/get_codes.py"]
    WIP_Server_data_get_codes_py:fetch_json_from_file["fetch_json_from_file"]
    WIP_Server_data_get_codes_py:get_office_codes["get_office_codes"]
    WIP_Server_data_get_codes_py:get_area_codes["get_area_codes"]
    WIP_Server_data_get_codes_py:find_area_key_by_children_code["find_area_key_by_children_code"]
  end
  subgraph WIP_Server_data_xml2dict_py["WIP_Server/data/xml2dict.py"]
    WIP_Server_data_xml2dict_py:etree_to_dict["etree_to_dict"]
  end
end
subgraph WIP_Server_scripts["WIP_Server/scripts"]
  subgraph WIP_Server_scripts_update_weather_data_py["WIP_Server/scripts/update_weather_data.py"]
    WIP_Server_scripts_update_weather_data_py:get_data["get_data"]
    WIP_Server_scripts_update_weather_data_py:get_data_fetch_and_process_area["get_data.fetch_and_process_area"]
    WIP_Server_scripts_update_weather_data_py:update_redis_weather_data["update_redis_weather_data"]
  end
  subgraph WIP_Server_scripts_update_alert_disaster_data_py["WIP_Server/scripts/update_alert_disaster_data.py"]
    WIP_Server_scripts_update_alert_disaster_data_py:main["main"]
  end
end
subgraph WIP_Server_servers["WIP_Server/servers"]
  subgraph WIP_Server_servers_location_server["WIP_Server/servers/location_server"]
    subgraph WIP_Server_servers_location_server_location_server_py["WIP_Server/servers/location_server/location_server.py"]
      WIP_Server_servers_location_server_location_server_py:LocationServer___init__["LocationServer.__init__"]
      WIP_Server_servers_location_server_location_server_py:LocationServer__init_database["LocationServer._init_database"]
      WIP_Server_servers_location_server_location_server_py:LocationServer__init_cache["LocationServer._init_cache"]
      WIP_Server_servers_location_server_location_server_py:LocationServer_parse_request["LocationServer.parse_request"]
      WIP_Server_servers_location_server_location_server_py:LocationServer_handle_request["LocationServer.handle_request"]
      WIP_Server_servers_location_server_location_server_py:LocationServer_validate_request["LocationServer.validate_request"]
      WIP_Server_servers_location_server_location_server_py:LocationServer_create_response["LocationServer.create_response"]
      WIP_Server_servers_location_server_location_server_py:LocationServer_get_district_code["LocationServer.get_district_code"]
      WIP_Server_servers_location_server_location_server_py:LocationServer__debug_print_request["LocationServer._debug_print_request"]
      WIP_Server_servers_location_server_location_server_py:LocationServer__debug_print_response["LocationServer._debug_print_response"]
      WIP_Server_servers_location_server_location_server_py:LocationServer__print_timing_info["LocationServer._print_timing_info"]
      WIP_Server_servers_location_server_location_server_py:LocationServer_print_statistics["LocationServer.print_statistics"]
      WIP_Server_servers_location_server_location_server_py:LocationServer__cleanup["LocationServer._cleanup"]
    end
  end
  subgraph WIP_Server_servers_query_server["WIP_Server/servers/query_server"]
    subgraph WIP_Server_servers_query_server_modules["WIP_Server/servers/query_server/modules"]
      subgraph WIP_Server_servers_query_server_modules_weather_data_manager_py["WIP_Server/servers/query_server/modules/weather_data_manager.py"]
        WIP_Server_servers_query_server_modules_weather_data_manager_py:WeatherDataManager___init__["WeatherDataManager.__init__"]
        WIP_Server_servers_query_server_modules_weather_data_manager_py:WeatherDataManager__init_redis["WeatherDataManager._init_redis"]
        WIP_Server_servers_query_server_modules_weather_data_manager_py:WeatherDataManager_get_weather_data["WeatherDataManager.get_weather_data"]
        WIP_Server_servers_query_server_modules_weather_data_manager_py:WeatherDataManager_check_update_time["WeatherDataManager.check_update_time"]
        WIP_Server_servers_query_server_modules_weather_data_manager_py:WeatherDataManager_save_weather_data["WeatherDataManager.save_weather_data"]
        WIP_Server_servers_query_server_modules_weather_data_manager_py:WeatherDataManager__generate_cache_key["WeatherDataManager._generate_cache_key"]
        WIP_Server_servers_query_server_modules_weather_data_manager_py:WeatherDataManager__get_from_cache["WeatherDataManager._get_from_cache"]
        WIP_Server_servers_query_server_modules_weather_data_manager_py:WeatherDataManager__save_to_cache["WeatherDataManager._save_to_cache"]
        WIP_Server_servers_query_server_modules_weather_data_manager_py:WeatherDataManager_close["WeatherDataManager.close"]
      end
      subgraph WIP_Server_servers_query_server_modules_debug_helper_py["WIP_Server/servers/query_server/modules/debug_helper.py"]
        WIP_Server_servers_query_server_modules_debug_helper_py:DebugHelper___init__["DebugHelper.__init__"]
        WIP_Server_servers_query_server_modules_debug_helper_py:DebugHelper__hex_dump["DebugHelper._hex_dump"]
        WIP_Server_servers_query_server_modules_debug_helper_py:DebugHelper_print_request_debug["DebugHelper.print_request_debug"]
        WIP_Server_servers_query_server_modules_debug_helper_py:DebugHelper_print_response_debug["DebugHelper.print_response_debug"]
        WIP_Server_servers_query_server_modules_debug_helper_py:DebugHelper_print_timing_info["DebugHelper.print_timing_info"]
        WIP_Server_servers_query_server_modules_debug_helper_py:DebugHelper_print_thread_info["DebugHelper.print_thread_info"]
        WIP_Server_servers_query_server_modules_debug_helper_py:DebugHelper_print_error["DebugHelper.print_error"]
        WIP_Server_servers_query_server_modules_debug_helper_py:DebugHelper_print_info["DebugHelper.print_info"]
        WIP_Server_servers_query_server_modules_debug_helper_py:PerformanceTimer___init__["PerformanceTimer.__init__"]
        WIP_Server_servers_query_server_modules_debug_helper_py:PerformanceTimer_start["PerformanceTimer.start"]
        WIP_Server_servers_query_server_modules_debug_helper_py:PerformanceTimer_mark["PerformanceTimer.mark"]
        WIP_Server_servers_query_server_modules_debug_helper_py:PerformanceTimer_get_timing["PerformanceTimer.get_timing"]
        WIP_Server_servers_query_server_modules_debug_helper_py:PerformanceTimer_get_all_timings["PerformanceTimer.get_all_timings"]
        WIP_Server_servers_query_server_modules_debug_helper_py:PerformanceTimer_reset["PerformanceTimer.reset"]
      end
      subgraph WIP_Server_servers_query_server_modules_response_builder_py["WIP_Server/servers/query_server/modules/response_builder.py"]
        WIP_Server_servers_query_server_modules_response_builder_py:ResponseBuilder___init__["ResponseBuilder.__init__"]
        WIP_Server_servers_query_server_modules_response_builder_py:ResponseBuilder_build_response["ResponseBuilder.build_response"]
        WIP_Server_servers_query_server_modules_response_builder_py:ResponseBuilder__set_weather_data["ResponseBuilder._set_weather_data"]
        WIP_Server_servers_query_server_modules_response_builder_py:ResponseBuilder__set_extended_fields["ResponseBuilder._set_extended_fields"]
        WIP_Server_servers_query_server_modules_response_builder_py:ResponseBuilder_build_error_response["ResponseBuilder.build_error_response"]
      end
      subgraph WIP_Server_servers_query_server_modules_config_manager_py["WIP_Server/servers/query_server/modules/config_manager.py"]
        WIP_Server_servers_query_server_modules_config_manager_py:ConfigManager___init__["ConfigManager.__init__"]
        WIP_Server_servers_query_server_modules_config_manager_py:ConfigManager__load_config["ConfigManager._load_config"]
        WIP_Server_servers_query_server_modules_config_manager_py:ConfigManager_get_redis_pool_config["ConfigManager.get_redis_pool_config"]
        WIP_Server_servers_query_server_modules_config_manager_py:ConfigManager_validate_config["ConfigManager.validate_config"]
        WIP_Server_servers_query_server_modules_config_manager_py:ConfigManager___str__["ConfigManager.__str__"]
      end
    end
    subgraph WIP_Server_servers_query_server_query_server_py["WIP_Server/servers/query_server/query_server.py"]
      WIP_Server_servers_query_server_query_server_py:QueryServer___init__["QueryServer.__init__"]
      WIP_Server_servers_query_server_query_server_py:QueryServer__init_components["QueryServer._init_components"]
      WIP_Server_servers_query_server_query_server_py:QueryServer_parse_request["QueryServer.parse_request"]
      WIP_Server_servers_query_server_query_server_py:QueryServer_validate_request["QueryServer.validate_request"]
      WIP_Server_servers_query_server_query_server_py:QueryServer_create_response["QueryServer.create_response"]
      WIP_Server_servers_query_server_query_server_py:QueryServer__debug_print_request["QueryServer._debug_print_request"]
      WIP_Server_servers_query_server_query_server_py:QueryServer__debug_print_response["QueryServer._debug_print_response"]
      WIP_Server_servers_query_server_query_server_py:QueryServer__cleanup["QueryServer._cleanup"]
      WIP_Server_servers_query_server_query_server_py:QueryServer__start_weather_update_scheduler["QueryServer._start_weather_update_scheduler"]
      WIP_Server_servers_query_server_query_server_py:QueryServer__start_weather_update_scheduler_run_scheduler["QueryServer._start_weather_update_scheduler.run_scheduler"]
      WIP_Server_servers_query_server_query_server_py:QueryServer_update_weather_data_scheduled["QueryServer.update_weather_data_scheduled"]
      WIP_Server_servers_query_server_query_server_py:QueryServer_check_and_update_skip_area_scheduled["QueryServer.check_and_update_skip_area_scheduled"]
    end
  end
  subgraph WIP_Server_servers_weather_server["WIP_Server/servers/weather_server"]
    subgraph WIP_Server_servers_weather_server_weather_server_py["WIP_Server/servers/weather_server/weather_server.py"]
      WIP_Server_servers_weather_server_weather_server_py:WeatherServer___init__["WeatherServer.__init__"]
      WIP_Server_servers_weather_server_weather_server_py:WeatherServer_handle_request["WeatherServer.handle_request"]
      WIP_Server_servers_weather_server_weather_server_py:WeatherServer__handle_location_request["WeatherServer._handle_location_request"]
      WIP_Server_servers_weather_server_weather_server_py:WeatherServer__validate_cache_data["WeatherServer._validate_cache_data"]
      WIP_Server_servers_weather_server_weather_server_py:WeatherServer__create_response_from_cache["WeatherServer._create_response_from_cache"]
      WIP_Server_servers_weather_server_weather_server_py:WeatherServer__handle_location_response["WeatherServer._handle_location_response"]
      WIP_Server_servers_weather_server_weather_server_py:WeatherServer__handle_weather_request["WeatherServer._handle_weather_request"]
      WIP_Server_servers_weather_server_weather_server_py:WeatherServer__send_weather_request["WeatherServer._send_weather_request"]
      WIP_Server_servers_weather_server_weather_server_py:WeatherServer__handle_weather_response["WeatherServer._handle_weather_response"]
      WIP_Server_servers_weather_server_weather_server_py:WeatherServer__handle_error_packet["WeatherServer._handle_error_packet"]
      WIP_Server_servers_weather_server_weather_server_py:WeatherServer_create_response["WeatherServer.create_response"]
      WIP_Server_servers_weather_server_weather_server_py:WeatherServer_parse_request["WeatherServer.parse_request"]
      WIP_Server_servers_weather_server_weather_server_py:WeatherServer_validate_request["WeatherServer.validate_request"]
      WIP_Server_servers_weather_server_weather_server_py:WeatherServer__debug_print_request["WeatherServer._debug_print_request"]
      WIP_Server_servers_weather_server_weather_server_py:WeatherServer__cleanup["WeatherServer._cleanup"]
    end
  end
  subgraph WIP_Server_servers_base_server_py["WIP_Server/servers/base_server.py"]
    WIP_Server_servers_base_server_py:BaseServer___init__["BaseServer.__init__"]
    WIP_Server_servers_base_server_py:BaseServer__init_thread_pool["BaseServer._init_thread_pool"]
    WIP_Server_servers_base_server_py:BaseServer__init_socket["BaseServer._init_socket"]
    WIP_Server_servers_base_server_py:BaseServer__hex_dump["BaseServer._hex_dump"]
    WIP_Server_servers_base_server_py:BaseServer__debug_print["BaseServer._debug_print"]
    WIP_Server_servers_base_server_py:BaseServer__debug_print_request["BaseServer._debug_print_request"]
    WIP_Server_servers_base_server_py:BaseServer__debug_print_response["BaseServer._debug_print_response"]
    WIP_Server_servers_base_server_py:BaseServer__measure_time["BaseServer._measure_time"]
    WIP_Server_servers_base_server_py:BaseServer_parse_request["BaseServer.parse_request"]
    WIP_Server_servers_base_server_py:BaseServer_create_response["BaseServer.create_response"]
    WIP_Server_servers_base_server_py:BaseServer_validate_request["BaseServer.validate_request"]
    WIP_Server_servers_base_server_py:BaseServer__handle_error["BaseServer._handle_error"]
    WIP_Server_servers_base_server_py:BaseServer_handle_request["BaseServer.handle_request"]
    WIP_Server_servers_base_server_py:BaseServer__print_timing_info["BaseServer._print_timing_info"]
    WIP_Server_servers_base_server_py:BaseServer_print_statistics["BaseServer.print_statistics"]
    WIP_Server_servers_base_server_py:BaseServer_send_udp_packet["BaseServer.send_udp_packet"]
    WIP_Server_servers_base_server_py:BaseServer_run["BaseServer.run"]
    WIP_Server_servers_base_server_py:BaseServer_shutdown["BaseServer.shutdown"]
    WIP_Server_servers_base_server_py:BaseServer__cleanup["BaseServer._cleanup"]
  end
end
subgraph WIP_Server___init___py["WIP_Server/__init__.py"]
  WIP_Server___init___py:__getattr__["__getattr__"]
end
WIP_Server_data_create_area_codes_json_py:map_area_code_to_children --> WIP_Server_data_create_area_codes_json_py:_map_office_code
WIP_Server_data_create_area_codes_json_py:map_area_code_to_children --> WIP_Server_data_create_area_codes_json_py:_process_area_code
WIP_Server_data_create_area_codes_json_py:generate_area_codes_file --> WIP_Server_data_create_area_codes_json_py:fetch_json_from_url
WIP_Server_data_create_area_codes_json_py:generate_area_codes_file --> WIP_Server_data_create_area_codes_json_py:map_area_code_to_children
WIP_Server_data_create_area_codes_json_py:main --> WIP_Server_data_create_area_codes_json_py:generate_area_codes_file
WIP_Server_data_create_area_codes_json_py:<module> --> WIP_Server_scripts_update_alert_disaster_data_py:main
WIP_Server_data_get_disaster_py:<module> --> WIP_Server_scripts_update_alert_disaster_data_py:main
WIP_Server_data_get_disaster_py:main --> WIP_Server_data_redis_manager_py:create_redis_manager
WIP_Server_data_disaster_processor_py:<module> --> WIP_Server_scripts_update_alert_disaster_data_py:main
WIP_Server_data_get_alert_py:<module> --> WIP_Server_scripts_update_alert_disaster_data_py:main
WIP_Server_data_get_alert_py:main --> WIP_Server_data_redis_manager_py:create_redis_manager
WIP_Server_data_alert_processor_py:<module> --> WIP_Server_scripts_update_alert_disaster_data_py:main
WIP_Server_data_get_codes_py:get_office_codes --> WIP_Server_data_get_codes_py:fetch_json_from_file
WIP_Server_data_get_codes_py:get_area_codes --> WIP_Server_data_get_codes_py:fetch_json_from_file
WIP_Server_data_get_codes_py:find_area_key_by_children_code --> WIP_Server_data_get_codes_py:fetch_json_from_file
WIP_Server_data_xml2dict_py:<module> --> WIP_Server_data_xml2dict_py:etree_to_dict
WIP_Server_servers_query_server_query_server_py:QueryServer_update_weather_data_scheduled --> WIP_Server_scripts_update_weather_data_py:update_redis_weather_data
WIP_Server_servers_query_server_query_server_py:QueryServer_check_and_update_skip_area_scheduled --> WIP_Server_scripts_update_weather_data_py:update_redis_weather_data
WIP_Server_servers_query_server_modules_weather_data_manager_py:WeatherDataManager_get_weather_data --> WIP_Server_scripts_update_alert_disaster_data_py:main
WIP_Server_servers_query_server_modules_weather_data_manager_py:WeatherDataManager_get_weather_data --> WIP_Server_scripts_update_alert_disaster_data_py:main
WIP_Server_scripts_update_weather_data_py:<module> --> WIP_Server_scripts_update_weather_data_py:get_data
WIP_Server_scripts_update_weather_data_py:get_data --> WIP_Server_data_redis_manager_py:create_redis_manager
WIP_Server_scripts_update_weather_data_py:update_redis_weather_data --> WIP_Server_scripts_update_weather_data_py:get_data
WIP_Server_scripts_update_alert_disaster_data_py:<module> --> WIP_Server_scripts_update_alert_disaster_data_py:main
WIP_Server_scripts_update_alert_disaster_data_py:main --> WIP_Server_scripts_update_alert_disaster_data_py:main
WIP_Server_scripts_update_alert_disaster_data_py:main --> WIP_Server_scripts_update_alert_disaster_data_py:main
```

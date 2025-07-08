import unittest
from unittest import mock

from common.clients.location_client import LocationClient
from common.clients.query_client import QueryClient
from common.clients.weather_client import WeatherClient
from common.clients.report_client import ReportClient

class TestClientCompatibility(unittest.TestCase):
    def test_location_alias(self):
        client = LocationClient(host='localhost', port=0)
        with mock.patch.object(client, 'get_location_data', return_value=('ok', 0)) as m:
            self.assertEqual(client.get_location_info(1, 2), ('ok', 0))
            m.assert_called_once_with(1, 2, source=None)
        with mock.patch.object(client, 'get_area_code_simple', return_value='AC') as m:
            self.assertEqual(client.get_area_code_from_coordinates(1, 2), 'AC')
            m.assert_called_once_with(1, 2, None)
        client.close()

    def test_query_alias(self):
        client = QueryClient(host='localhost', port=0)
        with mock.patch.object(client, 'get_weather_simple', return_value={'ok': True}) as m:
            self.assertEqual(client.get_weather_data_simple('001'), {'ok': True})
            m.assert_called_once_with('001', False, 5.0)

    def test_weather_alias(self):
        client = WeatherClient(host='localhost', port=0)
        with mock.patch.object(client, 'get_weather_data', return_value={'w':1}) as m:
            self.assertEqual(client.get_weather_by_area_code('001'), {'w':1})
            m.assert_called_once_with('001', True, True, True, False, False, 0)
        client.close()

    def test_report_alias(self):
        client = ReportClient(host='localhost', port=0)
        with mock.patch.object(client, 'send_report_data', return_value={'r':1}) as m:
            self.assertEqual(client.send_report(), {'r':1})
            m.assert_called_once()
        with mock.patch.object(client, 'send_data_simple', return_value={'r':2}) as m:
            self.assertEqual(client.send_current_data(), {'r':2})
            m.assert_called_once()
        client.close()

if __name__ == '__main__':
    unittest.main()

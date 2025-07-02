import unittest
from common.packet.weather_packet import WeatherRequest, WeatherResponse
from common.packet.location_packet import LocationRequest, LocationResponse
from common.packet.query_packet import QueryRequest, QueryResponse

class TestWeatherPacket(unittest.TestCase):
    def test_request_and_restore(self):
        req = WeatherRequest.create_by_coordinates(
            latitude=35.6895,
            longitude=139.6917,
            packet_id=123,
            weather=True,
            temperature=True,
            precipitation_prob=True
        )
        data = req.to_bytes()
        restored = WeatherRequest.from_bytes(data)
        self.assertEqual(restored.type, req.type)
        self.assertAlmostEqual(restored.ex_field.latitude, 35.6895)
        self.assertAlmostEqual(restored.ex_field.longitude, 139.6917)

class TestLocationPacket(unittest.TestCase):
    def test_create_and_response(self):
        req = LocationRequest.create_coordinate_lookup(
            latitude=35.0,
            longitude=135.0,
            packet_id=1,
            source=("1.1.1.1", 1000)
        )
        resp = LocationResponse.create_area_code_response(request=req, area_code="100000")
        self.assertEqual(resp.get_area_code(), "100000")
        self.assertTrue(resp.is_valid())

    def test_source_preserved_roundtrip(self):
        req = LocationRequest.create_coordinate_lookup(
            latitude=10.0,
            longitude=20.0,
            packet_id=5,
            source=("8.8.8.8", 8080),
        )
        data = req.to_bytes()
        restored = LocationRequest.from_bytes(data)
        self.assertEqual(restored.ex_field.source, ("8.8.8.8", 8080))

class TestQueryPacket(unittest.TestCase):
    def test_weather_data_response(self):
        req = QueryRequest.create_weather_data_request(
            area_code="011000",
            packet_id=2,
            weather=True,
            temperature=True
        )
        weather_data = {
            'weather': 100,
            'temperature': 25,
        }
        resp = QueryResponse.create_weather_data_response(request=req, weather_data=weather_data)
        self.assertEqual(resp.get_weather_code(), 100)
        self.assertEqual(resp.get_temperature_celsius(), 25)

    def test_query_request_with_source_roundtrip(self):
        req = QueryRequest.create_weather_data_request(
            area_code="022000",
            packet_id=3,
            weather=True,
            temperature=False,
            source=("1.2.3.4", 1234),
        )
        data = req.to_bytes()
        restored = QueryRequest.from_bytes(data)
        self.assertEqual(restored.ex_field.source, ("1.2.3.4", 1234))

    def test_query_response_preserves_source(self):
        req = QueryRequest.create_weather_data_request(
            area_code="022000",
            packet_id=4,
            weather=True,
            temperature=False,
            source=("9.9.9.9", 9000),
        )
        weather_data = {"weather": 300}
        resp = QueryResponse.create_weather_data_response(request=req, weather_data=weather_data)
        data = resp.to_bytes()
        restored = QueryResponse.from_bytes(data)
        self.assertEqual(restored.ex_field.source, ("9.9.9.9", 9000))

if __name__ == '__main__':
    unittest.main()

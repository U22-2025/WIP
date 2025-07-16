from fastapi.testclient import TestClient

from application.map.fastapi_app import (
    app,
    get_location_client,
    get_query_client,
)

class DummyLocationClient:
    async def get_location_data_async(self, latitude, longitude, use_cache=True):
        class Resp:
            def is_valid(self_inner):
                return True

            def get_area_code(self_inner):
                return "0000"

        return Resp(), 0.0

    def close(self):
        pass


class DummyQueryClient:
    async def get_weather_data_async(self, area_code, **kwargs):
        day = kwargs.get("day", 0)
        return {
            "weather_code": "100",
            "temperature": str(20 + day),
            "precipitation_prob": "0",
            "area_code": area_code,
        }

    def close(self):
        pass


def override_get_location_client():
    client = DummyLocationClient()
    try:
        yield client
    finally:
        client.close()


def override_get_query_client():
    client = DummyQueryClient()
    try:
        yield client
    finally:
        client.close()


app.dependency_overrides[get_location_client] = override_get_location_client
app.dependency_overrides[get_query_client] = override_get_query_client

client = TestClient(app)

def test_weekly_forecast_success():
    response = client.post("/weekly_forecast", json={"lat": 35.0, "lng": 139.0})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["area_code"] == "0000"
    assert len(data["weekly_forecast"]) == 7
    days = [item["day"] for item in data["weekly_forecast"]]
    assert days == sorted(days)

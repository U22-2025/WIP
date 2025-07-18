from fastapi.testclient import TestClient

from application.map.fastapi_app import (
    app,
    get_wip_client,
)

class DummyWIPClient:
    async def get_weather_by_coordinates(self, latitude, longitude, **kwargs):
        day = kwargs.get("day", 0)
        return {
            "weather_code": "100",
            "temperature": str(20 + day),
            "precipitation_prob": "0",
            "area_code": "0000",
        }

    async def get_weather_by_area_code(self, area_code, **kwargs):
        day = kwargs.get("day", 0)
        return {
            "weather_code": "100",
            "temperature": str(20 + day),
            "precipitation_prob": "0",
            "area_code": area_code,
        }

    def close(self):
        pass


def override_get_wip_client():
    client = DummyWIPClient()
    try:
        yield client
    finally:
        client.close()


app.dependency_overrides[get_wip_client] = override_get_wip_client

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

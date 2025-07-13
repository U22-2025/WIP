from fastapi.testclient import TestClient

from application.map.fastapi_app import app, get_client

class DummyClient:
    def __init__(self):
        self.set_coords = None
    def set_coordinates(self, lat, lng):
        self.set_coords = (lat, lng)
    async def get_weather(self, day=0, **kwargs):
        return {"weather_code": "100", "temperature": "20", "precipitation_prob": "0", "area_code": "0000"}
    async def get_weather_by_area_code(self, area_code, day=0, **kwargs):
        return {"weather_code": "100", "temperature": str(20 + day), "precipitation_prob": "0", "area_code": area_code}
    def close(self):
        pass

def override_get_client():
    client = DummyClient()
    try:
        yield client
    finally:
        client.close()

app.dependency_overrides[get_client] = override_get_client

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

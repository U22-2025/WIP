from WIP_Client.client import Client


def main():
    print("WIP Client Example (State Management)")
    print("=" * 50)

    with Client(debug=True) as client:
        client.set_coordinates(latitude=35.6895, longitude=139.6917)
        result = client.get_weather()
        if result:
            print("✓ Success!")
            print(result)
        else:
            print("✗ Failed to get weather data")


if __name__ == "__main__":
    main()

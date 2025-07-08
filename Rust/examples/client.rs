use wip_rust::common::clients::weather_client::WeatherClient;

fn main() {
    let client = WeatherClient::new("localhost", 4110, true).expect("init");
    match client.get_weather_simple(11000, true, true, true, false, false, 0) {
        Ok(Some(resp)) => println!("response: {:?}", resp),
        Ok(None) => println!("no response"),
        Err(e) => eprintln!("error: {}", e),
    }
}

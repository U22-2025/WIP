use wip_rust::common::clients::weather_client::WeatherClient;

fn main() {
    // サーバーは IPv4 のローカルアドレスで待ち受けている想定
    let client = WeatherClient::new("127.0.0.1", 4110, true).expect("init");
    match client.get_weather_simple(11000, true, true, true, false, false, 0) {
        Ok(Some(resp)) => println!("response: {:?}", resp),
        Ok(None) => println!("no response"),
        Err(e) => eprintln!("error: {}", e),
    }
}

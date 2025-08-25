use wip_rust::wip_common_rs::client::WipClient;

#[tokio::test]
async fn test_get_weather_proxy_flag() {
    let mut client = WipClient::new("127.0.0.1", 0, 0, 0, 0, false)
        .await
        .unwrap();
    client.set_area_code(130010);
    assert!(
        client
            .get_weather(true, true, true, false, false, 0, true)
            .await
            .is_err()
    );
    assert!(
        client
            .get_weather(true, true, true, false, false, 0, false)
            .await
            .is_err()
    );
}

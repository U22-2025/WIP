use wip_rust::wip_common_rs::client::WipClient;
use wip_rust::wip_common_rs::packet::types::report_packet::ReportRequest;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    // 統合クライアントを作成（デフォルトポートを使用）
    let mut client = WipClient::new("127.0.0.1", 4111, 4109, 4111, 4112, false).await?;

    // エリアコードを設定して気象データを取得
    client.set_area_code(11000);
    if let Some(resp) = client
        .get_weather(true, true, true, false, false, 0, true)
        .await?
    {
        println!("Area Code: {}", resp.area_code);
    }

    // センサーレポート送信の例
    let report = ReportRequest::create_sensor_data_report(
        "011000",
        Some(100),
        Some(22.0),
        Some(30),
        None,
        None,
        1,
        0,
    );
    let _ = client.send_report(report).await?;

    Ok(())
}

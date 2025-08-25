use bitvec::prelude::*;
use std::time::Duration;
use wip_rust::wip_common_rs::clients::report_client::{
    BatchConfig, CompressionConfig, EncryptionConfig, ReportClient, ReportClientConfig,
    ReportClientImpl,
};
use wip_rust::wip_common_rs::packet::core::extended_field::{unpack_ext_fields, FieldValue};
use wip_rust::wip_common_rs::packet::types::report_packet::ReportRequest;

#[tokio::test]
async fn test_auth_hash_included_when_auth_enabled() {
    // サーバ側ソケットを準備し、受信データにauth_hashが含まれているかを検証
    let server_socket = tokio::net::UdpSocket::bind("127.0.0.1:0").await.unwrap();
    let server_port = server_socket.local_addr().unwrap().port();
    let server_task = tokio::spawn(async move {
        let mut buf = [0u8; 2048];
        let (len, _) = server_socket.recv_from(&mut buf).await.unwrap();
        let packet = &buf[..len];
        let bits = BitSlice::<u8, Lsb0>::from_slice(&packet[..20]);
        assert!(bits[24], "ex_flag not set");
        assert!(bits[25], "request_auth flag not set");
        let map = unpack_ext_fields(&packet[20..]);
        assert!(matches!(map.get("auth_hash"), Some(FieldValue::String(s)) if !s.is_empty()));
    });

    // クライアント設定（認証有効）
    let config = ReportClientConfig {
        timeout: Duration::from_millis(100),
        max_concurrent_reports: 1,
        retry_attempts: 1,
        retry_delay: Duration::from_millis(10),
        compression: CompressionConfig::default(),
        encryption: EncryptionConfig::default(),
        batching: BatchConfig::default(),
        enable_debug: false,
        auth_enabled: true,
        auth_passphrase: Some("test_pass".into()),
    };
    let client = ReportClientImpl::with_config("127.0.0.1", server_port, config)
        .await
        .unwrap();

    let report = ReportRequest::create_sensor_data_report(
        "011000",
        Some(100),
        Some(20.0),
        Some(30),
        None,
        None,
        1,
        0,
    );

    // 応答が返らないため結果はエラーになるが、送信処理は行われる
    let _ = client.send_report(report).await;
    server_task.await.unwrap();
}

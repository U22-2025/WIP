use std::process::Command;
use wip_rust::wip_common_rs::packet::core::checksum::calc_checksum12;
use wip_rust::wip_common_rs::packet::types::query_packet::QueryRequest;

#[test]
fn rust_and_python_checksum_match() {
    // サンプルのQueryRequestを作成し、ヘッダ16バイトを取得
    let req = QueryRequest::new(110000, 42, true, false, false, false, false, 0);
    let bytes = req.to_bytes();

    // Rustでチェックサム計算
    let rust_sum = calc_checksum12(&bytes);

    // Pythonコードを実行してチェックサムを計算
    let py_code = format!(
        "from WIPCommonPy.packet.core.format_base import FormatBase;print(FormatBase().calc_checksum12(bytes({:?})))",
        bytes.to_vec()
    );
    let manifest_dir = env!("CARGO_MANIFEST_DIR");
    let py_path = format!("{}/../src", manifest_dir);
    let output = Command::new("python")
        .env("PYTHONPATH", py_path)
        .arg("-c")
        .arg(&py_code)
        .output()
        .expect("failed to run python");
    assert!(output.status.success(), "python exited with status {:?}", output.status);
    let py_sum: u16 = String::from_utf8(output.stdout).unwrap().trim().parse().unwrap();

    assert_eq!(rust_sum, py_sum);
}

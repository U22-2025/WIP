use wip_rust::common::clients::utils::packet_id_generator::PacketIDGenerator12Bit;

fn main() {
    let generator = PacketIDGenerator12Bit::new();
    let id = generator.next_id();
    println!("Generated Packet ID: {}", id);
}

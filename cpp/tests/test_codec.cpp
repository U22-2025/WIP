#include <cassert>
#include <cstdint>
#include <vector>

#include "wiplib/packet/codec.hpp"

using namespace wiplib::proto;

int main() {
  Header h{};
  h.version = 1;
  h.packet_id = 0x123;
  h.type = PacketType::WeatherRequest;
  h.flags.weather = true;
  h.flags.temperature = true;
  h.day = 2;
  h.timestamp = 0x0123456789ABCDEFULL;
  h.area_code = 130010;

  auto enc = encode_header(h);
  assert(enc.has_value());
  auto bytes = enc.value();

  
  assert(bytes.size() == kFixedHeaderSize);

  auto dec = decode_header(bytes);
  assert(dec.has_value());
  auto h2 = dec.value();

  assert(h2.version == h.version);
  assert(h2.packet_id == h.packet_id);
  assert(h2.day == h.day);
  assert(h2.timestamp == h.timestamp);
  assert(h2.area_code == h.area_code);
  assert(h2.flags.weather == true);
  assert(h2.flags.temperature == true);
  assert(static_cast<int>(h2.type) == static_cast<int>(h.type));

  // パケットAPIの基本動作
  Packet p{}; p.header = h;
  auto ep = encode_packet(p);
  assert(ep.has_value());
  auto dp = decode_packet(ep.value());
  assert(dp.has_value());

  // 拡張フィールドの往復
  Packet p2{}; p2.header = h;
  ExtendedField e1; e1.data_type = 0b100001; e1.data = {0x01,0x02,0x03};
  ExtendedField e2; e2.data_type = 0b100010; e2.data = {0xAA};
  p2.extensions.push_back(e1);
  p2.extensions.push_back(e2);
  auto ep2 = encode_packet(p2);
  assert(ep2);
  auto dp2 = decode_packet(ep2.value());
  assert(dp2);
  assert(dp2.value().extensions.size() == 2);
  assert(dp2.value().extensions[0].data_type == e1.data_type);
  assert(dp2.value().extensions[0].data.size() == e1.data.size());
  return 0;
}

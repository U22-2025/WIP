-- Weather Transfer Protocol (WTP) Dissector
local wtp_proto = Proto("wtp", "Weather Transfer Protocol")

-- Protocol fields
local f = wtp_proto.fields
f.version      = ProtoField.uint8("wtp.version", "Version", base.DEC, nil, 0xF0)
f.packet_id    = ProtoField.uint16("wtp.packet_id", "Packet ID", base.HEX, nil, 0x0FFF)
f.type         = ProtoField.uint8("wtp.type", "Type", base.DEC, nil, 0xE0)
f.flags        = ProtoField.uint8("wtp.flags", "Flags", base.HEX, nil, 0x3F)
f.timestamp    = ProtoField.uint64("wtp.timestamp", "Timestamp", base.DEC)
f.checksum     = ProtoField.uint16("wtp.checksum", "Checksum", base.HEX, nil, 0x0FFF)
f.time_offset  = ProtoField.uint8("wtp.time_offset", "Time Offset", base.DEC, nil, 0x07)
f.region_code  = ProtoField.uint32("wtp.region_code", "Region Code", base.HEX, nil, 0x000FFFFF)
f.weather_code = ProtoField.uint16("wtp.weather_code", "Weather Code", base.HEX)
f.temperature  = ProtoField.int8("wtp.temperature", "Temperature (°C)", base.DEC)
f.precip       = ProtoField.uint8("wtp.precip", "Precipitation Probability (%)", base.DEC)
f.reserved     = ProtoField.uint8("wtp.reserved", "Reserved", base.HEX, nil, 0x0F)
f.ext_length   = ProtoField.uint16("wtp.ext_length", "Extension Length", base.DEC)
f.ext_type     = ProtoField.uint8("wtp.ext_type", "Extension Type", base.HEX)
f.ext_data     = ProtoField.bytes("wtp.ext_data", "Extension Data")

-- Type判定用
local TYPE_COORD_REQ  = 0  -- 000
local TYPE_COORD_RESP = 1  -- 001
local TYPE_REQ        = 2  -- 010
local TYPE_RESP       = 3  -- 011

function wtp_proto.dissector(buffer, pinfo, tree)
    pinfo.cols.protocol = "WTP"
    local subtree = tree:add(wtp_proto, buffer(), "Weather Transfer Protocol")
    local offset = 0

    -- Version + Packet ID
    local byte1 = buffer(offset, 1):uint()
    local version = bit.rshift(byte1, 4)
    local byte2 = buffer(offset, 2):uint()
    local packet_id = bit.band(byte2, 0x0FFF)
    subtree:add(f.version, buffer(offset, 1))
    subtree:add(f.packet_id, buffer(offset, 2))
    offset = offset + 2

    -- Type + Flags
    local flags_byte = buffer(offset, 1):uint()
    local type_val = bit.rshift(flags_byte, 5)
    local flags = bit.band(flags_byte, 0x3F)
    subtree:add(f.type, buffer(offset, 1))
    subtree:add(f.flags, buffer(offset, 1))
    offset = offset + 1

    -- Timestamp
    subtree:add(f.timestamp, buffer(offset, 8))
    offset = offset + 8

    -- Checksum
    subtree:add(f.checksum, buffer(offset, 2))
    offset = offset + 2

    -- Time Offset
    subtree:add(f.time_offset, buffer(offset, 1))
    offset = offset + 1

    -- Region Code (20bit → 3 bytes)
    subtree:add(f.region_code, buffer(offset, 3))
    offset = offset + 3

    -- Only if Type == 3 (011): show weather, temp, precip
    if type_val == TYPE_RESP then
        subtree:add(f.weather_code, buffer(offset, 2))
        offset = offset + 2

        subtree:add(f.temperature, buffer(offset, 1))
        offset = offset + 1

        subtree:add(f.precip, buffer(offset, 1))
        offset = offset + 1
    end

    -- Reserved (4 bits)
    subtree:add(f.reserved, buffer(offset, 1))
    offset = offset + 1

    -- Extension field (if flag bit5 = 1)
    if bit.band(flags, 0x20) ~= 0 then
        while offset + 3 <= buffer:len() do
            local ext_len_type = buffer(offset, 2):uint()
            local ext_len = bit.rshift(ext_len_type, 6)
            local ext_type = bit.band(buffer(offset + 2, 1):uint(), 0x3F)

            subtree:add(f.ext_length, buffer(offset, 2))
            subtree:add(f.ext_type, buffer(offset + 2, 1))
            offset = offset + 3

            if offset + ext_len > buffer:len() then break end
            subtree:add(f.ext_data, buffer(offset, ext_len))
            offset = offset + ext_len
        end
    end
end

-- Register dissector to port 12345
local udp_table = DissectorTable.get("udp.port")
udp_table:add(4110, wtp_proto)

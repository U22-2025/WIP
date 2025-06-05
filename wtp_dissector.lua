-- WTP (Weather Transmission Protocol) Wireshark Dissector
-- Based on PACKET_STRUCTURE.md specification

-- プロトコル定義
local wtp_proto = Proto("WTPv1", "Weather Transmission Protocol")

-- 基本フィールドの定義（128ビット固定）
local f_version = ProtoField.uint8("wtp.version", "Version", base.DEC, nil, 0x0F)
local f_packet_id = ProtoField.uint16("wtp.packet_id", "Packet ID", base.DEC, nil, 0xFFF0)
local f_type = ProtoField.uint8("wtp.type", "Type", base.DEC, {
    [0] = "Location Request",
    [1] = "Location Response", 
    [2] = "Weather Request",
    [3] = "Weather Response",
    [4] = "Query Request",
    [5] = "Query Response",
    [6] = "Alert",
    [7] = "Reserved"
}, 0x07)

-- フラグフィールド
local f_weather_flag = ProtoField.bool("wtp.weather_flag", "Weather Flag", 8, nil, 0x08)
local f_temperature_flag = ProtoField.bool("wtp.temperature_flag", "Temperature Flag", 8, nil, 0x10)
local f_pops_flag = ProtoField.bool("wtp.pops_flag", "PoPs Flag", 8, nil, 0x20)
local f_alert_flag = ProtoField.bool("wtp.alert_flag", "Alert Flag", 8, nil, 0x40)
local f_disaster_flag = ProtoField.bool("wtp.disaster_flag", "Disaster Flag", 8, nil, 0x80)
local f_ex_flag = ProtoField.bool("wtp.ex_flag", "Extension Flag", 8, nil, 0x01)
local f_day = ProtoField.uint8("wtp.day", "Days", base.DEC, nil, 0x0E)
local f_reserved = ProtoField.uint8("wtp.reserved", "Reserved", base.HEX, nil, 0xF0)

-- タイムスタンプとエリア情報
local f_timestamp = ProtoField.uint64("wtp.timestamp", "Timestamp", base.DEC)
local f_area_code = ProtoField.uint32("wtp.area_code", "Area Code", base.DEC, nil, 0xFFFFF000)
local f_checksum = ProtoField.uint16("wtp.checksum", "Checksum", base.HEX, nil, 0x0FFF)

-- レスポンス固定長拡張フィールド（129-160ビット）
local f_weather_code = ProtoField.uint16("wtp.weather_code", "Weather Code", base.DEC)
local f_temperature = ProtoField.uint8("wtp.temperature", "Temperature", base.DEC)
local f_pops = ProtoField.uint8("wtp.pops", "Precipitation Probability (%)", base.DEC)

-- 可変長拡張フィールド
local f_ext_record = ProtoField.bytes("wtp.ext_record", "Extension Record")
local f_ext_key = ProtoField.uint16("wtp.ext_key", "Extension Key", base.DEC, {
    [1] = "Alert",
    [2] = "Disaster", 
    [33] = "Latitude",
    [34] = "Longitude",
    [40] = "Source"
}, 0x003F)
local f_ext_length = ProtoField.uint16("wtp.ext_length", "Extension Length", base.DEC, nil, 0xFFC0)
local f_ext_data = ProtoField.string("wtp.ext_data", "Extension Data")

-- プロトコルフィールドの登録
wtp_proto.fields = {
    f_version, f_packet_id, f_type,
    f_weather_flag, f_temperature_flag, f_pops_flag, f_alert_flag, f_disaster_flag,
    f_ex_flag, f_day, f_reserved,
    f_timestamp, f_area_code, f_checksum,
    f_weather_code, f_temperature, f_pops,
    f_ext_record, f_ext_key, f_ext_length, f_ext_data
}

-- ビット抽出用ヘルパー関数（リトルエンディアン対応）
local function extract_bits_le(data, bit_pos, bit_len)
    local byte_pos = math.floor(bit_pos / 8)
    local bit_offset = bit_pos % 8
    local mask = (1 << bit_len) - 1
    
    if byte_pos >= data:len() then
        return 0
    end
    
    -- 複数バイトにまたがる場合の処理
    local value = 0
    local bits_read = 0
    local current_byte = byte_pos
    
    while bits_read < bit_len and current_byte < data:len() do
        -- WiresharkのTvbRange APIを使用してバイト値を取得
        local byte_val = data(current_byte, 1):uint()
        local available_bits = 8 - (current_byte == byte_pos and bit_offset or 0)
        local bits_to_read = math.min(bit_len - bits_read, available_bits)
        
        local shift = current_byte == byte_pos and bit_offset or 0
        local byte_mask = ((1 << bits_to_read) - 1) << shift
        local extracted = (byte_val & byte_mask) >> shift
        
        value = value | (extracted << bits_read)
        bits_read = bits_read + bits_to_read
        current_byte = current_byte + 1
    end
    
    return value & mask
end

-- パケットタイプ別最小サイズ取得関数
local function get_min_packet_size(type_val)
    -- レスポンスパケット（1, 3, 5）は20バイト、リクエストパケットは16バイト
    if type_val == 1 or type_val == 3 or type_val == 5 then
        return 20  -- 基本16バイト + 固定長拡張4バイト
    else
        return 16  -- 基本フィールドのみ
    end
end

-- レスポンスパケット判定関数
local function is_response_packet(type_val)
    return type_val == 1 or type_val == 3 or type_val == 5
end

-- 拡張フィールドデコード関数
local function decode_extension_data(key, data)
    if key == 1 or key == 2 then  -- Alert, Disaster (UTF-8 string)
        return data:string()
    elseif key == 33 or key == 34 then  -- Latitude, Longitude (int32 scaled, little-endian)
        if data:len() >= 4 then
            -- リトルエンディアン符号付き32ビット整数として読み取り（10^6倍スケール）
            local value = data:le_int()
            return string.format("%.6f", value / 1000000.0)
        end
    elseif key == 40 then  -- Source (UTF-8 string)
        return data:string()
    end
    return data:bytes():tohex()
end

-- メイン解析関数
function wtp_proto.dissector(buffer, pinfo, tree)
    local length = buffer:len()
    if length < 16 then  -- 最小パケットサイズ（128ビット = 16バイト）
        return
    end
    
    pinfo.cols.protocol = wtp_proto.name
    
    local subtree = tree:add(wtp_proto, buffer(), "Weather Transmission Protocol")
    
    -- 基本フィールドの解析（128ビット）
    local basic_tree = subtree:add(buffer(0, 16), "Basic Fields (128 bits)")
    
    -- 制御情報ブロック（0-31ビット）
    local control_tree = basic_tree:add(buffer(0, 4), "Control Information Block")
    
    -- ビット単位でのフィールド抽出
    local version = extract_bits_le(buffer(0, 4), 0, 4)
    local packet_id = extract_bits_le(buffer(0, 4), 4, 12)
    local type_val = extract_bits_le(buffer(0, 4), 16, 3)
    local weather_flag = extract_bits_le(buffer(0, 4), 19, 1)
    local temperature_flag = extract_bits_le(buffer(0, 4), 20, 1)
    local pops_flag = extract_bits_le(buffer(0, 4), 21, 1)
    local alert_flag = extract_bits_le(buffer(0, 4), 22, 1)
    local disaster_flag = extract_bits_le(buffer(0, 4), 23, 1)
    local ex_flag = extract_bits_le(buffer(0, 4), 24, 1)
    local day = extract_bits_le(buffer(0, 4), 25, 3)
    local reserved = extract_bits_le(buffer(0, 4), 28, 4)
    
    control_tree:add_le(f_version, buffer(0, 1)):append_text(" (" .. version .. ")")
    control_tree:add_le(f_packet_id, buffer(0, 2)):append_text(" (" .. packet_id .. ")")
    control_tree:add_le(f_type, buffer(2, 1)):append_text(" (" .. type_val .. ")")
    
    -- フラグ情報
    local flag_tree = control_tree:add(buffer(2, 2), "Flags")
    flag_tree:add_le(f_weather_flag, buffer(2, 1)):append_text(" (" .. weather_flag .. ")")
    flag_tree:add_le(f_temperature_flag, buffer(2, 1)):append_text(" (" .. temperature_flag .. ")")
    flag_tree:add_le(f_pops_flag, buffer(2, 1)):append_text(" (" .. pops_flag .. ")")
    flag_tree:add_le(f_alert_flag, buffer(2, 1)):append_text(" (" .. alert_flag .. ")")
    flag_tree:add_le(f_disaster_flag, buffer(2, 1)):append_text(" (" .. disaster_flag .. ")")
    flag_tree:add_le(f_ex_flag, buffer(3, 1)):append_text(" (" .. ex_flag .. ")")
    flag_tree:add_le(f_day, buffer(3, 1)):append_text(" (" .. day .. " days)")
    flag_tree:add_le(f_reserved, buffer(3, 1)):append_text(" (" .. reserved .. ")")
    
    -- タイムスタンプ（32-95ビット）
    local timestamp = buffer(4, 8):le_uint64()
    local timestamp_str = ""
    if timestamp:tonumber() and timestamp:tonumber() > 0 then
        -- UInt64を安全にnumberに変換してからos.dateを使用
        local ts_num = timestamp:tonumber()
        if ts_num <= 2147483647 then  -- 32bit時刻の範囲内
            timestamp_str = os.date("%Y-%m-%d %H:%M:%S", ts_num)
        else
            timestamp_str = "Invalid timestamp: " .. tostring(timestamp)
        end
    else
        timestamp_str = tostring(timestamp)
    end
    basic_tree:add_le(f_timestamp, buffer(4, 8)):append_text(" (" .. timestamp_str .. ")")
    
    -- エリア情報（96-127ビット）
    local area_info_tree = basic_tree:add(buffer(12, 4), "Area Information Block")
    local area_code = extract_bits_le(buffer(12, 4), 0, 20)
    local checksum = extract_bits_le(buffer(12, 4), 20, 12)
    
    area_info_tree:add_le(f_area_code, buffer(12, 3)):append_text(" (" .. area_code .. ")")
    area_info_tree:add_le(f_checksum, buffer(14, 2)):append_text(" (0x" .. string.format("%03X", checksum) .. ")")
    
    -- パケットサイズの検証とパディング効率の表示
    local min_size = get_min_packet_size(type_val)
    local efficiency = string.format("%.1f%%", (length / length) * 100)  -- 実際は有効データ/全体で計算
    subtree:add(buffer(0, 0), "Packet Analysis: Size=" .. length .. " bytes, Min=" .. min_size .. " bytes, Efficiency=" .. efficiency)
    
    -- レスポンスパケットの固定長拡張フィールド解析（129-160ビット）
    if is_response_packet(type_val) and length >= 20 then
        local fixed_ext_tree = subtree:add(buffer(16, 4), "Fixed Extension Fields (129-160 bits)")
        
        -- weather_code (129-144ビット, 16ビット)
        local weather_code = extract_bits_le(buffer(16, 4), 0, 16)
        fixed_ext_tree:add_le(f_weather_code, buffer(16, 2)):append_text(" (" .. weather_code .. ")")
        
        -- temperature (145-152ビット, 8ビット)
        local temperature = extract_bits_le(buffer(16, 4), 16, 8)
        local temp_celsius = temperature - 100  -- -100℃～+155℃
        fixed_ext_tree:add_le(f_temperature, buffer(18, 1)):append_text(" (" .. temperature .. " = " .. temp_celsius .. "°C)")
        
        -- pops (153-160ビット, 8ビット)
        local pops = extract_bits_le(buffer(16, 4), 24, 8)
        fixed_ext_tree:add_le(f_pops, buffer(19, 1)):append_text(" (" .. pops .. "%)")
    end
    
    -- 可変長拡張フィールドの解析（ex_flag = 1の場合）
    if ex_flag == 1 and length > min_size then
        local var_ext_start = is_response_packet(type_val) and 20 or 16
        local ext_tree = subtree:add(buffer(var_ext_start), "Variable Extension Fields")
        local offset = var_ext_start
        local record_num = 1
        local valid_records = 0
        
        while offset < length do
            if offset + 2 > length then
                break
            end
            
            -- レコードヘッダー（16ビット: 6ビットキー + 10ビットデータ長）
            local header = buffer(offset, 2):le_uint()
            local key = header & 0x3F  -- 下位6ビット（0-5）
            local data_len = (header >> 6) & 0x3FF  -- 上位10ビット（6-15）
            
            -- 無効なレコード（key=0, data_len=0）の場合は処理を終了
            if header == 0 or (key == 0 and data_len == 0) then
                -- パディング開始位置を記録
                local padding_length = length - offset
                ext_tree:add(buffer(offset), "Zero Padding (Offset: " .. offset .. ", Length: " .. padding_length .. " bytes)")
                break
            end
            
            if offset + 2 + data_len > length then
                break
            end
            
            local record_tree = ext_tree:add(buffer(offset, 2 + data_len), 
                "Extension Record " .. record_num .. " (Key: " .. key .. ", Length: " .. data_len .. ")")
            
            record_tree:add_le(f_ext_key, buffer(offset, 1)):append_text(" (" .. key .. ")")
            record_tree:add_le(f_ext_length, buffer(offset, 2)):append_text(" (" .. data_len .. " bytes)")
            
            if data_len > 0 then
                local data_buffer = buffer(offset + 2, data_len)
                local decoded_data = decode_extension_data(key, data_buffer)
                record_tree:add(f_ext_data, data_buffer):append_text(" (" .. decoded_data .. ")")
            end
            
            offset = offset + 2 + data_len
            record_num = record_num + 1
            valid_records = valid_records + 1
        end
        
        -- デバッグ情報を表示
        ext_tree:add(buffer(16, 0), "Debug Info: Valid records=" .. valid_records .. ", Total packet=" .. length .. " bytes, Expected end=" .. offset)
    end
    
    -- パケット情報の設定
    pinfo.cols.info = "WTP v" .. version .. " ID:" .. packet_id .. " Type:" .. type_val .. 
                     " Area:" .. area_code .. (ex_flag == 1 and " [Extended]" or "")
end

-- UDPポート4109-4111にプロトコルを登録
local udp_port_table = DissectorTable.get("udp.port")
udp_port_table:add(4109, wtp_proto)
udp_port_table:add(4110, wtp_proto)
udp_port_table:add(4111, wtp_proto)

-- プロトコル情報を表示
local function wtp_proto_init()
    local wtp_info = {
        version = "1.0",
        author = "WTP Project",
        description = "Weather Transmission Protocol Dissector for Wireshark"
    }
    print("WTP Dissector loaded: " .. wtp_info.description .. " v" .. wtp_info.version)
end

-- 初期化時にプロトコル情報を表示
wtp_proto_init()

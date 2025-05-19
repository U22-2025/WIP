class format:
    """
    This class is used to define the format of the packets.
    """
    version = None # 1-4bit
    packet_ID = None # 5-16bit
    type = None # 17-19bit
    weather_flag = None # 20bit
    temperature_flag = None # 21bit
    pops_flag = None # 22bit
    alert_flag = None # 23bit
    disaster_flag = None # 24bit
    ex_flag = None # 25bit
    day = None # 26-28bit
    reserved = None # 29-32bit
    timestamp = None # 33-96bit
    area_code = None # 97-116bit
    checksum = None # 117-128bit

    @staticmethod
    def extract_bits(bitstr: int, start: int, length: int) -> int:
        """
        指定したビット列(bitstr)から、startビット目（0始まり）からlengthビット分を取り出して返す。
        例: extract_bits(0b110110, 1, 3) -> 0b101
        """
        mask = (1 << length) - 1
        return (bitstr >> (start)) & mask
    
    @staticmethod
    def extract_rest_bits(bitstr: int, start: int) -> int:
        """
        指定したビット列(bitstr)から、startビット目（0始まり）以降の全てのビットを取り出して返す。
        例: extract_rest_bits(0b110110, 2) -> 0b110
        """
        return bitstr >> start
    
    def common_bit_fetch(self, bitstr: int):
        """
        受信したビット列から、共通のビットを取り出す。
        """
        format.version = format.extract_bits(bitstr, 0, 4)
        format.packet_ID = format.extract_bits(bitstr, 4, 12)
        format.type = format.extract_bits(bitstr, 16, 3)
        format.weather_flag = format.extract_bits(bitstr, 19, 1)
        format.temperature_flag = format.extract_bits(bitstr, 20, 1)
        format.pops_flag = format.extract_bits(bitstr, 21, 1)
        format.alert_flag = format.extract_bits(bitstr, 22, 1)
        format.disaster_flag = format.extract_bits(bitstr, 23, 1)
        format.ex_flag = format.extract_bits(bitstr, 24, 1)
        format.day = format.extract_bits(bitstr, 25, 3)
        format.reserved = format.extract_bits(bitstr, 28, 4)
        format.timestamp = format.extract_bits(bitstr, 32, 64)
        format.area_code = format.extract_bits(bitstr, 96, 20)
        format.checksum = format.extract_bits(bitstr, 116, 12)
        return
    

class request ( format ):
    def __init__(self):
        return
    
    def bits_fetch(self, bitstr: int):
        """
        受信したビット列から、リクエストのビットを取り出す。
        """
        format.common_bit_fetch(bitstr)
        format.timestamp = format.extract_bits(bitstr, 32, 64)
        format.area_code = format.extract_bits(bitstr, 96, 20)
        format.checksum = format.extract_bits(bitstr, 116, 12)
        return
    
class response ( format ):
    weather_code = None # 1-16bit
    temperature = None # 17-24bit
    pops = None # 25-32bit
    ex_field = None # 33- bit

    def __init__(self):
        return
    
    def bits_fetch(self, bitstr: int):
        """
        受信したビット列から、レスポンスのビットを取り出す。
        """
        format.common_bit_fetch(bitstr)
        format.weather_code = format.extract_bits(bitstr, 16, 16)
        format.temperature = format.extract_bits(bitstr, 32, 8)
        format.pops = format.extract_bits(bitstr, 40, 8)
        format.ex_field = format.extract_rest_bits(bitstr, 48)
        return
    
class resolver_request ( format ):
    longitude = None # 1-64bit
    latitude = None # 65-128bit

    def __init__(self):
        return
    
    def bits_fetch(self, bitstr: int):
        """
        受信したビット列から、リクエストのビットを取り出す。
        """
        format.common_bit_fetch(bitstr)
        format.longitude = format.extract_bits(bitstr, 16, 64)
        format.latitude = format.extract_bits(bitstr, 80, 64)
        return
    
class resolver_response ( format ):
    longitude = None # 1-64bit
    latitude = None # 65-128bit
    ex_field = None # 129- bit

    def __init__(self):
        return
    
    def bits_fetch(self, bitstr: int):
        """
        受信したビット列から、レスポンスのビットを取り出す。
        """
        format.common_bit_fetch(bitstr)
        format.longitude = format.extract_bits(bitstr, 16, 64)
        format.latitude = format.extract_bits(bitstr, 80, 64)
        format.ex_field = format.extract_rest_bits(bitstr, 144)
        return  